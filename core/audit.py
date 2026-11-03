"""Append-only audit log."""
from datetime import datetime
from .sheets_db import append_row, get_next_id

def log(username: str, action: str, entity: str, entity_id,
        old_status: str = "", new_status: str = "", details: str = ""):
    try:
        log_id = get_next_id("audit_log", "log_id")
        append_row("audit_log", {
            "log_id": log_id,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "username": username,
            "action": action,
            "entity": entity,
            "entity_id": entity_id,
            "old_status": old_status,
            "new_status": new_status,
            "details": details,
        })
    except Exception as e:
        # Audit must never crash the app
        print(f"Audit log failed: {e}")
