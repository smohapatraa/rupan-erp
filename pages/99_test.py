import streamlit as st
from core import sheets_db
from googleapiclient.discovery import build

st.title("DB self-test")

if st.button("🚀 Auto-Fix Headers & Run Test"):
    with st.spinner("Fixing headers in Google Sheets..."):
        try:
            service = sheets_db.get_service()
            sheet_id = sheets_db._get_sheet_id()
            
            # Loop through every tab in our SCHEMA and write the correct headers
            for tab_name, headers in sheets_db.SCHEMA.items():
                body = {'values': [headers]}
                # Overwrite row 1 with the correct headers
                service.spreadsheets().values().update(
                    spreadsheetId=sheet_id, range=f"{tab_name}!A1",
                    valueInputOption="USER_ENTERED", body=body
                ).execute()
                st.write(f"✅ Fixed headers for `{tab_name}`")
                
            st.success("All headers are now correct in Google Sheets!")
            
        except Exception as e:
            st.error(f"Failed to fix headers: {e}")
            st.stop()

    # Now run the actual test
    with st.spinner("Checking headers..."):
        sheets_db.ensure_headers()
    st.success("Headers OK")

    with st.spinner("Inserting test party..."):
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
    st.success("ALL GOOD ✅")
