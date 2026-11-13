import streamlit as st
import pandas as pd
from datetime import date
from core import sheets_db
from core import auth

auth.require_login()
user = auth.current_user()

st.title("🧾 Purchase Entry")

# ---------- Load Master Data ----------
with st.spinner("Loading master data..."):
    parties = {p["Party Name"]: p for p in sheets_db.list_all("party_master", only_active=True)}
    items = {i["Item Name"]: i for i in sheets_db.list_all("item_master", only_active=True)}
    employees = {e["Name"]: e for e in sheets_db.list_all("employee_master", only_active=True)}
    transporters = {t["Name"]: t for t in sheets_db.list_all("transporter_master", only_active=True)}

if not parties or not items:
    st.error("Add at least one Party and one Item in the masters before creating a purchase.")
    st.stop()

with st.form("purchase_form", clear_on_submit=True):
    # Row 1 — Invoice basics
    c1, c2, c3, c4 = st.columns(4)
    with c1: inv_date = st.date_input("Date", value=date.today())
    with c2: inv_no = st.text_input("Invoice No *")
    with c3: party_name = st.selectbox("Party Name *", list(parties.keys()))
    with c4: employee_name = st.selectbox(
        "Employee Name *",
        list(employees.keys()) if employees else ["N/A"],
    )

    # Row 2 — Transport info
    c1, c2, c3, c4 = st.columns(4)
    with c1: transport_type = st.selectbox("Transport Type", ["By Vehicle", "By Transporter", "Self Pickup"])
    with c2: vehicle_no = st.text_input("Vehicle No")
    with c3: transporter_name = st.selectbox("Transporter Name", ["None"] + list(transporters.keys()))
    with c4: places_visited = st.text_input("Places Visited")

    # Row 3 — Km and charges
    c1, c2, c3, c4 = st.columns(4)
    with c1: start_km = st.number_input("Starting Km", min_value=0.0, step=1.0)
    with c2: end_km = st.number_input("End Km", min_value=0.0, step=1.0)
    with c3:
        auto_km = float(end_km - start_km) if end_km > start_km else 0.0
        km_covered = st.number_input("Km Covered", min_value=0.0, step=1.0, value=auto_km)
    with c4: other_charges = st.number_input("Other Charges (₹)", min_value=0.0, step=1.0)

    st.divider()
    st.subheader("Item Details")

    # Row 4 — Item
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        item_name = st.selectbox("Item *", list(items.keys()))
        default_unit = items[item_name].get("Unit", "Kg")
    with c2:
        qty = st.number_input("Qty *", min_value=0.1, step=1.0)
        unit = st.text_input("Unit", value=default_unit)
    with c3:
        moisture_pct = st.number_input("Moisture %", min_value=0.0, max_value=100.0, step=0.1)
        price = st.number_input("Price (₹) *", min_value=0.0, step=1.0)
    with c4:
        transport_amt = st.number_input("Transportation Amount (₹)", min_value=0.0, step=1.0)

    # Row 5 — Taxes
    st.write("**Taxes**")
    c1, c2, c3 = st.columns(3)
    with c1:
        cgst_pct = st.number_input("CGST %", min_value=0.0, step=0.1)
        sgst_pct = st.number_input("SGST %", min_value=0.0, step=0.1)
    with c2:
        igst_pct = st.number_input("IGST %", min_value=0.0, step=0.1)

    st.divider()
    uploaded_file = st.file_uploader("Upload Invoice (PDF/Image)", type=["pdf", "jpg", "jpeg", "png"])

    st.write("")
    submitted = st.form_submit_button("💾 Calculate & Save Purchase", use_container_width=True, type="primary")


# ---------- Process ----------
if submitted:
    if not inv_no:
        st.error("Invoice Number is required.")
        st.stop()

    # Math — gross amount on BILLED qty (fix)
    moisture_qty = round(qty * moisture_pct / 100, 3)
    actual_qty = round(qty - moisture_qty, 3)
    amount = round(qty * price, 2)          # ← billed qty × price (the fix)
    cgst_amt = round(amount * cgst_pct / 100, 2)
    sgst_amt = round(amount * sgst_pct / 100, 2)
    igst_amt = round(amount * igst_pct / 100, 2)

    # Transport is SEPARATE (not in purchase total)
    pre_round = round(amount + cgst_amt + sgst_amt + igst_amt, 2)
    rounded_total = round(pre_round)
    round_off_diff = round(rounded_total - pre_round, 2)

    st.success(f"Item Amount: ₹{amount:,.2f} | Taxes: ₹{cgst_amt+sgst_amt+igst_amt:,.2f} | Total: ₹{rounded_total:,.2f}")
    st.info(f"Transport (separate): ₹{transport_amt:,.2f} + Other: ₹{other_charges:,.2f}")

    # Upload invoice
    invoice_link = ""
    if uploaded_file is not None:
        with st.spinner("Uploading invoice to Google Drive..."):
            try:
                folder_id = st.secrets["google"]["invoice_folder_id"]
                file_bytes = uploaded_file.read()
                filename = f"{inv_no}_{party_name}_{inv_date}.{uploaded_file.name.split('.')[-1]}"
                invoice_link = sheets_db.upload_invoice_to_drive(
                    file_bytes=file_bytes,
                    filename=filename,
                    folder_id=folder_id,
                    mime_type=uploaded_file.type,
                )
                st.info("Invoice uploaded to Drive!")
            except Exception as e:
                st.error(f"Drive upload failed: {e}")

    # Save purchase header
    with st.spinner("Saving purchase..."):
        try:
            purchase_data = {
                "Month": inv_date.strftime("%B"),
                "Year": inv_date.strftime("%Y"),
                "Date": inv_date.strftime("%Y-%m-%d"),
                "Invoice no": inv_no,
                "Party ID": parties[party_name]["Party ID"],
                "Party name": party_name,
                "Item ID": items[item_name]["Item ID"],
                "Item": item_name,
                "Moisture %": moisture_pct,
                "Qty": qty,
                "Unit": unit,
                "price": price,
                "Amount": amount,
                "CGST": cgst_amt,
                "SGST": sgst_amt,
                "IGST": igst_amt,
                "ROUND OFF": round_off_diff,
                "Total amount": rounded_total,
                "Moisture Qty": moisture_qty,
                "Actual Qty": actual_qty,
                "Employee ID": employees[employee_name]["Employee ID"] if employee_name != "N/A" and employees else "",
                "Employee Name": employee_name,
                "Transport Type": transport_type,
                "Vehicle No": vehicle_no,
                "Transporter ID": transporters[transporter_name]["Transporter ID"] if transporter_name != "None" else "",
                "Transporter Name": transporter_name,
                "Starting Km": start_km,
                "End Km": end_km,
                "Km covered": km_covered,
                "Transportation Amount": transport_amt,
                "Other Charges": other_charges,
                "Places Visited": places_visited,
                "Invoice Link": invoice_link,
            }

            saved_purchase = sheets_db.insert_row("purchases", purchase_data, user_id=user["User ID"])

            # Save purchase line item
            item_data = {
                "Purchase ID": saved_purchase["Purchase ID"],
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
                "ROUND OFF": round_off_diff,
                "Total amount": rounded_total,
            }
            sheets_db.insert_row("purchase_items", item_data, user_id=user["User ID"])

            st.balloons()
            st.success(f"✅ Purchase Saved! (ID: {saved_purchase['Purchase ID']})")
        except Exception as e:
            st.error(f"Error saving purchase: {e}")
