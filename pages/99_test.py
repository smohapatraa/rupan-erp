# pages/99_test.py
import streamlit as st
from core import sheets_db

st.title("DB self-test")

if st.button("Run test"):
    try:
        st.write("1. Checking headers...")
        sheets_db.ensure_headers()
        st.success("headers OK")

        st.write("2. Health check...")
        st.json(sheets_db.healthcheck())

        st.write("3. Insert test party...")
        p = sheets_db.insert_row("party_master", {
            "Party Name": "Test Party",
            "Contact": "0000000000",
            "Address": "test address",
            "GSTIN": "",
            "Active": "TRUE",
        }, user_id="SYSTEM")
        st.write("inserted:", p["Party ID"])

        st.write("4. Read it back...")
        got = sheets_db.get_row("party_master", p["Party ID"])
        assert got["Party Name"] == "Test Party"
        st.success("read OK")

        st.write("5. Update it...")
        sheets_db.update_row("party_master", p["Party ID"], {"Contact": "1111111111"}, user_id="SYSTEM")
        assert sheets_db.get_row("party_master", p["Party ID"])["Contact"] == "1111111111"
        st.success("update OK")

        st.write("6. Soft-delete it...")
        sheets_db.delete_row("party_master", p["Party ID"], user_id="SYSTEM")
        assert sheets_db.get_row("party_master", p["Party ID"])["Active"] == "FALSE"
        st.success("soft-delete OK")

        st.write("7. Audit log...")
        logs = sheets_db.list_all("audit_log")
        st.write("audit rows:", len(logs))

        st.balloons()
        st.success("ALL GOOD")
    except Exception as e:
        st.error(f"FAILED: {type(e).__name__}: {e}")
        st.exception(e)
