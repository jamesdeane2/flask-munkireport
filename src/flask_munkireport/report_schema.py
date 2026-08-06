"""Column whitelist for the report builder.

Only ONE-row-per-serial tables (verified against the live DB 2026-08-06).
Multi-row tables (applications, installhistory, diskreport, memory, ...)
are deliberately absent — joining them explodes the row count. If one is
ever needed it gets an aggregating view, not a listing here.

fmt values:
  epoch   - unix timestamp int -> "YYYY-MM-DD HH:MM"
  secdays - seconds -> whole days
  osver   - MunkiReport padded int (150707) -> "15.7.7"
  bool    - 0/1 -> No/Yes (passes through non-numeric strings)
"""

# (table, display_name, [(column, label, fmt|None), ...])
REPORT_SCHEMA = [
    ("machine", "Machine", [
        ("hostname", "Name", None),
        ("computer_name", "Computer Name", None),
        ("machine_model", "Model", None),
        ("machine_desc", "Description", None),
        ("os_version", "OS Version", "osver"),
        ("buildversion", "OS Build", None),
        ("cpu", "CPU", None),
        ("cpu_arch", "Arch", None),
        ("physical_memory", "Memory (GB)", None),
    ]),
    ("reportdata", "Report", [
        ("serial_number", "Serial", None),
        ("console_user", "User", None),
        ("long_username", "Full Name", None),
        ("remote_ip", "Remote IP", None),
        ("timestamp", "Last Check-in", "epoch"),
        ("reg_timestamp", "First Seen", "epoch"),
        ("uptime", "Uptime (days)", "secdays"),
    ]),
    ("munkireport", "Munki", [
        ("manifestname", "Manifest", None),
        ("version", "Munki Version", None),
        ("runtype", "Run Type", None),
        ("errors", "Errors", None),
        ("warnings", "Warnings", None),
    ]),
    ("munkireportinfo", "MR Client", [
        ("version", "Client Version", None),
        ("python_version", "Python", None),
        ("installdate", "Client Installed", None),
    ]),
    ("security", "Security", [
        ("filevault_status", "FileVault", "onoff"),
        ("sip", "SIP", None),
        ("gatekeeper", "Gatekeeper", None),
        ("firewall_state", "Firewall", "firewall"),
        ("activation_lock", "Activation Lock", "actlock"),
        ("firmwarepw", "Firmware Password", None),
        ("root_user", "Root User", "bool"),
        ("ssh_users", "SSH Users", None),
        ("ard_users", "ARD Users", None),
    ]),
    ("mdm_status", "MDM", [
        ("mdm_enrolled", "Enrolled", None),
        ("mdm_enrolled_via_dep", "Via DEP", "bool"),
        ("is_user_approved", "User Approved", "bool"),
        ("is_supervised", "Supervised", "bool"),
        ("mdm_server_url", "MDM Server", None),
    ]),
    ("softwareupdate", "Software Update", [
        ("lastsuccessfuldate", "Last SU Check", None),
        ("lastupdatesavailable", "Updates Pending", None),
        ("automaticcheckenabled", "Auto Check", "onoff"),
        ("xprotect_version", "XProtect", None),
    ]),
    ("supported_os", "Supported OS", [
        ("current_os", "Current macOS", None),
        ("highest_supported", "Highest Supported", None),
        ("shipping_os", "Shipped With", None),
    ]),
    ("timemachine", "Time Machine", [
        ("auto_backup", "Auto Backup", "onoff"),
        ("last_success", "Last Backup", None),
        ("snapshot_count", "Snapshots", None),
    ]),
    ("localadmin", "Local Admins", [
        ("users", "Admin Users", None),
        ("user_count", "Admin Count", None),
    ]),
    ("wifi", "Wi-Fi", [
        ("ssid", "SSID", None),
        ("state", "State", None),
    ]),
    ("sophos", "Sophos", [
        ("installed", "Product", None),
        ("running", "Running", "bool"),
        ("product_version", "Version", None),
    ]),
    ("nudge", "Nudge", [
        ("required_os", "Required macOS", None),
        ("past_required_install_date", "Past Deadline", "bool"),
        ("deferral_count", "Deferrals", None),
    ]),
    ("power", "Power / Battery", [
        ("condition", "Battery Condition", None),
        ("cycle_count", "Cycle Count", None),
        ("current_percent", "Battery %", None),
        ("max_percent", "Battery Health %", None),
    ]),
]

# Flat lookup: "table.column" -> (table, column, label, fmt)
COLMAP = {}
for _table, _name, _cols in REPORT_SCHEMA:
    for _col, _label, _fmt in _cols:
        COLMAP[f"{_table}.{_col}"] = (_table, _col, _label, _fmt)


def schema_json():
    """Schema in the shape the builder page consumes."""
    return [
        {"key": t, "name": n, "cols": [{"id": f"{t}.{c}", "label": l} for c, l, _ in cols]}
        for t, n, cols in REPORT_SCHEMA
    ]
