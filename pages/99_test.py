import streamlit as st
from core import sheets_db

st.title("DB self-test")

# Test 1: Just check if Secrets load
if st.button("1. Check Secrets"):
    try:
        if "gcp_service_account" in st.secrets:
            st.success("Secrets found! Client Email: " + st.secrets["gcp_service_account"]["client_email"])
            st.write("Sheet ID:", st.secrets.get("sheet_id"))
        else:
            st.error("No gcp_service_account in Secrets!")
    except Exception as e:
        st.error(f"Error reading secrets: {e}")

# Test 2: Try to connect to Google Sheets
if st.button("2. Connect to Google"):
    with st.spinner("Connecting..."):
        try:
            client = sheets_db.get_client()
            st.success("Google Authorized!")
            
            sh = sheets_db.get_spreadsheet()
            st.success(f"Opened Spreadsheet: {sh.title}")
        except Exception as e:
            st.error(f"Connection Failed: {e}")

# Test 3: Run the full insert/update/delete test
if st.button("3. Run Full Test"):
    try:
        with st.spinner("Checking headers..."):
            sheets_db.ensure_headers()
        st.success("Headers OK")

        with st.spinner("Inserting..."):
            p = sheets_db.insert_row("party_master", {
                "Party Name": "Test Party", "Contact": "0", "Address": "test", "GSTIN": "", "Active": "TRUE",
            }, user_id="SYSTEM")
        st.success(f"Inserted: {p['Party ID']}")

        with st.spinner("Reading..."):
            got = sheets_db.get_row("party_master", p["Party ID"])
            assert got["Party Name"] == "Test Party"
        st.success("Read OK")

        with st.spinner("Updating..."):
            sheets_db.update_row("party_master", p["Party ID"], {"Contact": "1"}, user_id="SYSTEM")
        st.success("Update OK")

        with st.spinner("Deleting..."):
            sheets_db.delete_row("party_master", p["Party ID"], user_id="SYSTEM")
        st.success("Delete OK")
        
        st.balloons()
        st.success("ALL GOOD")
    except Exception as e:
        st.error(f"FAILED: {type(e).__name__}: {e}")
        st.exception(e)
