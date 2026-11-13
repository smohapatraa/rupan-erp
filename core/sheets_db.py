"""Google Sheets as database — complete wrapper with insert_row returning saved record."""
import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from gspread.exceptions import APIError
from datetime import datetime
import io

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

class ConcurrentEditError(Exception):
    pass


@st.cache_resource
def get_client():
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=SCOPES
    )
    return gspread.authorize(creds)


@st.cache_resource
def get_spreadsheet():
    return get_client().open_by_key(st.secrets["google"]["sheet_id"])


@st.cache_resource
def get_drive():
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def get_worksheet(tab_name: str):
    return get_spreadsheet().worksheet(tab_name)


# ---------- READ ----------

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type(APIError),
)
def read_table(tab_name: str) -> pd.DataFrame:
    ws = get_worksheet(tab_name)
    data = ws.get_all_records()
    return pd.DataFrame(data)


def list_all(tab_name: str, only_active: bool = False) -> list:
    """Return list of dicts for all rows. Optionally filter to Active=TRUE."""
    df = read_table(tab_name)
    if df.empty:
        return []
    rows = df.to_dict(orient="records")
    if only_active:
        # Check for Active or Active? column
        for col in ("Active", "active", "Is Active", "is_active"):
            if col in df.columns:
                rows = [
                    r for r in rows
                    if str(r.get(col, "")).upper() in ("TRUE", "1", "YES", "Y")
                ]
                break
    return rows


# ---------- WRITE ----------

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type(APIError),
)
def append_row(tab_name: str, row_dict: dict) -> None:
    ws = get_worksheet(tab_name)
    headers = ws.row_values(1)
    row = [row_dict.get(h, "") for h in headers]
    ws.append_row(row, value_input_option="RAW")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type(APIError),
)
def get_next_id(tab_name: str, id_col: str) -> int:
    df = read_table(tab_name)
    if df.empty or id_col not in df.columns:
        return 1
    try:
        return int(pd.to_numeric(df[id_col], errors="coerce").max()) + 1
    except Exception:
        return 1


def insert_row(tab_name: str, data: dict, user_id=None) -> dict:
    """
    Insert a row and RETURN the saved record (with generated ID).
    This is the fix for the NoneType error.
    """
    ws = get_worksheet(tab_name)
    headers = ws.row_values(1)

    # 1. Generate ID for the first column
    id_col = headers[0]
    next_id = get_next_id(tab_name, id_col)
    data[id_col] = next_id

    # 2. Stamp audit fields if they exist
    now = datetime.now().isoformat(timespec="seconds")
    if "entered_by" in headers and user_id and not data.get("entered_by"):
        data["entered_by"] = user_id
    if "entered_on" in headers and not data.get("entered_on"):
        data["entered_on"] = now
    if "last_modified" in headers:
        data["last_modified"] = now

    # 3. Build row in exact header order
    row = [data.get(h, "") for h in headers]
    ws.append_row(row, value_input_option="RAW")

    # 4. Return the saved record — FIX for saved_purchase["Purchase ID"]
    return data


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type(APIError),
)
def update_row(tab_name: str, key_col: str, key_val, updates: dict) -> None:
    ws = get_worksheet(tab_name)
    headers = ws.row_values(1)
    if key_col not in headers:
        raise ValueError(f"{key_col} not in {tab_name}")
    key_idx = headers.index(key_col) + 1
    all_rows = ws.get_all_values()
    target_row = None
    for i, row in enumerate(all_rows[1:], start=2):
        if row[key_idx - 1] == str(key_val):
            target_row = i
            break
    if not target_row:
        raise ValueError(f"{key_col}={key_val} not found in {tab_name}")

    updates["last_modified"] = datetime.now().isoformat(timespec="seconds")

    cells = []
    for col_name, val in updates.items():
        if col_name in headers:
            col_idx = headers.index(col_name) + 1
            cells.append(gspread.Cell(target_row, col_idx, val))
    if cells:
        ws.update_cells(cells, value_input_option="RAW")


# ---------- GOOGLE DRIVE ----------

def upload_invoice_to_drive(file_bytes: bytes, filename: str, folder_id: str,
                             mime_type: str = "application/pdf") -> str:
    """Upload file to Drive, return the view link (string)."""
    drive = get_drive()
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=False)
    file_meta = {"name": filename, "parents": [folder_id]}
    created = drive.files().create(
        body=file_meta,
        media_body=media,
        fields="id, webViewLink",
        supportsAllDrives=True,
    ).execute()
    return created.get("webViewLink", "")


def clear_cache():
    st.cache_data.clear()
