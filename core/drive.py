"""Google Drive — upload + view invoice PDFs."""
import io
import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.service_account import Credentials
from .config import INVOICE_FOLDER_ID, get_gcp_credentials_dict

SCOPES = ["https://www.googleapis.com/auth/drive"]

@st.cache_resource
def get_drive():
    creds = Credentials.from_service_account_info(get_gcp_credentials_dict(), scopes=SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def upload_invoice(file_bytes: bytes, filename: str, mime: str = "application/pdf") -> dict:
    drive = get_drive()
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime, resumable=False)
    file_meta = {"name": filename, "parents": [INVOICE_FOLDER_ID()]}
    created = drive.files().create(
        body=file_meta, media_body=media,
        fields="id, webViewLink, webContentLink",
        supportsAllDrives=True,
    ).execute()
    return {
        "file_id": created["id"],
        "view_link": created.get("webViewLink", ""),
        "download_link": created.get("webContentLink", ""),
    }

def download_invoice(file_id: str) -> bytes:
    drive = get_drive()
    return drive.files().get_media(fileId=file_id, supportsAllDrives=True).execute()
