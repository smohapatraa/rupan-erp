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
    farms = {f["Farm Name"]: f for f in sheets_db.list_all("farm_master", only_active=True)}

if not parties or not items:
    st.error("You must add at least one Party and one Item in the Master tables.")
    st.stop()

# Use a form to prevent page refreshes on every cell edit
with st.form("multi_item_purchase_form", clear_on_submit=True):
    
    # --- SECTION 1: INVOICE HEADER ---
    st.subheader("1. Invoice Details")
    c1, c2, c3, c4 = st.columns(4)
    with c1: inv_date = st.date_input("Date", value=date.today())
    with c2: inv_no = st.text_input("Invoice No *")
    with c3: party_name = st.selectbox("Party Name *", list(parties.keys()))
    with c4: 
        farm_name = st.selectbox("Farm Name", ["None"] + list(farms.keys()))
        farm_id = farms[farm_name]["Farm ID"] if farm_name != "None" else ""

    c1, c2, c3, c4 = st.columns(4)
    with c1: employee_name = st.selectbox("Employee Name *", list(employees.keys()) if employees else ["N/A"])
    with c2: transport_type = st.selectbox("Transport Type", ["By Vehicle", "By Transporter", "Self Pickup"])
    with c3: vehicle_no = st.text_input("Vehicle No")
    with c4: transporter_name = st.selectbox("Transporter Name", ["None"] + list(transporters.keys()))

    c1, c2, c3, c4 = st.columns(4)
    with c1: places_visited = st.text_input("Places Visited")
    with c2: start_km = st.number_input("Starting Km", min_value=0.0, step=1.0)
    with c3: end_km = st.number_input("End Km", min_value=0.0, step=1.0)
    with c4: km_covered = st.number_input("Km Covered", min_value=0.0, step=1.0, value=float(end_km - start_km) if end_km > start_km else 0.0)

    c1, c2 = st.columns(2)
    with c1: other_charges = st.number_input("Other Charges (₹)", min_value=0.0, step=1.0)
    with c2: invoice_link = st.text_input("Invoice Link (Drive / OneDrive)")

    st.divider()

    # --- SECTION 2: MULTI-ITEM GRID ---
    st.subheader("2. Line Items")
    st.write("Click the '+' at the bottom of the table to add a new row.")
    
    # Create the default first row
    default_data = pd.DataFrame([
        {"Item": list(items.keys())[0], "Qty": 1.00, "Moisture %": 0.00, "Price": 0.00, "CGST %": 0.00, "SGST %": 0.00, "IGST %": 0.00, "Transport Amt": 0.00}
    ])

    # Use dynamic rows inside the form. This is FAST and allows adding rows.
    edited_df = st.data_editor(
        default_data,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Item": st.column_config.SelectboxColumn("Item", options=list(items.keys()), required=True),
            "Qty": st.column_config.NumberColumn("Qty", min_value=0.1, step=1.0, format="%.2f", required=True),
            "Moisture %": st.column_config.NumberColumn("Moisture %", min_value=0.0, max_value=100.0, step=0.1, format="%.2f"),
            "Price": st.column_config.NumberColumn("Price (₹)", min_value=0.0, step=0.01, format="%.2f", required=True),
            "CGST %": st.column_config.NumberColumn("CGST %", min_value=0.0, step=0.1, format="%.2f"),
            "SGST %": st.column_config.NumberColumn("SGST %", min_value=0.0, step=0.1, format="%.2f"),
            "IGST %": st.column_config.NumberColumn("IGST %", min_value=0.0, step=0.1, format="%.2f"),
            "Transport Amt": st.column_config.NumberColumn("Transport Amt (₹)", min_value=0.0, step=1.0, format="%.2f"),
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

    # Auto-fill empty rows (for when user clicks '+' but doesn't type an Item)
    # We fill the Item with the first available item so the app doesn't crash
    edited_df["Item"] = edited_df["Item"].fillna(list(items.keys())[0])
    
    total_base_amount = 0.0
    total_cgst = 0.0
    total_sgst = 0.0
    total_igst = 0.0
    total_transport = 0.0
    total_qty = 0.0
    total_moisture_qty = 0.0
    total_actual_qty = 0.0
    weighted_moisture = 0.0
    
    line_items_to_save = []
    
    try:
        for index, row in edited_df.iterrows():
            # Skip rows that are completely empty (if user added a row and didn't use it)
            if pd.isna(row["Qty"]) or row["Qty"] == 0:
                continue
                
            item_name = row["Item"]
            qty = float(row["Qty"])
            moisture_pct = float(row["Moisture %"]) if not pd.isna(row["Moisture %"]) else 0.0
            price = float(row["Price"]) if not pd.isna(row["Price"]) else 0.0
            cgst_pct = float(row["CGST %"]) if not pd.isna(row["CGST %"]) else 0.0
            sgst_pct = float(row["SGST %"]) if not pd.isna(row["SGST %"]) else 0.0
            igst_pct = float(row["IGST %"]) if not pd.isna(row["IGST %"]) else 0.0
            transport_amt = float(row["Transport Amt"]) if not pd.isna(row["Transport Amt"]) else 0.0
            
            moisture_qty = qty * (moisture_pct / 100.0)
            actual_qty = qty - moisture_qty
            amount = qty * price
            
            cgst_amt = amount * (cgst_pct / 100.0)
            sgst_amt = amount * (sgst_pct / 100.0)
            igst_amt = amount * (igst_pct / 100.0)
            row_total = amount + cgst_amt + sgst_amt + igst_amt + transport_amt
            
            total_base_amount += amount
            total_cgst += cgst_amt
            total_sgst += sgst_amt
            total_igst += igst_amt
            total_transport += transport_amt
            total_qty += qty
            total_moisture_qty += moisture_qty
            total_actual_qty += actual_qty
            weighted_moisture += (moisture_pct * qty)
            
            unit = items[item_name].get("Unit", "Kg")
            line_items_to_save.append({
                "Item ID": items[item_name]["Item ID"],
                "Item": item_name,
                "Qty": qty,
                "Unit": unit,
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

        if not line_items_to_save:
            st.error("Please add at least one item with a valid quantity.")
            st.stop()

        gross_total = total_base_amount + total_cgst + total_sgst + total_igst + total_transport + other_charges
        rounded_total = round(gross_total)
        round_off_diff = rounded_total - gross_total
        
        avg_moisture = (weighted_moisture / total_qty) if total_qty > 0 else 0.0
        avg_price = (total_base_amount / total_qty) if total_qty > 0 else 0.0

        st.success(f"Calculated Total: ₹ {rounded_total:,.2f}")
        st.info(f"Total Qty: {total_qty:.2f} | Total Moisture Qty: {total_moisture_qty:.2f} | Total Actual Qty: {total_actual_qty:.2f}")
        st.info(f"Avg Moisture: {avg_moisture:.2f}% | Avg Price: ₹ {avg_price:,.2f}")

        purchase_data = {
            "Month": inv_date.strftime("%B"), "Year": inv_date.strftime("%Y"), "Date": inv_date.strftime("%Y-%m-%d"),
            "Invoice no": inv_no, "Party ID": parties[party_name]["Party ID"], "Party name": party_name,
            "Item ID": "", "Item": "Multiple Items", 
            "Moisture %": avg_moisture, "Qty": total_qty, "Unit": "Mixed", "price": avg_price, "Amount": total_base_amount,
            "CGST": total_cgst, "SGST": total_sgst, "IGST": total_igst, "ROUND OFF": round_off_diff, "Total amount": rounded_total,
            "Moisture Qty": total_moisture_qty, "Actual Qty": total_actual_qty,
            "Employee ID": employees[employee_name]["Employee ID"] if employee_name != "N/A" else "", "Employee Name": employee_name,
            "Transport Type": transport_type, "Vehicle No": vehicle_no,
            "Transporter ID": transporters[transporter_name]["Transporter ID"] if transporter_name != "None" else "", "Transporter Name": transporter_name,
            "Starting Km": start_km, "End Km": end_km, "Km covered": km_covered,
            "Transportation Amount": total_transport, "Other Charges": other_charges, "Places Visited": places_visited,
            "Farm ID": farm_id, "Farm Name": farm_name,
            "Invoice Link": invoice_link
        }
        
        saved_purchase = sheets_db.insert_row("purchases", purchase_data, user_id=user["User ID"])
        master_id = saved_purchase["Purchase ID"]

        for item_data in line_items_to_save:
            item_data["Purchase ID"] = master_id
            sheets_db.insert_row("purchase_items", item_data, user_id=user["User ID"])

        st.balloons()
        st.success(f"✅ Invoice {inv_no} Saved! (ID: {master_id}) with {len(line_items_to_save)} items.")
        
    except Exception as e:
        st.error(f"Error saving purchase: {e}")
