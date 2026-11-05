import streamlit as st
import pandas as pd
from core import sheets_db
from core import auth

# 1. Security Check
auth.require_login()
user = auth.current_user()

st.title("🏢 Party Master")

# 2. Create layout with Tabs
tab_view, tab_add = st.tabs(["View Parties", "Add New Party"])

# --- TAB 1: VIEW & MANAGE ---
with tab_view:
    with st.spinner("Loading parties..."):
        # Fetch all parties from Google Sheets
        parties = sheets_db.list_all("party_master")
    
    if not parties:
        st.info("No parties found. Add one in the 'Add New Party' tab.")
    else:
        # Convert to DataFrame for a nice table
        df = pd.DataFrame(parties)
        
        # Display the table
        st.dataframe(
            df[["Party ID", "Party Name", "Contact", "GSTIN", "Active"]], 
            use_container_width=True,
            hide_index=True
        )
        
        st.divider()
        st.subheader("Manage Party")
        
        # Select a party to edit or delete
        party_ids = [p["Party ID"] for p in parties if p.get("Active") == "TRUE"]
        selected_id = st.selectbox("Select a Party to Edit/Deactivate", [""] + party_ids)
        
        if selected_id:
            # Find the specific party data
            party_data = next((p for p in parties if p["Party ID"] == selected_id), None)
            
            with st.form("edit_party_form"):
                st.write(f"Editing: **{selected_id}**")
                edit_name = st.text_input("Party Name", value=party_data.get("Party Name", ""))
                edit_contact = st.text_input("Contact", value=party_data.get("Contact", ""))
                edit_address = st.text_input("Address", value=party_data.get("Address", ""))
                edit_gstin = st.text_input("GSTIN", value=party_data.get("GSTIN", ""))
                
                col1, col2 = st.columns(2)
                with col1:
                    save_btn = st.form_submit_button("💾 Save Changes", use_container_width=True)
                with col2:
                    delete_btn = st.form_submit_button("🗑️ Deactivate Party", use_container_width=True, type="primary")
                
                if save_btn:
                    with st.spinner("Saving..."):
                        sheets_db.update_row("party_master", selected_id, {
                            "Party Name": edit_name,
                            "Contact": edit_contact,
                            "Address": edit_address,
                            "GSTIN": edit_gstin
                        }, user_id=user["User ID"])
                    st.success("Party updated successfully!")
                    st.rerun()
                    
                if delete_btn:
                    with st.spinner("Deactivating..."):
                        sheets_db.delete_row("party_master", selected_id, user_id=user["User ID"])
                    st.warning("Party deactivated.")
                    st.rerun()

# --- TAB 2: ADD NEW PARTY ---
with tab_add:
    st.subheader("Add a New Party")
    
    with st.form("add_party_form", clear_on_submit=True):
        new_name = st.text_input("Party Name *")
        new_contact = st.text_input("Contact Number")
        new_address = st.text_input("Address")
        new_gstin = st.text_input("GSTIN")
        
        submit = st.form_submit_button("➕ Add Party", use_container_width=True)
        
        if submit:
            if not new_name:
                st.error("Party Name is required.")
            else:
                with st.spinner("Adding to database..."):
                    new_party = sheets_db.insert_row("party_master", {
                        "Party Name": new_name,
                        "Contact": new_contact,
                        "Address": new_address,
                        "GSTIN": new_gstin,
                        "Active": "TRUE"
                    }, user_id=user["User ID"])
                st.success(f"Added {new_party['Party Name']} with ID {new_party['Party ID']}!")
                st.rerun()
