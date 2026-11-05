import streamlit as st
import pandas as pd
from core import sheets_db
from core import auth

auth.require_login()
user = auth.current_user()

# Security Check: Only Admins can see this page
if user.get("Role") != "admin":
    st.error("⛔ Access Denied. Only Admins can manage users.")
    st.stop()

st.title("👥 User Management")

tab_view, tab_add = st.tabs(["Manage Users", "Add New User"])

# --- TAB 1: VIEW & MANAGE USERS ---
with tab_view:
    with st.spinner("Loading users..."):
        users = sheets_db.list_all("users")
        
    if not users:
        st.info("No users found.")
    else:
        df = pd.DataFrame(users)
        # We don't display the Password Hash for security
        st.dataframe(
            df[["User ID", "Username", "Role", "Active", "Created At"]], 
            use_container_width=True, 
            hide_index=True
        )
        
        st.divider()
        st.subheader("Edit User Role or Status")
        
        # Don't allow the admin to deactivate themselves
        usernames = [u["Username"] for u in users if u["Username"] != user["Username"]]
        selected_user = st.selectbox("Select User", [""] + usernames)
        
        if selected_user:
            row = next((u for u in users if u["Username"] == selected_user), None)
            
            with st.form("edit_user"):
                st.write(f"Editing: **{selected_user}**")
                
                # Dropdown for Role
                roles = ["admin", "manager", "operator"]
                current_role = row.get("Role", "operator")
                role_index = roles.index(current_role) if current_role in roles else 2
                new_role = st.selectbox("Role", roles, index=role_index)
                
                # Toggle for Active
                is_active = str(row.get("Active", "TRUE")).upper() == "TRUE"
                new_active = st.checkbox("Account Active", value=is_active)
                
                if st.form_submit_button("💾 Save Changes", use_container_width=True):
                    sheets_db.update_row("users", row["User ID"], {
                        "Role": new_role,
                        "Active": "TRUE" if new_active else "FALSE"
                    }, user_id=user["User ID"])
                    st.success("User updated!")
                    st.rerun()

# --- TAB 2: ADD NEW USER ---
with tab_add:
    st.subheader("Create a New User")
    
    with st.form("add_user_form", clear_on_submit=True):
        new_username = st.text_input("Username * (no spaces)")
        new_password = st.text_input("Password *", type="password")
        
        roles = ["manager", "operator", "admin"]
        new_role = st.selectbox("Role", roles)
        
        submit = st.form_submit_button("➕ Create User", use_container_width=True)
        
        if submit:
            if not new_username or not new_password:
                st.error("Username and Password are required.")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters.")
            elif " " in new_username:
                st.error("Username cannot contain spaces.")
            else:
                with st.spinner("Creating user..."):
                    # Check if user exists
                    if sheets_db.find_rows("users", {"Username": new_username}):
                        st.error(f"User '{new_username}' already exists.")
                    else:
                        auth.create_user(
                            username=new_username,
                            password=new_password,
                            role=new_role,
                            created_by=user["Username"]
                        )
                        st.success(f"User '{new_username}' created successfully!")
