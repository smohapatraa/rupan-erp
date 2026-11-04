# core/auth.py
import bcrypt
import streamlit as st
from datetime import datetime
from typing import Optional, Dict, Any

from core import sheets_db

def hash_password(password: str) -> str:
    """Hash a plain text password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Check if a plain text password matches the hash."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

def login(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Attempt to log in. Returns the user dict if successful, None otherwise.
    """
    try:
        users = sheets_db.find_rows("users", {"Username": username})
        if not users:
            return None
            
        user = users[0]
        
        # Check if active
        if str(user.get("Active", "TRUE")).upper() == "FALSE":
            return None
            
        # Verify password
        if verify_password(password, user.get("Password Hash", "")):
            return user
            
        return None
    except Exception as e:
        st.error(f"Login error: {e}")
        return None

def require_login():
    """
    Streamlit guard. Stops the app if the user is not logged in.
    """
    if "user" not in st.session_state:
        st.warning("Please log in to access this page.")
        st.stop()

def current_user() -> Dict[str, Any]:
    """Get the currently logged in user from session state."""
    return st.session_state.get("user", {})

def logout():
    """Log out the current user."""
    if "user" in st.session_state:
        del st.session_state["user"]
    st.rerun()

def create_user(username: str, password: str, role: str = "admin", created_by: str = "SYSTEM") -> bool:
    """
    Create a new user. Used by the bootstrap script.
    """
    # Check if user already exists
    if sheets_db.find_rows("users", {"Username": username}):
        st.warning(f"User '{username}' already exists.")
        return False
        
    hashed_pw = hash_password(password)
    
    try:
        sheets_db.insert_row("users", {
            "Username": username,
            "Password Hash": hashed_pw,
            "Role": role,
            "Active": "TRUE"
        }, user_id=created_by)
        return True
    except Exception as e:
        st.error(f"Failed to create user: {e}")
        return False
