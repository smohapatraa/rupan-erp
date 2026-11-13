import streamlit as st
import pandas as pd
from datetime import date
from core import sheets_db
from core import auth

auth.require_login()
user = auth.current_user()

st.title("🧾 Purchase Entry (Multi-Item)")

# 1. Fetch Master Data
with st.spinner("Loading master data..."):
    parties = {p["Party Name"]: p for p in sheets_db.list_all("party_master", only_active=True)}
    items = {i["Item Name"]: i for i in sheets_db.list_all("item_master", only_active=True)}
    employees = {e["Name"]: e for e in sheets_db.list_all("employee_master", only_active=True)}
    transporters = {t["Name"]: t for t in sheets_db.list_all("transporter_master", only_active=True)}

if not parties or not items:
    st.error("You must add at least one Party and one Item in the Master tables.")
    st.stop()

# We use a form so the user can fill everything out without the page refreshing
with st.form("multi_item_purchase_form", clear_on_submit=True):
    
    # --- SECTION 1: INVOICE HEADER ---
    st.subheader("1. Invoice Details")
    c1, c2, c3, c4 = st.columns(4)
    with c1: inv_date = st.date_input("Date", value=date.today())
    with c2: inv_no = st.text_input("Invoice No *")
    with c3: party_name = st.selectbox("Party Name *", list(parties.keys()))
    with c4: employee_name = st.selectbox("Employee Name *", list(employees.keys()) if employees else ["N/A"])

    c1, c2, c3, c4 = st.columns(4)
    with c1: transport_type = st.selectbox("Transport Type", ["By Vehicle", "By Transporter", "Self Pickup"])
    with c2: vehicle_no = st.text_input("Vehicle No")
    with c3: transporter_name = st.selectbox("Transporter Name", ["None"] + list(transporters.keys()))
    with c4: places_visited = st.text_input("Places Visited")

    c1, c2, c3, c4 = st.columns(4)
    with c1: start_km = st.number_input("Starting Km", min_value=0.0, step=1.0)
    with c2: end_km = st.number_input("End Km", min_value=0.0, step=1.0)
    with c3: km_covered = st.number_input("Km Covered", min_value=0.0, step=1.0, value=float(end_km - start_km) if end_km > start_km else 0.0)
    with c4: other_charges = st.number_input("Other Charges (₹)", min_value=0.0, step=1.0)

    invoice_link = st.text_input("Invoice Link (Paste Google Drive / OneDrive link here)")

    st.divider()

    # --- SECTION 2: MULTI-ITEM GRID ---
    st.subheader("2. Line Items")
    st.write("Add items using the table below. Click the '+' at the bottom to add a new row.")
    
    # Create a default empty row for the table
    default_data = pd.DataFrame([
        {"Item": list(items.keys())[0], "Qty": 1.0, "Moisture %": 0.0, "Price": 0.0, "CGST %": 0.0, "SGST %": 0.0, "IGST %": 0.0, "Transport Amt": 0.0}
    ])

    # st.data_editor lets users add/delete rows dynamically
    edited_df = st.data_editor(
        default_data,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Item": st.column_config.SelectboxColumn("Item", options=list(items.keys()), required=True),
            "Qty": st.column_config.NumberColumn("Qty", min_value=0.1, step=1.0, required=True),
            "Moisture %": st.column_config.NumberColumn("Moisture %", min_value=0.0, max_value=100.0, step=0.1),
            "Price": st.column_config.NumberColumn("Price (₹)", min_value=0.0, step=1.0, required=True),
            "CGST %": st.column_config.NumberColumn("CGST %", min_value=0.0, step=0.1),
            "SGST %": st.column_config.NumberColumn("SGST %", min_value=0.0, step=0.1),
            "IGST %": st.column_config.NumberColumn("IGST %", min_value=0.0, step=0.1),
            "Transport Amt": st.column_config.NumberColumn("Transport Amt (₹)", min_value=0.0, step=1.0),
        }
    )

    st.write("")
    submitted = st.form_submit_button("💾 Calculate & Save Invoice", use_container_width=True, type="primary")

# --- PROCESSING LOGIC ---
if submitted:
    if not inv_no:
        st.error("Invoice Number is required.")
        st.stop()
        
    if edited_df.empty:
        st.error("Please add at least one item.")
        st.stop()

    # Calculate totals for the invoice header
    total_base_amount = 0.0
    total_tax = 0.0
    total_transport = 0.0
    
    # Create a list to hold all line items for the purchase_items tab
    line_items_to_save = []
    
    with st.spinner("Processing items and saving..."):
        try:
            # 1. Process each row in the grid
            for index, row in edited_df.iterrows():
                item_name = row["Item"]
                qty = float(row["Qty"])
                moisture_pct = float(row["Moisture %"])
                price = float(row["Price"])
                cgst_pct = float(row["CGST %"])
                sgst_pct = float(row["SGST %"])
                igst_pct = float(row["IGST %"])
                transport_amt = float(row["Transport Amt"])
                
                # Math
                moisture_qty = qty * (moisture_pct / 100.0)
                actual_qty = qty - moisture_qty
                
                # Amount on Gross Qty
                amount = qty * price
                
                cgst_amt = amount * (cgst_pct / 100.0)
                sgst_amt = amount * (sgst_pct / 100.0)
                igst_amt = amount * (igst_pct / 100.0)
                
                row_total = amount + cgst_amt + sgst_amt + igst_amt + transport_amt
                
                # Add to invoice totals
                total_base_amount += amount
                total_tax += (cgst_amt + sgst_amt + igst_amt)
                total_transport += transport_amt
                
                # Prepare line item for the database
                line_items_to_save.append({
                    "Item ID": items[item_name]["Item ID"],
                    "Item": item_name,
                    "Qty": qty,
                    "Unit": items[item_name].get("Unit", "Kg"),
                    "price": price,
                    "Amount": amount,
                    "Moisture %": moisture_pct,
                    "Moisture Qty": moisture_qty,
                    "Actual Qty": actual_qty,
                    "CGST": cgst_amt,
                    "SGST": sgst_amt,
                    "IGST": igst_amt,
                    "Total amount": row_total
                })

            # 2. Calculate Final Invoice Total
            gross_total = total_base_amount + total_tax + total_transport + other_charges
            rounded_total = round(gross_total)
            round_off_diff = rounded_total - gross_total

            # 3. Save the Header (purchases tab)
            # Note: Since we have multiple items, we leave the "Item ID" and "Item" blank in the header
            purchase_data = {
                "Month": inv_date.strftime("%B"), "Year": inv_date.strftime("%Y"), "Date": inv_date.strftime("%Y-%m-%d"),
                "Invoice no": inv_no, "Party ID": parties[party_name]["Party ID"], "Party name": party_name,
                "Item ID": "", "Item": "Multiple Items", # Indicate it's a multi-item invoice
                "Moisture %": "", "Qty": "", "Unit": "", "price": "", "Amount": total_base_amount,
                "CGST": sum(i["CGST"] for i in line_items_to_save), 
                "SGST": sum(i["SGST"] for i in line_items_to_save), 
                "IGST": sum(i["IGST"] for i in line_items_to_save), 
                "ROUND OFF": round_off_diff, "Total amount": rounded_total,
                "Moisture Qty": "", "Actual Qty": "",
                "Employee ID": employees[employee_name]["Employee ID"] if employee_name != "N/A" else "", "Employee Name": employee_name,
                "Transport Type": transport_type, "Vehicle No": vehicle_no,
                "Transporter ID": transporters[transporter_name]["Transporter ID"] if transporter_name != "None" else "", "Transporter Name": transporter_name,
                "Starting Km": start_km, "End Km": end_km, "Km covered": km_covered,
                "Transportation Amount": total_transport, "Other Charges": other_charges, "Places Visited": places_visited,
                "Invoice Link": invoice_link
            }
            
            saved_purchase = sheets_db.insert_row("purchases", purchase_data, user_id=user["User ID"])
            master_id = saved_purchase["Purchase ID"]

            # 4. Save all Line Items (purchase_items tab)
            for item_data in line_items_to_save:
                item_data["Purchase ID"] = master_id
                sheets_db.insert_row("purchase_items", item_data, user_id=user["User ID"])

            st.balloons()
            st.success(f"✅ Invoice {inv_no} Saved! (ID: {master_id}) with {len(line_items_to_save)} items.")
            st.write(f"**Total Invoice Value:** ₹ {rounded_total:,.2f}")
            
        except Exception as e:
            st.error(f"Error saving purchase: {e}")
