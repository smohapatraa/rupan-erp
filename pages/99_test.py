# pages/99_test.py
import streamlit as st
from core import sheets_db
from core import cache

st.title("DB self-test (cached)")

if st.button("Run test"):
    try:
        # 1. Check headers
        with st.spinner("Checking headers..."):
            sheets_db.ensure_headers()
        st.success("1. headers OK")

        # 2. Health check
        with st.spinner("Running healthcheck..."):
            hc = cache.healthcheck()
        st.success("2. healthcheck OK")
        st.json(hc)

        # 3. Insert
        with st.spinner("Inserting test party..."):
            p = sheets_db.insert_row("party_master", {
                "Party Name": "Test Party",
                "Contact": "0000000000",
                "Address": "test address",
                "GSTIN": "",
                "Active": "TRUE",
            }, user_id="SYSTEM")
        st.success(f"3. inserted: {p['Party ID']}")

        # 4. Read
        with st.spinner("Reading back..."):
            got = cache.load_row("party_master", p["Party ID"])
            assert got["Party Name"] == "Test Party", got
        st.success("4. read OK")

        # 5. Update
        with st.spinner("Updating..."):
            sheets_db.update_row("party_master", p["Party ID"], {"Contact": "1111111111"}, user_id="SYSTEM")
            got2 = cache.load_row("party_master", p["Party ID"])
            assert got2["Contact"] == "1111111111", got2
        st.success("5. update OK")

        # 6. Soft-delete
        with st.spinner("Soft-deleting..."):
            sheets_db.delete_row("party_master", p["Party ID"], user_id="SYSTEM")
            got3 = cache.load_row("party_master", p["Party ID"])
            assert got3["Active"] == "FALSE", got3
        st.success("6. soft-delete OK")

        # 7. Audit log
        with st.spinner("Checking audit log..."):
            logs = cache.load_all("audit_log")
        st.success(f"7. audit rows: {len(logs)}")

        st.balloons()
        st.success("ALL GOOD")

    except Exception as e:
        st.error(f"FAILED: {type(e).__name__}: {e}")
        st.exception(e)
