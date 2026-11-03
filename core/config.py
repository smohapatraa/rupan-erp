"""Load config from Streamlit secrets."""
import streamlit as st

def get_secret(section: str, key: str, default=None):
    try:
        return st.secrets[section][key]
    except (KeyError, FileNotFoundError):
        return default

APP_SECRET = lambda: get_secret("app", "secret_key")
COOKIE_NAME = lambda: get_secret("app", "cookie_name", "rupan_erp_auth")
COOKIE_EXPIRY = lambda: get_secret("app", "cookie_expiry_days", 1)

SHEET_ID = lambda: get_secret("google", "sheet_id")
INVOICE_FOLDER_ID = lambda: get_secret("google", "invoice_folder_id")
BACKUP_FOLDER_ID = lambda: get_secret("google", "backup_folder_id")

def get_gcp_credentials_dict() -> dict:
    return dict(st.secrets["gcp_service_account"])
