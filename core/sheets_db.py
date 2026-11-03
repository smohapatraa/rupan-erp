"""Google Sheets as database — gspread wrapper with locking + retry."""
import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from gspread.exceptions import APIError
from datetime import datetime
from .config import SHEET_ID, get_gcp_credentials_dict

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

class ConcurrentEditError(Exception):
    pass

@st.cache_resource
def get_client():
    creds = Credentials.from_service_account_info(get_gcp_credentials_dict(), scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_resource
def get_spreadsheet():
    return get_client().open_by_key(SHEET_ID())

def get_worksheet(tab_name: str):
    return get_spreadsheet().worksheet(tab_name)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type(APIError),
)
def read_table(tab_name: str) -> pd.DataFrame:
    ws = get_worksheet(tab_name)
    data = ws.get_all_records()
    return pd.DataFrame(data)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5),
       retry=retry_if_exception_type(APIError))
def append_row(tab_name: str, row_dict: dict) -> None:
    ws = get_worksheet(tab_name)
    headers = ws.row_values(1)
    row = [row_dict.get(h, "") for h in headers]
    ws.append_row(row, value_input_option="RAW")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5),
       retry=retry_if_exception_type(APIError))
def update_row(tab_name: str, key_col: str, key_val, updates: dict,
               expected_version: int = None, version_col: str = "version") -> None:
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

    if expected_version is not None and version_col in headers:
        ver_idx = headers.index(version_col)
        current_ver = int(all_rows[target_row - 1][ver_idx] or 0)
        if current_ver != expected_version:
            raise ConcurrentEditError(
                f"Row was modified. Expected version {expected_version}, found {current_ver}."
            )
        updates[version_col] = expected_version + 1

    updates["last_modified"] = datetime.now().isoformat(timespec="seconds")

    cells = []
    for col_name, val in updates.items():
        if col_name in headers:
            col_idx = headers.index(col_name) + 1
            cells.append(gspread.Cell(target_row, col_idx, val))
    if cells:
        ws.update_cells(cells, value_input_option="RAW")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5),
       retry=retry_if_exception_type(APIError))
def get_next_id(tab_name: str, id_col: str) -> int:
    df = read_table(tab_name)
    if df.empty or id_col not in df.columns:
        return 1
    try:
        return int(df[id_col].astype(int).max()) + 1
    except Exception:
        return 1

def clear_cache():
    st.cache_data.clear()
