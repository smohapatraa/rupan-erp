import streamlit as st
import pandas as pd
from core import sheets_db
from core import auth

auth.require_login()
user = auth.current_user()

st.title("🌾 Farm Master")

tab_view, tab_add = st.tabs(["View Farms", "Add New Farm"])

with tab_view:
    with st.spinner("Loading farms..."):
        data = sheets_db.list_all("farm_master")
    
    if not data:
        st.info("No farms found.")
    else:
        df = pd.DataFrame(data)
        st.dataframe(df[["Farm ID", "Farm Name", "Location", "Owner", "Contact", "Active"]], use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("Manage Farm")
        
        ids = [d["Farm ID"] for d in data if d.get("Active") == "TRUE"]
        selected_id = st.selectbox("Select a Farm", [""] + ids)
        
        if selected_id:
            row = next((d for d in data if d["Farm ID"] == selected_id), None)
            
            with st.form("edit_farm"):
                st.write(f"Editing: **{selected_id}**")
                name = st.text_input("Farm Name", value=row.get("Farm Name", ""))
                location = st.text_input("Location", value=row.get("Location", ""))
                owner = st.text_input("Owner", value=row.get("Owner", ""))
                contact = st.text_input("Contact", value=row.get("Contact", ""))
                
                c1, c2 = st.columns(2)
                if c1.form_submit_button("💾 Save", use_container_width=True):
                    sheets_db.update_row("farm_master", selected_id, {
                        "Farm Name": name, "Location": location, "Owner": owner, "Contact": contact
                    }, user_id=user["User ID"])
                    st.success("Updated!")
                    st.rerun()
                if c2.form_submit_button("🗑️ Deactivate", type="primary", use_container_width=True):
                    sheets_db.delete_row("farm_master", selected_id, user_id=user["User ID"])
                    st.rerun()

with tab_add:
    st.subheader("Add New Farm")
    with st.form("add_farm", clear_on_submit=True):
        name = st.text_input("Farm Name *")
        location = st.text_input("Location")
        owner = st.text_input("Owner")
        contact = st.text_input("Contact")
        
        if st.form_submit_button("➕ Add Farm", use_container_width=True):
            if not name:
                st.error("Farm Name is required.")
            else:
                sheets_db.insert_row("farm_master", {
                    "Farm Name": name, "Location": location, "Owner": owner, "Contact": contact, "Active": "TRUE"
                }, user_id=user["User ID"])
                st.success("Added successfully!")
                st.rerun()
