# core/sheets_db.py
from __future__ import annotations
import json
import os
import threading
from datetime import datetime
from typing import Any, Optional
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st  # We need this for the debug prints

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
    st.write("DEBUG: Loading credentials...")
    try:
        if "gcp_service_account" in st.secrets:
            info = dict(st.secrets["gcp_service_account"])
            st.write("DEBUG: Found st.secrets['gcp_service_account']")
            return Credentials.from_service_account_info(info, scopes=_SCOPES)
    except Exception as e:
        st.write(f"DEBUG ERROR loading secrets: {e}")
        
    path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if path and os.path.isfile(path):
        return Credentials.from_service_account_file(path, scopes=_SCOPES)
    fallback = os.path.join(os.getcwd(), "service_account.json")
    if os.path.isfile(fallback):
        return Credentials.from_service_account_file(fallback, scopes=_SCOPES)
    raise RuntimeError("No credentials found")

def _get_spreadsheet_name() -> str:
    try:
        if "spreadsheet_name" in st.secrets:
            return str(st.secrets["spreadsheet_name"])
    except Exception:
        pass
    return os.environ.get("SPREADSHEET_NAME", "Rupan ERP Data")

def get_client() -> gspread.Client:
    global _client
    with _client_lock:
        if _client is None:
            st.write("DEBUG: Authorizing gspread client...")
            _client = gspread.authorize(_load_credentials())
        return _client

def get_spreadsheet() -> gspread.Spreadsheet:
    global _spreadsheet
    with _client_lock:
        if _spreadsheet is None:
            name = _get_spreadsheet_name()
            st.write(f"DEBUG: Opening spreadsheet '{name}'...")
            _spreadsheet = get_client().open(name)
            st.write("DEBUG: Spreadsheet opened successfully.")
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
    """Verify every tab's header row. WITH DEBUG PRINTS."""
    tabs_to_check = [tab] if tab else list(SCHEMA)
    errors: list[str] = []

    st.write("DEBUG: Getting spreadsheet object...")
    try:
        sh = get_spreadsheet()
    except Exception as e:
        st.write(f"DEBUG ERROR getting spreadsheet: {e}")
        raise

    st.write("DEBUG: Fetching worksheet list (this is where it usually hangs)...")
    try:
        all_worksheets = {ws.title: ws for ws in sh.worksheets()}
        st.write(f"DEBUG: Found {len(all_worksheets)} tabs.")
    except Exception as e:
        st.write(f"DEBUG ERROR fetching worksheets: {e}")
        raise

    for name in tabs_to_check:
        st.write(f"DEBUG: Checking headers for tab '{name}'...")
        expected = SCHEMA[name]
        
        if name not in all_worksheets:
            errors.append(f"[{name}] tab is missing from the spreadsheet.")
            continue

        try:
            ws = all_worksheets[name]
            actual = ws.row_values(1)
            while actual and actual[-1] == "":
                actual.pop()

            if actual != expected:
                missing = [h for h in expected if h not in actual]
                extra = [h for h in actual if h not in expected]
                msg = f"[{name}] header mismatch."
                if missing: msg += f" Missing: {missing}."
                if extra: msg += f" Extra: {extra}."
                if not missing and not extra: msg += " Same columns but wrong order."
                errors.append(msg)
                st.write(f"DEBUG: Mismatch found in '{name}'")
        except Exception as e:
            errors.append(f"[{name}] error reading headers: {e}")
            st.write(f"DEBUG ERROR reading headers for '{name}': {e}")

    st.write("DEBUG: Finished checking all headers.")
    if errors:
        raise RuntimeError("Schema validation failed:\n  " + "\n  ".join(errors))

# ... [Keep the rest of the file exactly the same as before: _header_map, now_iso, _next_id, _row_to_dict, _dict_to_row, insert_row, get_row, find_rows, _row_number_of, update_row, delete_row, _record_id_of, log_audit, list_all, healthcheck] ...
# COPY THE REST OF THE FILE FROM YOUR CURRENT VERSION DOWN BELOW THIS LINE
