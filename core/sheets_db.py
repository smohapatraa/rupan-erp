# core/sheets_db.py
from __future__ import annotations
import json
import os
import threading
from datetime import datetime
from typing import Any, Optional
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st

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
    "users": ("USR", "User ID"),
    "farm_master": ("FRM", "Farm ID"),
    "party_master": ("PTY", "Party ID"),
    "item_master": ("ITM", "Item ID"),
    "transporter_master": ("TRN", "Transporter ID"),
    "employee_master": ("EMP", "Employee ID"),
    "purchases": ("PUR", "Purchase ID"),
    "purchase_items": ("PIT", "Line ID"),
    "audit_log": ("LOG", "Log ID"),
    "state_master": ("STM", "State ID"),
}

AUTO_COLUMNS = {"Created At", "Updated At", "Timestamp"}
ID_COLUMNS = {col for _, col in ID_SPEC.values()}
_SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

_client_lock = threading.Lock()
_client: Optional[gspread.Client] = None
_spreadsheet: Optional[gspread.Spreadsheet] = None

def _load_credentials() -> Credentials:
    st.write("DEBUG: [1] Loading credentials from st.secrets...")
    if "gcp_service_account" not in st.secrets:
        raise RuntimeError("gcp_service_account is missing from Streamlit Secrets!")
    info = dict(st.secrets["gcp_service_account"])
    st.write("DEBUG: [2] Building credentials object...")
    creds = Credentials.from_service_account_info(info, scopes=_SCOPES)
    st.write("DEBUG: [3] Credentials built successfully.")
    return creds

def get_client() -> gspread.Client:
    global _client
    with _client_lock:
        if _client is None:
            st.write("DEBUG: [4] Authorizing gspread client...")
            _client = gspread.authorize(_load_credentials())
            st.write("DEBUG: [5] Client authorized.")
        return _client

def get_spreadsheet() -> gspread.Spreadsheet:
    global _spreadsheet
    with _client_lock:
        if _spreadsheet is None:
            try:
                sheet_id = st.secrets.get("sheet_id")
            except Exception:
                sheet_id = None
                
            if sheet_id:
                st.write(f"DEBUG: [6] Opening spreadsheet by ID: '{sheet_id}'...")
                _spreadsheet = get_client().open_by_key(sheet_id)
            else:
                st.write("DEBUG: [6] Opening spreadsheet by name...")
                name = st.secrets.get("spreadsheet_name", "Rupan ERP Data")
                _spreadsheet = get_client().open(name)
                
            st.write("DEBUG: [7] Spreadsheet opened successfully.")
        return _spreadsheet

def get_worksheet(tab: str) -> gspread.Worksheet:
    if tab not in SCHEMA:
        raise KeyError(f"Unknown tab '{tab}'")
    try:
        return get_spreadsheet().worksheet(tab)
    except gspread.WorksheetNotFound:
        raise RuntimeError(f"Tab '{tab}' does not exist.")

def _invalidate_streamlit_cache() -> None:
    try:
        st.cache_data.clear()
    except Exception:
        pass

def ensure_headers(tab: Optional[str] = None) -> None:
    tabs_to_check = [tab] if tab else list(SCHEMA)
    errors: list[str] = []

    st.write("DEBUG: [8] Getting spreadsheet object...")
    sh = get_spreadsheet()

    st.write("DEBUG: [9] Fetching worksheet list...")
    all_worksheets = {ws.title: ws for ws in sh.worksheets()}
    st.write(f"DEBUG: [10] Found {len(all_worksheets)} tabs.")

    for name in tabs_to_check:
        expected = SCHEMA[name]
        if name not in all_worksheets:
            errors.append(f"[{name}] tab is missing.")
            continue

        ws = all_worksheets[name]
        actual = ws.row_values(1)
        while actual and actual[-1] == "":
            actual.pop()

        if actual != expected:
            errors.append(f"[{name}] header mismatch.")
            st.write(f"DEBUG: Mismatch found in '{name}'")

    st.write("DEBUG: [11] Finished checking headers.")
    if errors:
        raise RuntimeError("Schema validation failed:\n  " + "\n  ".join(errors))

# --- The rest of the functions (insert_row, find_rows, etc.) ---
# (COPY FROM YOUR CURRENT FILE - THEY DON'T NEED CHANGES)

def _header_map(ws): return {name: i + 1 for i, name in enumerate(ws.row_values(1)) if name}
def now_iso(): return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
def _next_id(tab, ws):
    prefix, col_name = ID_SPEC[tab]
    col_idx = _header_map(ws)[col_name]
    values = ws.col_values(col_idx)[1:]
    max_n = max([int(v.split("-")[1]) for v in values if v and "-" in v] + [0])
    return f"{prefix}-{max_n + 1:04d}"

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

def insert_row(tab, data, user_id=None, skip_audit=False):
    ws = get_worksheet(tab)
    headers = ws.row_values(1)
    payload = {k: v for k, v in data.items() if k not in AUTO_COLUMNS and k not in ID_COLUMNS}
    for col in headers:
        if col in AUTO_COLUMNS: payload[col] = now_iso()
    if tab in ID_SPEC: payload[ID_SPEC[tab][1]] = _next_id(tab, ws)
    row = _dict_to_row(headers, payload)
    ws.append_row(row, value_input_option="USER_ENTERED")
    inserted = _row_to_dict(headers, [str(x) for x in row])
    if not skip_audit and tab != "audit_log":
        log_audit(user_id or "SYSTEM", "INSERT", tab, _record_id_of(tab, inserted), None, inserted)
    _invalidate_streamlit_cache()
    return inserted

def get_row(tab, record_id):
    _, id_col = ID_SPEC[tab]
    matches = find_rows(tab, {id_col: record_id})
    return matches[0] if matches else None

def find_rows(tab, filters=None):
    ws = get_worksheet(tab)
    headers = ws.row_values(1)
    all_rows = ws.get_all_values()[1:]
    out = []
    for row in all_rows:
        if not any(row): continue
        rec = _row_to_dict(headers, row)
        if filters:
            if all(str(rec.get(k, "")) == str(v) for k, v in filters.items()):
                out.append(rec)
        else:
            out.append(rec)
    return out

def _row_number_of(tab, record_id):
    _, id_col = ID_SPEC[tab]
    ws = get_worksheet(tab)
    col_idx = _header_map(ws)[id_col]
    for i, v in enumerate(ws.col_values(col_idx)[1:], start=2):
        if v == record_id: return i
    return None

def update_row(tab, record_id, patch, user_id=None):
    ws = get_worksheet(tab)
    headers = ws.row_values(1)
    row_num = _row_number_of(tab, record_id)
    if not row_num: raise KeyError(f"{tab} record '{record_id}' not found.")
    old_row = _row_to_dict(headers, ws.row_values(row_num))
    clean_patch = {k: v for k, v in patch.items() if k in headers and k not in ID_COLUMNS}
    if "Updated At" in headers: clean_patch["Updated At"] = now_iso()
    new_row = dict(old_row)
    new_row.update(clean_patch)
    for k, v in clean_patch.items():
        if k in headers:
            val = json.dumps(v) if isinstance(v, (dict, list)) else v
            ws.update_cell(row_num, headers.index(k) + 1, val)
    log_audit(user_id or "SYSTEM", "UPDATE", tab, record_id, old_row, new_row)
    _invalidate_streamlit_cache()
    return new_row

def delete_row(tab, record_id, user_id=None, hard=False):
    ws = get_worksheet(tab)
    headers = ws.row_values(1)
    row_num = _row_number_of(tab, record_id)
    if not row_num: raise KeyError(f"{tab} record '{record_id}' not found.")
    old_row = _row_to_dict(headers, ws.row_values(row_num))
    if hard: ws.delete_rows(row_num)
    else:
        if "Active" not in headers: raise RuntimeError("No 'Active' column.")
        ws.update_cell(row_num, headers.index("Active") + 1, "FALSE")
    log_audit(user_id or "SYSTEM", "HARD_DELETE" if hard else "SOFT_DELETE", tab, record_id, old_row, None)
    _invalidate_streamlit_cache()

def _record_id_of(tab, rec):
    if tab in ID_SPEC: return str(rec.get(ID_SPEC[tab][1], ""))
    if tab == "config": return str(rec.get("Key", ""))
    return ""

def log_audit(user_id, action, table, record_id, old, new):
    try:
        payload = {
            "Timestamp": now_iso(), "User ID": user_id, "Action": action, "Table": table, "Record ID": record_id,
            "Old Value": "" if old is None else json.dumps(old, ensure_ascii=False),
            "New Value": "" if new is None else json.dumps(new, ensure_ascii=False),
        }
        insert_row("audit_log", payload, user_id=user_id, skip_audit=True)
    except Exception:
        pass

def list_all(tab, only_active=False):
    rows = find_rows(tab)
    if only_active and rows and "Active" in rows[0]:
        rows = [r for r in rows if str(r.get("Active", "TRUE")).upper() != "FALSE"]
    return rows

def healthcheck():
    result = {"credentials": False, "spreadsheet": False, "tabs": {}}
    try:
        get_client()
        result["credentials"] = True
    except Exception as e:
        result["error"] = f"credentials: {e}"
        return result
    try:
        sh = get_spreadsheet()
        result["spreadsheet"] = True
        all_worksheets = {ws.title: ws for ws in sh.worksheets()}
        for tab in SCHEMA:
            if tab not in all_worksheets: result["tabs"][tab] = "missing"
            else:
                header = all_worksheets[tab].row_values(1)
                while header and header[-1] == "": header.pop()
                result["tabs"][tab] = "ok" if header == SCHEMA[tab] else "header-mismatch"
    except Exception as e:
        result["error"] = f"spreadsheet: {e}"
    return result
