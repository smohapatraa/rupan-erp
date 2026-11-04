import streamlit as st
from core import auth
from core import sheets_db

# 1. Page Configuration
st.set_page_config(
    page_title="Rupan ERP",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Initialize Session State
if "user" not in st.session_state:
    st.session_state["user"] = None

# 3. Login Screen
if st.session_state["user"] is None:
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<h1 style='text-align: center;'>Rupan ERP</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Purchase Management System</p>", unsafe_allow_html=True)
        st.divider()
        
        with st.form("login_form"):
            st.subheader("Login")
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submit = st.form_submit_button("Sign In", use_container_width=True)
            
            if submit:
                if not username or not password:
                    st.error("Please enter both username and password.")
                else:
                    with st.spinner("Authenticating..."):
                        user = auth.login(username, password)
                        if user:
                            st.session_state["user"] = user
                            st.rerun()
                        else:
                            st.error("Invalid username or password, or account is inactive.")
                            
    # Stop the app here so the dashboard doesn't load
    st.stop()

# 4. If we get here, the user is logged in!
user = st.session_state["user"]

# Sidebar
with st.sidebar:
    st.title("🌾 Rupan ERP")
    st.write(f"Logged in as: **{user.get('Username')}**")
    st.write(f"Role: {user.get('Role')}")
    st.divider()
    
    if st.button("Logout", use_container_width=True):
        auth.logout()

# Main Dashboard (Temporary)
st.title("Dashboard")
st.success(f"Welcome, {user.get('Username')}! You are successfully logged in.")

st.write("Here is where the ERP modules will go:")
st.write("- **Purchases** (Coming Next)")
st.write("- **Party Master**")
st.write("- **Item Master**")
st.write("- **Reports**")

# Quick DB Healthcheck to prove connection
with st.expander("System Status"):
    try:
        # We don't want to hit the API every time, but just to show it works
        if st.button("Run DB Healthcheck"):
            with st.spinner("Checking..."):
                hc = sheets_db.healthcheck()
                if hc.get("status") == "ok":
                    st.success("Database connected successfully!")
                else:
                    st.error(f"DB Error: {hc.get('message')}")
    except Exception as e:
        st.error(f"Error: {e}")
