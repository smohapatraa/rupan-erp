import streamlit as st
import pandas as pd
from core import sheets_db
from core import auth

# 1. Security Check
auth.require_login()
user = auth.current_user()

st.title("📦 Item Master")

# 2. Tabs
tab_view, tab_add = st.tabs(["View Items", "Add New Item"])

# --- TAB 1: VIEW & MANAGE ---
with tab_view:
    with st.spinner("Loading items..."):
        items = sheets_db.list_all("item_master")
    
    if not items:
        st.info("No items found. Add one in the 'Add New Item' tab.")
    else:
        df = pd.DataFrame(items)
        
        # Display the table
        st.dataframe(
            df[["Item ID", "Item Name", "Unit", "Default Price", "Active"]], 
            use_container_width=True,
            hide_index=True
        )
        
        st.divider()
        st.subheader("Manage Item")
        
        item_ids = [i["Item ID"] for i in items if i.get("Active") == "TRUE"]
        selected_id = st.selectbox("Select an Item to Edit/Deactivate", [""] + item_ids)
        
        if selected_id:
            item_data = next((i for i in items if i["Item ID"] == selected_id), None)
            
            with st.form("edit_item_form"):
                st.write(f"Editing: **{selected_id}**")
                edit_name = st.text_input("Item Name", value=item_data.get("Item Name", ""))
                edit_unit = st.text_input("Unit (e.g. Kg, Bag, Quintal)", value=item_data.get("Unit", ""))
                
                # Handle price safely (it comes as string from Google Sheets)
                try:
                    current_price = float(item_data.get("Default Price", 0))
                except:
                    current_price = 0.0
                    
                edit_price = st.number_input("Default Price", value=current_price, step=1.0)
                
                col1, col2 = st.columns(2)
                with col1:
                    save_btn = st.form_submit_button("💾 Save Changes", use_container_width=True)
                with col2:
                    delete_btn = st.form_submit_button("🗑️ Deactivate Item", use_container_width=True, type="primary")
                
                if save_btn:
                    with st.spinner("Saving..."):
                        sheets_db.update_row("item_master", selected_id, {
                            "Item Name": edit_name,
                            "Unit": edit_unit,
                            "Default Price": str(edit_price)
                        }, user_id=user["User ID"])
                    st.success("Item updated successfully!")
                    st.rerun()
                    
                if delete_btn:
                    with st.spinner("Deactivating..."):
                        sheets_db.delete_row("item_master", selected_id, user_id=user["User ID"])
                    st.warning("Item deactivated.")
                    st.rerun()

# --- TAB 2: ADD NEW ITEM ---
with tab_add:
    st.subheader("Add a New Item")
    
    with st.form("add_item_form", clear_on_submit=True):
        new_name = st.text_input("Item Name *")
        new_unit = st.text_input("Unit * (e.g. Kg, Bag)")
        new_price = st.number_input("Default Price", min_value=0.0, step=1.0)
        
        submit = st.form_submit_button("➕ Add Item", use_container_width=True)
        
        if submit:
            if not new_name or not new_unit:
                st.error("Item Name and Unit are required.")
            else:
                with st.spinner("Adding to database..."):
                    new_item = sheets_db.insert_row("item_master", {
                        "Item Name": new_name,
                        "Unit": new_unit,
                        "Default Price": str(new_price),
                        "Active": "TRUE"
                    }, user_id=user["User ID"])
                st.success(f"Added {new_item['Item Name']} with ID {new_item['Item ID']}!")
                st.rerun()
