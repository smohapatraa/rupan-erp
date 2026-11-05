import streamlit as st
import pandas as pd
from core import sheets_db
from core import auth

auth.require_login()
user = auth.current_user()

st.title("🚚 Transporter Master")

tab_view, tab_add = st.tabs(["View Transporters", "Add New Transporter"])

with tab_view:
    with st.spinner("Loading..."):
        data = sheets_db.list_all("transporter_master")
    
    if not data:
        st.info("No transporters found.")
    else:
        df = pd.DataFrame(data)
        st.dataframe(df[["Transporter ID", "Name", "Contact", "Vehicle Count", "Active"]], use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("Manage Transporter")
        
        ids = [d["Transporter ID"] for d in data if d.get("Active") == "TRUE"]
        selected_id = st.selectbox("Select a Transporter", [""] + ids)
        
        if selected_id:
            row = next((d for d in data if d["Transporter ID"] == selected_id), None)
            
            with st.form("edit_trans"):
                st.write(f"Editing: **{selected_id}**")
                name = st.text_input("Name", value=row.get("Name", ""))
                contact = st.text_input("Contact", value=row.get("Contact", ""))
                vehicles = st.text_input("Vehicle Count", value=row.get("Vehicle Count", "0"))
                
                c1, c2 = st.columns(2)
                if c1.form_submit_button("💾 Save", use_container_width=True):
                    sheets_db.update_row("transporter_master", selected_id, {
                        "Name": name, "Contact": contact, "Vehicle Count": vehicles
                    }, user_id=user["User ID"])
                    st.success("Updated!")
                    st.rerun()
                if c2.form_submit_button("🗑️ Deactivate", type="primary", use_container_width=True):
                    sheets_db.delete_row("transporter_master", selected_id, user_id=user["User ID"])
                    st.rerun()

with tab_add:
    st.subheader("Add New Transporter")
    with st.form("add_trans", clear_on_submit=True):
        name = st.text_input("Name *")
        contact = st.text_input("Contact")
        vehicles = st.text_input("Vehicle Count", value="0")
        
        if st.form_submit_button("➕ Add", use_container_width=True):
            if not name:
                st.error("Name is required.")
            else:
                sheets_db.insert_row("transporter_master", {
                    "Name": name, "Contact": contact, "Vehicle Count": vehicles, "Active": "TRUE"
                }, user_id=user["User ID"])
                st.success("Added successfully!")
                st.rerun()
