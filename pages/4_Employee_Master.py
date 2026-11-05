import streamlit as st
import pandas as pd
from core import sheets_db
from core import auth

auth.require_login()
user = auth.current_user()

st.title("👷 Employee Master")

tab_view, tab_add = st.tabs(["View Employees", "Add New Employee"])

# --- TAB 1: VIEW & MANAGE ---
with tab_view:
    with st.spinner("Loading employees..."):
        data = sheets_db.list_all("employee_master")
    
    if not data:
        st.info("No employees found. Add one in the 'Add New Employee' tab.")
    else:
        df = pd.DataFrame(data)
        st.dataframe(
            df[["Employee ID", "Name", "Role", "Contact", "Active"]], 
            use_container_width=True, 
            hide_index=True
        )
        
        st.divider()
        st.subheader("Manage Employee")
        
        ids = [d["Employee ID"] for d in data if d.get("Active") == "TRUE"]
        selected_id = st.selectbox("Select an Employee", [""] + ids)
        
        if selected_id:
            row = next((d for d in data if d["Employee ID"] == selected_id), None)
            
            with st.form("edit_emp"):
                st.write(f"Editing: **{selected_id}**")
                name = st.text_input("Name", value=row.get("Name", ""))
                role = st.text_input("Role", value=row.get("Role", ""))
                contact = st.text_input("Contact", value=row.get("Contact", ""))
                
                c1, c2 = st.columns(2)
                if c1.form_submit_button("💾 Save Changes", use_container_width=True):
                    sheets_db.update_row("employee_master", selected_id, {
                        "Name": name, "Role": role, "Contact": contact
                    }, user_id=user["User ID"])
                    st.success("Updated!")
                    st.rerun()
                    
                if c2.form_submit_button("🗑️ Deactivate", type="primary", use_container_width=True):
                    sheets_db.delete_row("employee_master", selected_id, user_id=user["User ID"])
                    st.warning("Employee deactivated.")
                    st.rerun()

# --- TAB 2: ADD NEW ---
with tab_add:
    st.subheader("Add New Employee")
    with st.form("add_emp", clear_on_submit=True):
        name = st.text_input("Name *")
        role = st.text_input("Role (e.g. Manager, Operator)")
        contact = st.text_input("Contact")
        
        if st.form_submit_button("➕ Add Employee", use_container_width=True):
            if not name:
                st.error("Name is required.")
            else:
                with st.spinner("Adding..."):
                    sheets_db.insert_row("employee_master", {
                        "Name": name, 
                        "Role": role, 
                        "Contact": contact, 
                        "Active": "TRUE"
                    }, user_id=user["User ID"])
                st.success("Added successfully!")
                st.rerun()
