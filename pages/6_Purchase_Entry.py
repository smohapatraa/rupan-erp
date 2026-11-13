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

# Initialize session state for the grid if it doesn't exist
if "purchase_grid" not in st.session_state:
    st.session_state.purchase_grid = pd.DataFrame([
        {"Item": list(items.keys())[0], "Qty": 1.00, "Moisture %": 0.00, "Price": 0.00, "CGST %": 0.00, "SGST %": 0.00, "IGST %": 0.00, "Transport Amt": 0.00}
    ])

def add_new_row():
    """Copies the last row's Item, but resets numbers to 0.0."""
    df = st.session_state.purchase_grid
    if not df.empty:
        last_row = df.iloc[-1].to_dict()
        # Reset numeric fields to 0.0
        last_row["Qty"] = 0.00
        last_row["Price"] = 0.00
        last_row["Moisture %"] = 0.00
        last_row["CGST %"] = 0.00
        last_row["SGST %"] = 0.00
        last_row["IGST %"] = 0.00
        last_row["Transport Amt"] = 0.00
        
        st.session_state.purchase_grid = pd.concat([df, pd.DataFrame([last_row])], ignore_index=True)
    else:
        st.session_state.purchase_grid = pd.DataFrame([
            {"Item": list(items.keys())[0], "Qty": 1.00, "Moisture %": 0.00, "Price": 0.00, "CGST %": 0.00, "SGST %": 0.00, "IGST %": 0.00, "Transport Amt": 0.00}
        ])

def delete_last_row():
    """Removes the last row."""
    if len(st.session_state.purchase_grid) > 1:
        st.session_state.purchase_grid = st.session_state.purchase_grid.iloc[:-1]

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
    
    col_add, col_remove, _ = st.columns([1, 1, 2])
    with col_add:
        st.button("➕ Add Row (Copy Previous Item)", on_click=add_new_row, use_container_width=True)
    with col_remove:
        st.button("➖ Remove Last Row", on_click=delete_last_row, use_container_width=True)

    edited_df = st.data_editor(
        st.session_state.purchase_grid,
        use_container_width=True,
        hide_index=True,
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
    
    st.session_state.purchase_grid = edited_df

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
            item_name = row["Item"]
            qty = float(row["Qty"])
            moisture_pct = float(row["Moisture %"])
            price = float(row["Price"])
            cgst_pct = float(row["CGST %"])
            sgst_pct = float(row["SGST %"])
            igst_pct = float(row["IGST %"])
            transport_amt = float(row["Transport Amt"])
            
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
        
        # Clear the grid for the next invoice
        st.session_state.purchase_grid = pd.DataFrame([
            {"Item": list(items.keys())[0], "Qty": 1.00, "Moisture %": 0.00, "Price": 0.00, "CGST %": 0.00, "SGST %": 0.00, "IGST %": 0.00, "Transport Amt": 0.00}
        ])
        
    except Exception as e:
        st.error(f"Error saving purchase: {e}")
