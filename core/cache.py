# core/cache.py
"""
Caching wrappers around sheets_db read functions.

Why this exists:
  Streamlit reruns app.py on EVERY interaction (button click, text input,
  page switch). Without caching, every rerun hits the Google Sheets API,
  which:
    - adds 200-800ms per API call,
    - burns the 60 reads/minute per-user quota,
    - and makes the whole app feel frozen.

How it works:
  - @st.cache_resource caches the gspread client (auth happens once).
  - @st.cache_data caches list/read results for a short TTL.
  - Call invalidate() after any insert/update/delete so the next read
    is fresh.

Usage in pages:
    from core.cache import load_all, invalidate

    parties = load_all("party_master", only_active=True)
    # ... user edits something ...
    sheets_db.update_row(...)
    invalidate("party_master")
"""

from __future__ import annotations

from typing import Any, Optional

import streamlit as st

from core import sheets_db


# --------------------------------------------------------------------------- #
# Connection (cached for the lifetime of the process)
# --------------------------------------------------------------------------- #

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
    """
    Cached healthcheck. Re-runs at most every 5 minutes instead of on
    every page load (previously made ~11 API calls per rerun).
    """
    return sheets_db.healthcheck()


# --------------------------------------------------------------------------- #
# Reads
# --------------------------------------------------------------------------- #

@st.cache_data(ttl="30s", show_spinner=False)
def load_all(tab: str, only_active: bool = False) -> list[dict[str, Any]]:
    """
    Cached list_all. Returns a list of dicts (rows).
    TTL is 30 seconds -- short enough that edits made by other users
    appear quickly, long enough that a single page session only hits
    the API once or twice.
    """
    return sheets_db.list_all(tab, only_active=only_active)


@st.cache_data(ttl="30s", show_spinner=False)
def load_row(tab: str, record_id: str) -> Optional[dict[str, Any]]:
    """Cached get_row for a single record."""
    return sheets_db.get_row(tab, record_id)


@st.cache_data(ttl="30s", show_spinner=False)
def load_by(tab: str, filters: tuple[tuple[str, str], ...] = ()) -> list[dict[str, Any]]:
    """
    Cached find_rows. Filters must be a tuple of (key, value) pairs so
    the arguments are hashable (dicts are not hashable, so we can't pass
    a dict directly to a cached function).
    """
    return sheets_db.find_rows(tab, dict(filters) if filters else None)


# --------------------------------------------------------------------------- #
# Cache invalidation
# --------------------------------------------------------------------------- #

def invalidate(tab: Optional[str] = None) -> None:
    """
    Clear cached reads so the next load reflects the latest writes.

    Call after ANY insert_row / update_row / delete_row.

    If tab is None -> clear everything (use after bulk operations).
    If tab is set -> clear only that tab's caches (keeps other tabs warm).
    """
    # st.cache_data.clear() clears ALL cached data functions.
    # For per-tab invalidation, Streamlit doesn't support that granularly
    # via the public API, so we clear all -- it's cheap.
    st.cache_data.clear()
