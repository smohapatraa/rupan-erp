import streamlit as st
import pandas as pd
from core import sheets_db
from core import auth

auth.require_login()
user = auth.current_user()

st.title("📊 Purchase Register")

# 1. Load Data
with st.spinner("Loading purchases..."):
    purchases = sheets_db.list_all("purchases")
    purchase_items = sheets_db.list_all("purchase_items")

if not purchases:
    st.info("No purchases recorded yet.")
    st.stop()

df = pd.DataFrame(purchases)

# 2. Filters
st.subheader("Filters")
c1, c2, c3 = st.columns(3)
with c1:
    search_inv = st.text_input("Search Invoice No", "")
with c2:
    search_party = st.text_input("Search Party Name", "")
with c3:
    search_month = st.selectbox("Month", ["All", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])

# Apply filters
filtered_df = df.copy()
if search_inv:
    filtered_df = filtered_df[filtered_df["Invoice no"].str.contains(search_inv, case=False, na=False)]
if search_party:
    filtered_df = filtered_df[filtered_df["Party name"].str.contains(search_party, case=False, na=False)]
if search_month != "All":
    filtered_df = filtered_df[filtered_df["Month"] == search_month]

# 3. Display Table
st.write(f"Showing {len(filtered_df)} records")

display_cols = ["Purchase ID", "Date", "Invoice no", "Party name", "Item", "Qty", "Total amount"]
st.dataframe(
    filtered_df[display_cols], 
    use_container_width=True,
    hide_index=True
)

st.divider()

# 4. View Invoice Details
st.subheader("View Invoice Details")
selected_inv = st.selectbox("Select Purchase ID", [""] + filtered_df["Purchase ID"].tolist())

if selected_inv:
    # Find the header and line items
    row = next((p for p in purchases if p["Purchase ID"] == selected_inv), None)
    items = [i for i in purchase_items if str(i.get("Purchase ID")) == str(selected_inv)]
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.write(f"**Invoice No:** {row.get('Invoice no')}")
        st.write(f"**Date:** {row.get('Date')}")
        st.write(f"**Party:** {row.get('Party name')}")
        st.write(f"**Employee:** {row.get('Employee Name')}")
        st.write(f"**Vehicle:** {row.get('Vehicle No')} | **Transporter:** {row.get('Transporter Name')}")
        st.write(f"**Total Amount:** ₹ {float(row.get('Total amount', 0) or 0):,.2f}")
        
        if row.get("Invoice Link"):
            st.markdown(f"[📄 View Invoice Document]({row['Invoice Link']})")
        else:
            st.write("No invoice attached.")
        
        st.write("**Line Items:**")
        if items:
            df_items = pd.DataFrame(items)
            # Ensure we only show columns that actually exist in the data
            possible_cols = ["Purchase ID", "Line ID", "Item", "Qty", "Unit", "price", "Moisture %", "Actual Qty", "Total amount"]
            display_cols = [c for c in possible_cols if c in df_items.columns]
            st.dataframe(df_items[display_cols], hide_index=True, use_container_width=True)
        else:
            st.warning("No line items found for this Purchase ID.")
            
    with col2:
        st.warning("⚠️ Danger Zone")
        st.write("Deleting a purchase will also delete its line items.")
        
        confirm = st.checkbox("Yes, I want to delete this invoice.")
        if st.button("🗑️ Delete Invoice", type="primary", disabled=not confirm, use_container_width=True):
            with st.spinner("Deleting..."):
                # 1. Hard delete the header
                sheets_db.delete_row("purchases", selected_inv, user_id=user["User ID"], hard=True)
                
                # 2. Hard delete the line items
                for i in items:
                    if "Line ID" in i:
                        sheets_db.delete_row("purchase_items", i["Line ID"], user_id=user["User ID"], hard=True)
                    
            st.success("Invoice deleted successfully!")
            st.rerun()
