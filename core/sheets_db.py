# core/sheets_db.py
from __future__ import annotations
import json
from datetime import datetime
from typing import Any, Optional
import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCHEMA: dict[str, list[str]] = {
    "users": ["User ID", "Username", "Password Hash", "Role", "Active", "Created At"],
    "farm_master": ["Farm ID", "Farm Name", "Location", "Owner", "Contact", "Active", "Created At"],
    "party_master": ["Party ID", "Party Name", "Contact", "Address", "GSTIN", "Active", "Created At"],
    "item_master": ["Item ID", "Item Name", "Unit", "Default Price", "Active", "Created At"],
    "transporter_master": ["Transporter ID", "Name", "Contact", "Vehicle Count", "Active", "Created At"],
    "employee_master": ["Employee ID", "Name", "Role", "Contact", "Active", "Created At"],
    "purchases": ["Purchase ID", "Month", "Year", "Date", "Invoice no", "Party ID", "Party name", "Item ID", "Item", "Moisture %", "Qty", "Unit", "price", "Amount", "CGST", "SGST", "IGST", "ROUND OFF", "Total amount", "Moisture Qty", "Actual Qty", "Employee ID", "Employee Name", "Transport Type", "Vehicle No", "Transporter ID", "Transporter Name", "Starting Km", "End Km", "Km covered", "Transportation Amount", "Other Charges", "Places Visited", "Created At"],
    "purchase_items": ["Line ID", "Purchase ID", "Item ID", "Item", "Qty", "Unit", "price", "Amount", "Moisture %", "Moisture Qty", "Actual Qty", "CGST", "SGST", "IGST", "ROUND OFF", "Total amount"],
    "audit_log": ["Log ID", "Timestamp", "User ID", "Action", "Table", "Record ID", "Old Value", "New Value"],
    "config": ["Key", "Value", "Description", "Updated At"],
    "state_master": ["State ID", "State Name", "State Code", "Active"],
}

ID_SPEC: dict[str, tuple[str, str]] = {
    "users": ("USR", "User ID"), "farm_master": ("FRM", "Farm ID"), "party_master": ("PTY", "Party ID"),
    "item_master": ("ITM", "Item ID"), "transporter_master": ("TRN", "Transporter ID"),
    "employee_master": ("EMP", "Employee ID"), "purchases": ("PUR", "Purchase ID"),
    "purchase_items": ("PIT", "Line ID"), "audit_log": ("LOG", "Log ID"), "state_master": ("STM", "State ID"),
}

AUTO_COLUMNS = {"Created At", "Updated At", "Timestamp"}
ID_COLUMNS = {col for _, col in ID_SPEC.values()}
_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_service():
    if "gcp_service_account" not in st.secrets:
        raise RuntimeError("gcp_service_account missing in Streamlit Secrets!")
    info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(info, scopes=_SCOPES)
    return build('sheets', 'v4', credentials=creds, cache_discovery=False)

def _get_sheet_id() -> str:
    sid = st.secrets.get("sheet_id")
    if not sid: raise RuntimeError("sheet_id missing in Secrets!")
    return sid

def _get_sheet_data(tab: str) -> list[list[str]]:
    service = get_service()
    sheet_id = _get_sheet_id()
    # Get all values from the tab
    result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=tab).execute()
    return result.get('values', [])

def get_worksheet_headers(tab: str) -> list[str]:
    data = _get_sheet_data(tab)
    return data[0] if data else []

def ensure_headers(tab: Optional[str] = None) -> None:
    tabs = [tab] if tab else list(SCHEMA)
    for t in tabs:
        actual = get_worksheet_headers(t)
        if actual != SCHEMA[t]:
            raise RuntimeError(f"[{t}] Header mismatch. Expected {SCHEMA[t]}, got {actual}")

def _row_to_dict(headers, row):
    padded = list(row) + [""] * (len(headers) - len(row))
    return dict(zip(headers, padded[: len(headers)]))

def _dict_to_row(headers, data):
    out = []
    for h in headers:
        v = data.get(h, "")
        if isinstance(v, (dict, list)): v = json.dumps(v, ensure_ascii=False)
        out.append(v if v is not None else "")
    return out

def now_iso(): return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def find_rows(tab: str, filters: Optional[dict] = None) -> list[dict[str, Any]]:
    data = _get_sheet_data(tab)
    if not data: return []
    headers = data[0]
    rows = data[1:]
    out = []
    for r in rows:
        if not any(r): continue
        rec = _row_to_dict(headers, r)
        if filters and not all(str(rec.get(k, "")) == str(v) for k, v in filters.items()):
            continue
        out.append(rec)
    return out

def list_all(tab: str, only_active: bool = False) -> list[dict[str, Any]]:
    rows = find_rows(tab)
    if only_active and rows and "Active" in rows[0]:
        rows = [r for r in rows if str(r.get("Active", "TRUE")).upper() != "FALSE"]
    return rows

def _next_id(tab: str) -> str:
    prefix, col_name = ID_SPEC[tab]
    rows = find_rows(tab)
    max_n = 0
    for r in rows:
        v = r.get(col_name, "")
        if v and "-" in v:
            try:
                n = int(v.split("-")[1])
                if n > max_n: max_n = n
            except: pass
    return f"{prefix}-{max_n + 1:04d}"

def insert_row(tab: str, data: dict[str, Any], user_id: Optional[str] = None, skip_audit: bool = False) -> dict[str, Any]:
    service = get_service()
    sheet_id = _get_sheet_id()
    headers = get_worksheet_headers(tab)
    
    payload = {k: v for k, v in data.items() if k not in AUTO_COLUMNS and k not in ID_COLUMNS}
    for col in headers:
        if col in AUTO_COLUMNS: payload[col] = now_iso()
    if tab in ID_SPEC: payload[ID_SPEC[tab][1]] = _next_id(tab)
    
    row = _dict_to_row(headers, payload)
    
    # Append row using Google API directly
    body = {'values': [row]}
    service.spreadsheets().values().append(
        spreadsheetId=sheet_id, range=tab,
        valueInputOption="USER_ENTERED", body=body
    ).execute()
    
    inserted = _row_to_dict(headers, row)
    if not skip_audit and tab != "audit_log":
        log_audit(user_id or "SYSTEM", "INSERT", tab, _record_id_of(tab, inserted), None, inserted)
    return inserted

def _record_id_of(tab: str, rec: dict[str, Any]) -> str:
    if tab in ID_SPEC: return str(rec.get(ID_SPEC[tab][1], ""))
    if tab == "config": return str(rec.get("Key", ""))
    return ""

def log_audit(user_id: str, action: str, table: str, record_id: str, old: Optional[dict], new: Optional[dict]):
    try:
        payload = {
            "Timestamp": now_iso(), "User ID": user_id, "Action": action, "Table": table, "Record ID": record_id,
            "Old Value": "" if old is None else json.dumps(old, ensure_ascii=False),
            "New Value": "" if new is None else json.dumps(new, ensure_ascii=False),
        }
        insert_row("audit_log", payload, user_id=user_id, skip_audit=True)
    except Exception:
        pass

def get_row(tab: str, record_id: str) -> Optional[dict[str, Any]]:
    if tab not in ID_SPEC: return None
    _, id_col = ID_SPEC[tab]
    matches = find_rows(tab, {id_col: record_id})
    return matches[0] if matches else None

def update_row(tab: str, record_id: str, patch: dict[str, Any], user_id: Optional[str] = None) -> dict[str, Any]:
    service = get_service()
    sheet_id = _get_sheet_id()
    headers = get_worksheet_headers(tab)
    data = _get_sheet_data(tab)
    
    row_num = None
    for i, r in enumerate(data):
        if i == 0: continue
        rec = _row_to_dict(headers, r)
        if rec.get(ID_SPEC[tab][1]) == record_id:
            row_num = i + 1 # 1-based index
            old_row = rec
            break
            
    if not row_num: raise KeyError(f"Record {record_id} not found.")
    
    clean_patch = {k: v for k, v in patch.items() if k in headers and k not in ID_COLUMNS}
    if "Updated At" in headers: clean_patch["Updated At"] = now_iso()
    
    new_row_dict = dict(old_row)
    new_row_dict.update(clean_patch)
    
    # Update specific cells
    for k, v in clean_patch.items():
        col_idx = headers.index(k)
        col_letter = chr(65 + col_idx) # A=65, B=66...
        cell_range = f"{tab}!{col_letter}{row_num}"
        val = json.dumps(v) if isinstance(v, (dict, list)) else v
        body = {'values': [[val]]}
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id, range=cell_range,
            valueInputOption="USER_ENTERED", body=body
        ).execute()
        
    log_audit(user_id or "SYSTEM", "UPDATE", tab, record_id, old_row, new_row_dict)
    return new_row_dict

def delete_row(tab: str, record_id: str, user_id: Optional[str] = None, hard: bool = False) -> None:
    if hard: raise NotImplementedError("Hard delete not supported in raw API yet.")
    # Soft delete = update Active column to FALSE
    update_row(tab, record_id, {"Active": "FALSE"}, user_id)
    log_audit(user_id or "SYSTEM", "SOFT_DELETE", tab, record_id, None, None)

def healthcheck():
    try:
        ensure_headers()
        return {"status": "ok", "message": "Raw Google API connected successfully!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
