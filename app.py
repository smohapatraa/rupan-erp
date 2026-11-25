import streamlit as st
import pandas as pd
from datetime import date
from core import auth
from core import sheets_db

# 1. Page Configuration
st.set_page_config(
    page_title="Rupan Renewables ERP",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------------------------------------
# CUSTOM BRANDING & CSS
# ------------------------------------------------------------
# Brand-matched SVG: Green leaf (sustainability) + Orange Sun (energy)
LOGO_SVG = """
<svg width="80" height="80" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <circle cx="50" cy="50" r="48" fill="#f4fbf4" stroke="#2e7d32" stroke-width="2"/>
  <path d="M 30 70 Q 50 40 70 70" fill="none" stroke="#2e7d32" stroke-width="6" stroke-linecap="round"/>
  <path d="M 50 70 Q 50 45 50 30" fill="none" stroke="#2e7d32" stroke-width="4" stroke-linecap="round"/>
  <circle cx="50" cy="28" r="8" fill="#ff9800"/>
  <path d="M 50 15 L 50 18 M 50 38 L 50 41 M 37 28 L 40 28 M 60 28 L 63 28" stroke="#ff9800" stroke-width="2.5" stroke-linecap="round"/>
</svg>
"""

st.markdown("""
<style>
    /* Main layout tweaks */
    .block-container { padding-top: 2rem; }
    
    /* Login box styling */
    .login-container {
        background-color: #ffffff;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.05);
        border-top: 6px solid #2e7d32;
    }
    
    /* Hide default streamlit menu and footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# 2. Initialize Session State
if "user" not in st.session_state:
    st.session_state["user"] = None

# 3. Login Screen
if st.session_state["user"] is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Branding Header
        st.markdown(f"<div style='text-align: center; margin-bottom: 20px;'>{LOGO_SVG}</div>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #1e5631; margin-bottom: 0;'>Rupan Renewables</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666; font-size: 1.1em; margin-top: 5px;'>Sustainable Energy Solutions for a Greener Tomorrow</p>", unsafe_allow_html=True)
        
        st.write("") # spacer
        
        # Login Form inside a styled container
        with st.container():
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            with st.form("login_form"):
                st.subheader("🔐 Enterprise Login")
                username = st.text_input("Username", placeholder="Enter username")
                password = st.text_input("Password", type="password", placeholder="Enter password")
                submit = st.form_submit_button("Sign In", use_container_width=True, type="primary")
                
                if submit:
                    if not username or not password:
                        st.error("Please enter both username and password.")
                    else:
                        with st.spinner("Authenticating..."):
                            user = auth.login(username, password)
                            if user:
                                st.session_state["user"] = user
                                st.rerun()
                            else:
                                st.error("Invalid username or password, or account is inactive.")
            st.markdown('</div>', unsafe_allow_html=True)
                            
    st.stop()

# 4. Logged in - Sidebar setup
user = st.session_state["user"]

with st.sidebar:
    # Sidebar Branding
    st.markdown(f"<div style='text-align: center; margin-bottom: 10px;'>{LOGO_SVG}</div>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: #1e5631; margin-bottom: 0;'>Rupan Renewables</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #888; font-size: 0.85em;'>Biomass ERP System</p>", unsafe_allow_html=True)
    st.divider()
    
    # User Info
    st.markdown(f"👤 **{user.get('Username')}**")
    st.caption(f"Role: {user.get('Role')}")
    
    st.divider()
    if st.button("🚪 Logout", use_container_width=True):
        auth.logout()

# ============================================================
# 5. DASHBOARD
# ============================================================
st.title("📊 Dashboard")
st.caption(f"Welcome back, **{user.get('Username')}**. Here is your operations summary.")

# ------------------------------------------------------------
# 5a. LOAD DATA
# ------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner="Loading dashboard…")
def load_dashboard_data():
    return sheets_db.list_all("purchases")

try:
    purchases = load_dashboard_data()
except Exception as e:
    st.error(f"Failed to load purchases: {e}")
    st.stop()

if not purchases:
    st.info("No purchases recorded yet. Start by adding a purchase in the sidebar.")
    st.stop()

df = pd.DataFrame(purchases)
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Farm Name"] = df["Farm Name"].astype("string").str.strip()
df["Total amount"] = pd.to_numeric(df["Total amount"], errors="coerce")
df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce")
df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
df["Month"] = df["Month"].astype("string").str.strip()

# ------------------------------------------------------------
# 5b. FILTERS — Farm + Month/Year
# ------------------------------------------------------------
st.markdown("### 🎯 Filters")
f1, f2, f3, f4 = st.columns([2, 2, 1.5, 1.5])

farm_vals = sorted([v for v in df["Farm Name"].dropna().unique().tolist() if v not in ("", "None")])
has_blank = (df["Farm Name"].isna() | (df["Farm Name"] == "")).any()
farm_opts = farm_vals + (["(blank)"] if has_blank else [])

with f1:
    selected_farms = st.multiselect("Farm Name", options=farm_opts, default=farm_opts)

year_vals = sorted([int(y) for y in df["Year"].dropna().unique().tolist()], reverse=True)
month_names = ["January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]

with f2:
    selected_year = st.selectbox("Year", ["All"] + year_vals, index=0)

with f3:
    selected_month = st.selectbox("Month", ["All"] + month_names, index=0)

with f4:
    date_mode = st.radio("Date basis", ["Use Month+Year", "Use Date range"], horizontal=False)

if date_mode == "Use Date range":
    min_d = df["Date"].min().date()
    max_d = df["Date"].max().date()
    default_start = max(min_d, date.today().replace(day=1))
    default_end = min(max_d, date.today())
    if default_start > default_end:
        default_start, default_end = min_d, max_d
    start_date = st.date_input("From", value=default_start, min_value=min_d, max_value=max_d)
    end_date = st.date_input("To", value=default_end, min_value=min_d, max_value=max_d)

# ------------------------------------------------------------
# 5c. APPLY FILTERS
# ------------------------------------------------------------
mask = df["Farm Name"].notna()

include_blank = "(blank)" in selected_farms
farm_mask = df["Farm Name"].isin([f for f in selected_farms if f != "(blank)"])
if include_blank:
    farm_mask |= df["Farm Name"].isna() | (df["Farm Name"] == "")
mask &= farm_mask

if date_mode == "Use Month+Year":
    if selected_year != "All":
        mask &= df["Year"] == selected_year
    if selected_month != "All":
        mask &= df["Month"] == selected_month
else:
    mask &= (df["Date"].dt.date >= start_date) & (df["Date"].dt.date <= end_date)

fdf = df.loc[mask].copy()

# ------------------------------------------------------------
# 5d. KPI CARDS
# ------------------------------------------------------------
st.markdown("---")

k1, k2, k3, k4, k5 = st.columns(5)
total_rows = len(fdf)
total_amt = fdf["Total amount"].sum() if not fdf.empty else 0
total_qty = fdf["Qty"].sum() if not fdf.empty else 0
total_farms = fdf["Farm Name"].nunique() if not fdf.empty else 0
total_parties = fdf["Party name"].nunique() if not fdf.empty else 0

with k1: st.metric("🧾 Purchases", f"{total_rows:,}")
with k2: st.metric("💰 Total Amount", f"₹ {total_amt:,.0f}")
with k3: st.metric("📦 Total Qty", f"{total_qty:,.0f}")
with k4: st.metric("🏞️ Active Farms", f"{total_farms}")
with k5: st.metric("🤝 Suppliers", f"{total_parties}")

# ------------------------------------------------------------
# 5e. TREND + FARM BREAKDOWN
# ------------------------------------------------------------
st.markdown("---")
chart_col, breakdown_col = st.columns([2, 1])

with chart_col:
    st.markdown("#### 📈 Recent Purchases Amount")
    trend = fdf.dropna(subset=["Date"]).copy()
    if trend.empty:
        st.info("No dated purchases to chart.")
    else:
        recent_trend = trend.sort_values("Date", ascending=True).tail(10)
        recent_trend["_label"] = recent_trend["Date"].dt.strftime("%d-%b") + " (" + recent_trend["Purchase ID"].str[-3:] + ")"
        
        st.bar_chart(
            recent_trend.set_index("_label")["Total amount"],
            use_container_width=True,
            height=320,
            color="#2e7d32"  # Rupan Green
        )

with breakdown_col:
    st.markdown("#### 🏞️ Breakdown")
    toggle = st.radio("Group by:", ["Farm", "Month"], horizontal=True, label_visibility="collapsed")
    
    if fdf.empty:
        st.info("No data.")
    else:
        if toggle == "Farm":
            group_col = fdf["Farm Name"].fillna("(blank)")
        else:
            group_col = fdf["Month"].fillna("Unknown")

        bdf = (
            fdf.assign(_group=group_col)
               .groupby("_group")["Total amount"]
               .sum()
               .sort_values(ascending=False)
               .reset_index()
               .rename(columns={"_group": "Category", "Total amount": "Amount"})
        )
        
        st.bar_chart(
            bdf.set_index("Category")["Amount"],
            use_container_width=True,
            height=320,
            color="#ff9800"  # Energy Orange
        )

# ------------------------------------------------------------
# 5f. TOP SUPPLIERS
# ------------------------------------------------------------
st.markdown("---")
st.markdown("#### 🏆 Top Suppliers by Amount")

if fdf.empty:
    st.info("No data.")
else:
    top = (
        fdf.groupby("Party name", dropna=False)
           .agg(
               Purchases=("Purchase ID", "count"),
               Qty=("Qty", "sum"),
               Amount=("Total amount", "sum"),
           )
           .sort_values("Amount", ascending=False)
           .head(10)
           .reset_index()
    )
    top["Qty"] = top["Qty"].round(2)
    top["Amount"] = top["Amount"].round(2)
    st.dataframe(
        top.style.format({"Qty": "{:,.2f}", "Amount": "₹ {:,.2f}"}, na_rep=""),
        use_container_width=True,
        hide_index=True,
    )

# ------------------------------------------------------------
# 5g. RECENT PURCHASES
# ------------------------------------------------------------
st.markdown("---")
st.markdown("#### 🕒 Recent Purchases")

if fdf.empty:
    st.info("No data.")
else:
    recent = (
        fdf.sort_values("Date", ascending=False)
           .head(15)[["Purchase ID", "Date", "Party name", "Farm Name", "Invoice no", "Item", "Qty", "Total amount"]]
    )
    recent["Date"] = recent["Date"].dt.strftime("%d-%b-%Y")
    st.dataframe(
        recent.style.format({"Qty": "{:,.2f}", "Total amount": "₹ {:,.2f}"}, na_rep=""),
        use_container_width=True,
        hide_index=True,
    )

# ------------------------------------------------------------
# 5h. SYSTEM STATUS
# ------------------------------------------------------------
with st.expander("⚙️ System Status"):
    try:
        if st.button("Run DB Healthcheck"):
            with st.spinner("Checking..."):
                hc = sheets_db.healthcheck()
                if hc.get("status") == "ok":
                    st.success("Database connected successfully!")
                else:
                    st.error(f"DB Error: {hc.get('message')}")
    except Exception as e:
        st.error(f"Error: {e}")
