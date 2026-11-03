"""Authentication with bcrypt + streamlit session."""
import bcrypt
import streamlit as st
from datetime import datetime
from .sheets_db import read_table, update_row
from .config import COOKIE_NAME, COOKIE_EXPIRY, APP_SECRET

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False

def authenticate(username: str, password: str):
    df = read_table("users")
    if df.empty:
        return None
    row = df[df["username"] == username]
    if row.empty:
        return None
    user = row.iloc[0].to_dict()
    if str(user.get("is_active", "")).upper() not in ("TRUE", "1", "YES"):
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    try:
        update_row("users", "user_id", user["user_id"],
                   {"last_login": datetime.now().isoformat(timespec="seconds")},
                   expected_version=None)
    except Exception:
        pass
    return user

def login_session(user: dict):
    st.session_state["user"] = {
        "username": user["username"],
        "full_name": user["full_name"],
        "role": user["role"],
        "farm_access": user.get("farm_access", "ALL"),
    }
    st.session_state["logged_in"] = True

def logout():
    for k in ("user", "logged_in"):
        st.session_state.pop(k, None)

def current_user():
    return st.session_state.get("user")

def require_login():
    if not st.session_state.get("logged_in"):
        st.warning("Please log in first.")
        st.switch_page("pages/01_Login.py")
        st.stop()

def require_role(*allowed_roles):
    require_login()
    user = current_user()
    if user["role"] not in allowed_roles:
        st.error(f"Access denied. Required role: {', '.join(allowed_roles)}")
        st.stop()

def has_role(*roles) -> bool:
    user = current_user()
    return user and user["role"] in roles
