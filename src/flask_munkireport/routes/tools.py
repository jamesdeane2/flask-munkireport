"""Tool endpoints - main query API."""

from flask import jsonify, request, current_app, g
from . import api
from ..auth import require_api_key
from ..database import MunkiReportDB
from ..utils.machines import query_machines, get_machine_details, get_mdm_enrollment_summary
from ..utils.events import get_events, get_error_summary, get_recent_critical_events
from ..utils.queries import get_database_stats, get_table_summary


def get_db():
    """Get database instance for request."""
    if 'db' not in g:
        g.db = MunkiReportDB(
            current_app.config['DATABASE_PATH'],
            timeout=current_app.config['SQLITE_TIMEOUT'],
            check_same_thread=current_app.config['SQLITE_CHECK_SAME_THREAD']
        )
    return g.db


@api.route('/tools/query_machines', methods=['POST'])
@require_api_key
def route_query_machines():
    """Query machines with filters."""
    try:
        data = request.get_json() or {}
        db = get_db()
        
        result = query_machines(
            db,
            filters=data.get('filters'),
            include=data.get('include'),
            order_by=data.get('order_by'),
            limit=data.get('limit')
        )
        
        return jsonify({
            "success": True,
            "data": result,
            "count": len(result)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api.route('/tools/get_machine_details/<serial_number>', methods=['GET'])
@require_api_key
def route_get_machine_details(serial_number):
    """Get details for a specific machine."""
    try:
        db = get_db()
        result = get_machine_details(db, serial_number)
        
        if result is None:
            return jsonify({
                "success": False,
                "error": f"Machine not found: {serial_number}"
            }), 404
        
        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api.route('/tools/get_mdm_enrollment_summary', methods=['GET'])
@require_api_key
def route_get_mdm_enrollment_summary():
    """Get MDM enrollment summary."""
    try:
        db = get_db()
        result = get_mdm_enrollment_summary(db)
        
        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api.route('/tools/get_events', methods=['POST'])
@require_api_key
def route_get_events():
    """Query events."""
    try:
        data = request.get_json() or {}
        db = get_db()
        
        result = get_events(
            db,
            filters=data.get('filters'),
            include_machine=data.get('include_machine', False),
            order_by=data.get('order_by'),
            limit=data.get('limit')
        )
        
        return jsonify({
            "success": True,
            "data": result,
            "count": len(result)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api.route('/tools/get_error_summary', methods=['GET'])
@require_api_key
def route_get_error_summary():
    """Get error summary."""
    try:
        db = get_db()
        result = get_error_summary(db)
        
        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api.route('/tools/get_recent_critical_events', methods=['GET'])
@require_api_key
def route_get_recent_critical_events():
    """Get recent critical events."""
    try:
        hours = request.args.get('hours', default=24, type=int)
        limit = request.args.get('limit', default=50, type=int)
        
        db = get_db()
        result = get_recent_critical_events(db, hours=hours, limit=limit)
        
        return jsonify({
            "success": True,
            "data": result,
            "count": len(result)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api.route('/tools/get_database_stats', methods=['GET'])
@require_api_key
def route_get_database_stats():
    """Get database statistics."""
    try:
        db = get_db()
        result = get_database_stats(db)
        
        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api.route('/tools/get_table_summary', methods=['POST'])
@require_api_key
def route_get_table_summary():
    """Get table summary with optional grouping."""
    try:
        data = request.get_json() or {}
        db = get_db()

        if 'table_name' not in data:
            return jsonify({
                "success": False,
                "error": "Missing required field: table_name"
            }), 400

        result = get_table_summary(
            db,
            table_name=data['table_name'],
            group_by=data.get('group_by'),
            filters=data.get('filters')
        )

        return jsonify({
            "success": True,
            "data": result
        })
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api.route('/tools/get_machine_profiles/<serial_number>', methods=['GET'])
@require_api_key
def route_get_machine_profiles(serial_number):
    """Get all configuration profiles installed on a machine."""
    try:
        db = get_db()

        query = """
            SELECT
                profile_uuid,
                profile_name,
                profile_organization,
                profile_verification_state,
                profile_method,
                profile_install_date,
                profile_removal_allowed,
                profile_description,
                profile_id,
                payload_name,
                payload_display,
                user,
                timestamp
            FROM profile
            WHERE serial_number = ?
            ORDER BY profile_name, payload_name
        """

        result = db.execute_query(query, (serial_number,))

        return jsonify({
            "success": True,
            "data": result,
            "count": len(result)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api.route('/tools/get_filevault_status/<serial_number>', methods=['GET'])
@require_api_key
def route_get_filevault_status(serial_number):
    """Get FileVault encryption status for a machine."""
    try:
        db = get_db()

        query = """
            SELECT
                filevault_status,
                has_personal_recovery_key,
                has_institutional_recovery_key,
                conversion_state,
                conversion_percent,
                filevault_users,
                crypto_users,
                volume_name,
                volume_size,
                bytes_converted,
                auth_restart_support,
                bootstraptoken_supported,
                bootstraptoken_escrowed,
                deferral_info
            FROM filevault_status
            WHERE serial_number = ?
        """

        result = db.execute_single(query, (serial_number,))

        if result is None:
            return jsonify({
                "success": False,
                "error": f"FileVault status not found: {serial_number}"
            }), 404

        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api.route('/tools/get_firewall_status/<serial_number>', methods=['GET'])
@require_api_key
def route_get_firewall_status(serial_number):
    """Get firewall status for a machine."""
    try:
        db = get_db()

        query = """
            SELECT
                globalstate,
                stealthenabled,
                loggingenabled,
                loggingoption,
                allowsignedenabled,
                allowdownloadsignedenabled,
                firewallunload,
                applications,
                services,
                version
            FROM firewall
            WHERE serial_number = ?
        """

        result = db.execute_single(query, (serial_number,))

        if result is None:
            return jsonify({
                "success": False,
                "error": f"Firewall status not found: {serial_number}"
            }), 404

        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api.route('/tools/get_icloud_status/<serial_number>', methods=['GET'])
@require_api_key
def route_get_icloud_status(serial_number):
    """Get iCloud account status for a machine."""
    try:
        db = get_db()

        query = """
            SELECT
                logged_in,
                display_name,
                account_id,
                account_description,
                find_my_mac_enabled,
                clouddesktop_desktop_enabled,
                clouddesktop_documents_enabled,
                clouddesktop_drive_enabled,
                keychain_sync_enabled,
                photo_stream_enabled,
                cloud_photo_enabled,
                calendar_enabled,
                contacts_enabled,
                mail_and_notes_enabled,
                reminders_enabled,
                siri_enabled,
                is_managed_apple_id,
                imessage_syncing_enabled
            FROM icloud
            WHERE serial_number = ?
        """

        result = db.execute_single(query, (serial_number,))

        if result is None:
            return jsonify({
                "success": False,
                "error": f"iCloud status not found: {serial_number}"
            }), 404

        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api.route('/tools/get_local_admins/<serial_number>', methods=['GET'])
@require_api_key
def route_get_local_admins(serial_number):
    """Get local admin users for a machine."""
    try:
        db = get_db()

        query = """
            SELECT
                users,
                user_count
            FROM localadmin
            WHERE serial_number = ?
        """

        result = db.execute_single(query, (serial_number,))

        if result is None:
            return jsonify({
                "success": False,
                "error": f"Local admin info not found: {serial_number}"
            }), 404

        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api.route('/tools/get_defender_status/<serial_number>', methods=['GET'])
@require_api_key
def route_get_defender_status(serial_number):
    """Get Microsoft Defender status for a machine."""
    try:
        db = get_db()

        query = """
            SELECT
                healthy,
                licensed,
                real_time_protection_enabled,
                real_time_protection_available,
                real_time_protection_subsystem,
                cloud_enabled,
                cloud_automatic_sample_submission,
                cloud_diagnostic_enabled,
                definitions_version,
                definitions_updated,
                app_version,
                engine_version,
                org_id,
                machine_guid,
                release_ring,
                log_level
            FROM ms_defender
            WHERE serial_number = ?
        """

        result = db.execute_single(query, (serial_number,))

        if result is None:
            return jsonify({
                "success": False,
                "error": f"Defender status not found: {serial_number}"
            }), 404

        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api.route('/tools/get_storage_report/<serial_number>', methods=['GET'])
@require_api_key
def route_get_storage_report(serial_number):
    """Get storage/disk report for a machine."""
    try:
        db = get_db()

        query = """
            SELECT
                volumename,
                mountpoint,
                totalsize,
                freespace,
                percentage,
                volumetype,
                media_type,
                encrypted,
                smartstatus,
                internal,
                busprotocol
            FROM diskreport
            WHERE serial_number = ?
            ORDER BY internal DESC, mountpoint
        """

        result = db.execute_query(query, (serial_number,))

        return jsonify({
            "success": True,
            "data": result,
            "count": len(result)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
