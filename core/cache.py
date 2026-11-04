# core/cache.py
"""
Caching wrappers around sheets_db read functions.
"""

from __future__ import annotations

from typing import Any, Optional

import streamlit as st

from core import sheets_db


@st.cache_resource(show_spinner=False)
def get_client():
    """Cache the authorized gspread client. Auth handshake happens once."""
    return sheets_db.get_client()


@st.cache_resource(show_spinner=False)
def get_spreadsheet():
    """Cache the opened spreadsheet object."""
    return sheets_db.get_spreadsheet()


@st.cache_data(ttl="5m", show_spinner=False)
def healthcheck() -> dict[str, Any]:
    """Cached healthcheck. Re-runs at most every 5 minutes."""
    return sheets_db.healthcheck()


@st.cache_data(ttl="30s", show_spinner=False)
def load_all(tab: str, only_active: bool = False) -> list[dict[str, Any]]:
    """Cached list_all."""
    return sheets_db.list_all(tab, only_active=only_active)


@st.cache_data(ttl="30s", show_spinner=False)
def load_row(tab: str, record_id: str) -> Optional[dict[str, Any]]:
    """Cached get_row for a single record."""
    return sheets_db.get_row(tab, record_id)


@st.cache_data(ttl="30s", show_spinner=False)
def load_by(tab: str, filters: tuple[tuple[str, str], ...] = ()) -> list[dict[str, Any]]:
    """Cached find_rows."""
    return sheets_db.find_rows(tab, dict(filters) if filters else None)


def invalidate() -> None:
    """Clear all cached reads so the next load reflects the latest writes."""
    st.cache_data.clear()
