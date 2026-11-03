import streamlit as st

st.set_page_config(
    page_title="Rupan ERP",
    page_icon="🏭",
    layout="wide",
)

st.title("🏭 Rupan Renewable ERP")
st.success("✅ App is deployed successfully!")

st.markdown("---")
st.markdown("### Setup Status")

# Check secrets
try:
    sheet_id = st.secrets["google"]["sheet_id"]
    st.write(f"✅ Sheet ID loaded: `{sheet_id[:15]}...`")
except Exception as e:
    st.error(f"❌ Secrets not loaded: {e}")

# Check Sheets connection
try:
    from core.sheets_db import get_spreadsheet
    ss = get_spreadsheet()
    st.write(f"✅ Connected to Sheet: **{ss.title}**")
    tabs = [ws.title for ws in ss.worksheets()]
    st.write(f"✅ Tabs found: {', '.join(tabs)}")
except Exception as e:
    st.warning(f"⚠️ Sheet connection pending: {e}")

# Check Drive connection
try:
    from core.drive import get_drive
    drive = get_drive()
    st.write("✅ Drive API connected")
except Exception as e:
    st.warning(f"⚠️ Drive connection pending: {e}")

st.markdown("---")
st.info("This is the setup verification page. Full ERP coming in next steps.")
