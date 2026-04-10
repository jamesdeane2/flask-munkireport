"""Cyber Essentials Plus compliance evaluation logic."""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from ..database import MunkiReportDB


# macOS version support status as of March 2026
# Update this when Apple changes support
MACOS_SUPPORT = {
    # major_version: (name, status)
    # status: "current", "supported" (still getting security updates), "eol"
    26: ("Tahoe", "current"),
    15: ("Sequoia", "supported"),
    14: ("Sonoma", "supported"),
    13: ("Ventura", "supported"),  # still getting security updates (13.7.x) as of Mar 2026
    12: ("Monterey", "eol"),
    11: ("Big Sur", "eol"),
    10: ("Legacy", "eol"),
}

# Stale threshold in days
STALE_THRESHOLD_DAYS = 30

# OS patch grace period — machines with pending updates younger than this pass
PATCH_GRACE_DAYS = 14

# Max admin accounts before flagging
MAX_ADMIN_ACCOUNTS = 2


CE_PLUS_QUERY = """
SELECT
    m.serial_number,
    m.computer_name,
    m.os_version,
    m.machine_model,
    mr.manifestname,
    rd.timestamp as last_checkin,
    -- FileVault
    fv.filevault_status as fv_status,
    fv.conversion_state as fv_conversion,
    -- Firewall
    fw.globalstate as fw_state,
    -- Security
    sec.gatekeeper,
    sec.sip,
    sec.firewall_state as sec_fw_state,
    -- Auto-update
    su.automaticcheckenabled as auto_check,
    su.automaticdownload as auto_download,
    su.criticalupdateinstall as auto_critical,
    su.recommendedupdates as pending_updates,
    -- Admin accounts
    la.users as local_admins,
    la.user_count as admin_count,
    -- Supported OS
    so.current_os,
    so.highest_supported
FROM machine m
INNER JOIN munkireport mr ON m.serial_number = mr.serial_number
LEFT JOIN reportdata rd ON m.serial_number = rd.serial_number
LEFT JOIN filevault_status fv ON m.serial_number = fv.serial_number
LEFT JOIN firewall fw ON m.serial_number = fw.serial_number
LEFT JOIN security sec ON m.serial_number = sec.serial_number
LEFT JOIN softwareupdate su ON m.serial_number = su.serial_number
LEFT JOIN localadmin la ON m.serial_number = la.serial_number
LEFT JOIN supported_os so ON m.serial_number = so.serial_number
WHERE mr.manifestname LIKE ?
ORDER BY m.computer_name
"""


def _parse_os_version(os_version) -> Optional[tuple]:
    """Parse MunkiReport's packed integer OS version into (major, minor, patch).

    MunkiReport stores os_version as an integer: major*10000 + minor*100 + patch.
    E.g. 150700 = 15.7.0, 260300 = 26.3.0, 101404 = 10.14.4
    """
    if os_version is None:
        return None
    try:
        v = int(os_version)
    except (ValueError, TypeError):
        # Might be a string like "15.7.0" — try that
        try:
            parts = str(os_version).split(".")
            return (int(parts[0]), int(parts[1]) if len(parts) > 1 else 0,
                    int(parts[2]) if len(parts) > 2 else 0)
        except (ValueError, IndexError):
            return None

    if v < 1000:
        # Possibly just a major version number
        return (v, 0, 0)

    major = v // 10000
    minor = (v % 10000) // 100
    patch = v % 100
    return (major, minor, patch)


def _format_os_version(os_version) -> str:
    """Convert packed integer OS version to readable string."""
    parsed = _parse_os_version(os_version)
    if parsed is None:
        return str(os_version) if os_version else "Unknown"
    major, minor, patch = parsed
    return f"{major}.{minor}.{patch}"


def _parse_os_major(os_version) -> Optional[int]:
    """Extract major version number from OS version (packed int or string)."""
    parsed = _parse_os_version(os_version)
    if parsed is None:
        return None
    return parsed[0]


def _check_filevault(row: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Check FileVault disk encryption status.

    Returns (passed, details).
    MunkiReport stores filevault_status as integer (1=on, 0=off) or text.
    """
    status = row.get("fv_status")
    conversion = row.get("fv_conversion")

    # Handle integer values (1=on, 0=off)
    if isinstance(status, int):
        passed = status == 1
        status_display = "On" if status == 1 else "Off"
    elif status is not None:
        status_lower = str(status).lower().strip()
        passed = status_lower in ("filevault is on.", "on", "on (encrypted)", "1")
        status_display = str(status)
    else:
        passed = False
        status_display = "Unknown"

    # Special case: converting
    converting = False
    if conversion and "convert" in str(conversion).lower():
        converting = True

    details = {"status": status_display}
    if conversion:
        details["conversion_state"] = conversion
    if converting:
        details["converting"] = True

    return passed, details


def _check_firewall(row: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Check firewall is enabled.

    globalstate: 0=off, 1=on, 2=on+stealth
    """
    fw_state = row.get("fw_state")

    if fw_state is None:
        return False, {"globalstate": None, "note": "No firewall data"}

    try:
        state_int = int(fw_state)
    except (ValueError, TypeError):
        return False, {"globalstate": fw_state, "note": "Unexpected value"}

    passed = state_int >= 1
    details = {"globalstate": state_int}
    if state_int == 2:
        details["stealth_mode"] = True

    return passed, details


def _check_os_supported(row: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Check OS is not end-of-life."""
    raw_version = row.get("os_version")
    os_version_display = _format_os_version(raw_version)
    major = _parse_os_major(raw_version)

    if major is None:
        return False, {"os_version": os_version_display, "note": "Cannot parse version"}

    support_info = MACOS_SUPPORT.get(major)
    if support_info is None:
        # Unknown version — if > max known, assume current
        max_known = max(MACOS_SUPPORT.keys())
        if major > max_known:
            return True, {"os_version": os_version_display, "status": "newer_than_known"}
        return False, {"os_version": os_version_display, "status": "unknown_old"}

    name, status = support_info
    passed = status in ("current", "supported")

    details = {
        "os_version": os_version_display,
        "os_name": name,
        "support_status": status,
    }

    return passed, details


def _check_os_patched(row: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Check OS is patched (no pending critical macOS updates).

    MunkiReport stores recommendedupdates as a comma-separated string of
    update names, e.g. "Safari, macOS Sequoia 15.7.4, macOS Sonoma 14.8.4".

    We only flag machines with pending *macOS* updates (not just Safari/Xcode).
    """
    pending = row.get("pending_updates")
    os_version_display = _format_os_version(row.get("os_version"))

    details = {"os_version": os_version_display}

    # No pending updates data — assume patched
    if not pending or str(pending).strip() == "":
        return True, details

    # Parse the comma-separated update list
    pending_str = str(pending).strip()
    updates = [u.strip() for u in pending_str.split(",") if u.strip()]

    # Filter to macOS updates only (critical for CE+)
    macos_updates = [u for u in updates if u.lower().startswith("macos")]
    other_updates = [u for u in updates if not u.lower().startswith("macos")]

    details["all_pending"] = updates

    if not macos_updates:
        # Only non-OS updates pending (Safari, Xcode, etc.) — pass
        details["note"] = "Only app updates pending, no macOS patches"
        return True, details

    # Has pending macOS updates — fail
    details["macos_updates_pending"] = macos_updates
    if other_updates:
        details["other_updates_pending"] = other_updates
    details["note"] = "Pending macOS updates — verify age for CE+ 14-day requirement"

    return False, details


def _check_gatekeeper(row: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Check Gatekeeper is enabled.

    MunkiReport stores this as "Active" or similar text.
    """
    gatekeeper = row.get("gatekeeper") or ""
    gk_lower = str(gatekeeper).lower().strip()

    passed = any(term in gk_lower for term in [
        "active",
        "app store and identified developers",
        "enabled",
        "app store",
    ])

    return passed, {"gatekeeper": gatekeeper or "Unknown"}


def _check_sip(row: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Check System Integrity Protection is enabled.

    MunkiReport stores as "Active" or "Disabled".
    """
    sip = row.get("sip") or ""
    sip_lower = str(sip).lower().strip()

    passed = sip_lower in ("active", "enabled")

    return passed, {"sip": sip or "Unknown"}


def _check_auto_update(row: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Check automatic updates are configured.

    CE+ requires at minimum: automatic checking enabled AND critical update install.
    NULL values = not provably compliant = fail.
    """
    auto_check = row.get("auto_check")
    auto_critical = row.get("auto_critical")
    auto_download = row.get("auto_download")

    # Track whether we have data at all
    has_data = any(v is not None for v in [auto_check, auto_critical, auto_download])

    details = {
        "automatic_check": bool(auto_check) if auto_check is not None else None,
        "automatic_download": bool(auto_download) if auto_download is not None else None,
        "critical_update_install": bool(auto_critical) if auto_critical is not None else None,
    }

    if not has_data:
        details["note"] = "No software update data reported"

    # CE+ requires at minimum: auto-check enabled AND critical updates install
    passed = bool(auto_check) and bool(auto_critical)

    return passed, details


def _check_admin_accounts(row: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Check admin account count is reasonable."""
    admin_count = row.get("admin_count")
    local_admins = row.get("local_admins") or ""

    if admin_count is None:
        return True, {"admin_count": None, "note": "No admin data"}

    try:
        count = int(admin_count)
    except (ValueError, TypeError):
        return False, {"admin_count": admin_count, "note": "Unexpected value"}

    passed = count <= MAX_ADMIN_ACCOUNTS

    details = {
        "admin_count": count,
        "admin_users": local_admins,
    }

    if not passed:
        details["note"] = f"Has {count} admin accounts (max {MAX_ADMIN_ACCOUNTS})"

    return passed, details


# Map of check name → function
CHECKS = {
    "filevault": _check_filevault,
    "firewall": _check_firewall,
    "os_supported": _check_os_supported,
    "os_patched": _check_os_patched,
    "gatekeeper": _check_gatekeeper,
    "sip": _check_sip,
    "auto_update": _check_auto_update,
    "admin_accounts": _check_admin_accounts,
}


def evaluate_machine(row: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a single machine against all CE+ checks.

    Args:
        row: Machine data dict from the CE+ query.

    Returns:
        Dict with machine info, per-check results, and overall pass/fail.
    """
    results = {}
    failing_checks = []

    for check_name, check_fn in CHECKS.items():
        passed, details = check_fn(row)
        results[check_name] = {
            "passed": passed,
            "details": details,
        }
        if not passed:
            failing_checks.append(check_name)

    # Calculate days since last checkin
    last_checkin = row.get("last_checkin")
    days_since_checkin = None
    is_stale = False

    if last_checkin:
        try:
            # MunkiReport stores timestamps as unix epoch or ISO — handle both
            if isinstance(last_checkin, (int, float)):
                checkin_dt = datetime.fromtimestamp(last_checkin, tz=timezone.utc)
            else:
                checkin_str = str(last_checkin)
                if "T" in checkin_str or "-" in checkin_str:
                    checkin_dt = datetime.fromisoformat(checkin_str.replace("Z", "+00:00"))
                else:
                    checkin_dt = datetime.fromtimestamp(float(checkin_str), tz=timezone.utc)

            now = datetime.now(timezone.utc)
            days_since_checkin = (now - checkin_dt).days
            is_stale = days_since_checkin > STALE_THRESHOLD_DAYS
        except (ValueError, TypeError, OSError):
            pass

    return {
        "serial_number": row.get("serial_number"),
        "computer_name": row.get("computer_name"),
        "os_version": _format_os_version(row.get("os_version")),
        "machine_model": row.get("machine_model"),
        "last_checkin": str(last_checkin) if last_checkin else None,
        "days_since_checkin": days_since_checkin,
        "is_stale": is_stale,
        "overall_pass": len(failing_checks) == 0,
        "failing_checks": failing_checks,
        "checks": results,
    }


def generate_report(
    db: MunkiReportDB,
    manifest: str,
    include_passing: bool = False,
) -> Dict[str, Any]:
    """Generate a full CE+ compliance report for a manifest.

    Args:
        db: MunkiReportDB instance.
        manifest: Manifest name to filter by (supports SQL LIKE patterns).
        include_passing: If True, include passing machines in the failures list.

    Returns:
        Full compliance report dict.
    """
    # Query all machines in the manifest
    rows = db.execute_query(CE_PLUS_QUERY, (manifest,))

    if not rows:
        return {
            "success": True,
            "manifest": manifest,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_machines": 0,
                "pass": 0,
                "fail": 0,
                "checks": {name: {"pass": 0, "fail": 0} for name in CHECKS},
            },
            "failures": [],
            "stale_machines": [],
        }

    # Evaluate all machines
    evaluated = [evaluate_machine(row) for row in rows]

    # Build summary
    total = len(evaluated)
    passing = sum(1 for m in evaluated if m["overall_pass"])
    failing = total - passing

    # Per-check summary
    check_summary = {}
    for check_name in CHECKS:
        check_pass = sum(
            1 for m in evaluated if m["checks"][check_name]["passed"]
        )
        check_summary[check_name] = {
            "pass": check_pass,
            "fail": total - check_pass,
        }

    # Build failure list
    if include_passing:
        detail_list = evaluated
    else:
        detail_list = [m for m in evaluated if not m["overall_pass"]]

    # Format failure entries — strip full check details for brevity,
    # keep only failing check details
    failures = []
    for m in detail_list:
        entry = {
            "serial_number": m["serial_number"],
            "computer_name": m["computer_name"],
            "os_version": m["os_version"],
            "last_checkin": m["last_checkin"],
            "days_since_checkin": m["days_since_checkin"],
            "failing_checks": m["failing_checks"],
            "details": {},
        }

        # Include details for failing checks only (or all if include_passing)
        for check_name in m["failing_checks"]:
            entry["details"][check_name] = m["checks"][check_name]["details"]

        if include_passing and m["overall_pass"]:
            entry["status"] = "pass"

        failures.append(entry)

    # Stale machines — separate list
    stale_machines = [
        {
            "serial_number": m["serial_number"],
            "computer_name": m["computer_name"],
            "last_checkin": m["last_checkin"],
            "days_since_checkin": m["days_since_checkin"],
        }
        for m in evaluated
        if m["is_stale"]
    ]

    return {
        "success": True,
        "manifest": manifest,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_machines": total,
            "pass": passing,
            "fail": failing,
            "checks": check_summary,
        },
        "failures": failures,
        "stale_machines": stale_machines,
    }
