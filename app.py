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
# 🎨 PREMIUM CUSTOM CSS
# ------------------------------------------------------------
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #f8fafc;
    }
    
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Glassmorphism KPI Cards */
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.9);
        border: 1px solid #e2e8f0;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border-left: 5px solid #2e7d32;
    }
    div[data-testid="metric-container"] label {
        color: #64748b !important;
        font-weight: 600;
        font-size: 0.9rem;
        text-transform: uppercase;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #1e293b !important;
        font-weight: 700;
    }

    /* Style the Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 8px 8px 0px 0px;
        font-weight: 600;
        color: #64748b;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff;
        color: #2e7d32 !important;
        border-bottom: 3px solid #2e7d32;
    }

    /* Dataframe Styling */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }

    /* Login Box Styling */
    .login-container {
        background-color: #ffffff;
        padding: 2.5rem;
        border-radius: 16px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        border-top: 6px solid #2e7d32;
    }
</style>
""", unsafe_allow_html=True)

# 2. Initialize Session State
if "user" not in st.session_state:
    st.session_state["user"] = None

# 3. Login Screen
if st.session_state["user"] is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        try:
            logo_col1, logo_col2, logo_col3 = st.columns([1, 2, 1])
            with logo_col2:
                st.image("logo.png", use_container_width=True) 
        except:
            pass 
            
        
        st.markdown("<p style='text-align: center; color: #64748b; font-size: 1.1em; margin-bottom: 2rem;'>Sustainable Energy Solutions for a Greener Tomorrow</p>", unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            with st.form("login_form"):
                st.subheader("🔐 Enterprise Login")
                username = st.text_input("Username", placeholder="Enter username")
                password = st.text_input("Password", type="password", placeholder="Enter password")
                st.write("")
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
                                st.error("Invalid username or password.")
            st.markdown('</div>', unsafe_allow_html=True)
                            
    st.stop()

# 4. Sidebar Setup
user = st.session_state["user"]

with st.sidebar:
    try:
        st.image("logo.png", use_container_width=True)
    except:
        pass
        
    
    st.markdown("<p style='text-align: center; color: #64748b; font-size: 0.85em;'>Biomass ERP System</p>", unsafe_allow_html=True)
    st.divider()
    
    st.markdown(f"👤 **{user.get('Username')}**")
    st.caption(f"Role: {user.get('Role')}")
    
    st.divider()
    if st.button("🚪 Logout", use_container_width=True):
        auth.logout()

# ============================================================
# 5. MAIN DASHBOARD
# ============================================================
st.title("📊 Dashboard")
st.caption(f"Welcome back, **{user.get('Username')}**. Here is your operations summary.")

@st.cache_data(ttl=300, show_spinner="Loading dashboard…")
def load_dashboard_data():
    return (sheets_db.list_all("purchases"), sheets_db.list_all("purchase_items"))

try:
    purchases, purchase_items = load_dashboard_data()
except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.stop()

if not purchases:
    st.info("No purchases recorded yet. Start by adding a purchase in the sidebar.")
    st.stop()

df = pd.DataFrame(purchases)
items_df = pd.DataFrame(purchase_items) if purchase_items else pd.DataFrame(columns=["Purchase ID", "Item", "Qty", "Moisture %", "Amount"])

# Clean Data
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Farm Name"] = df["Farm Name"].astype("string").str.strip()
df["Total amount"] = pd.to_numeric(df["Total amount"], errors="coerce")
df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce")
df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
df["Month"] = df["Month"].astype("string").str.strip()
df["Employee Name"] = df.get("Employee Name", "Unknown").fillna("Unknown")
df["Moisture %"] = pd.to_numeric(df.get("Moisture %"), errors="coerce").fillna(0)
df["Transportation Amount"] = pd.to_numeric(df.get("Transportation Amount"), errors="coerce").fillna(0)

# ------------------------------------------------------------
# 5b. FILTERS
# ------------------------------------------------------------
with st.container():
    st.markdown("### 🎯 Filters")
    f1, f2, f3, f4 = st.columns([2, 2, 1.5, 1.5])
    
    farm_vals = sorted([v for v in df["Farm Name"].dropna().unique().tolist() if v not in ("", "None")])
    has_blank = (df["Farm Name"].isna() | (df["Farm Name"] == "")).any()
    farm_opts = farm_vals + (["(blank)"] if has_blank else [])
    
    with f1:
        selected_farms = st.multiselect("Farm Name", options=farm_opts, default=farm_opts)
    
    year_vals = sorted([int(y) for y in df["Year"].dropna().unique().tolist()], reverse=True)
    month_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    
    with f2:
        selected_year = st.selectbox("Year", ["All"] + year_vals, index=0)
    
    with f3:
        selected_month = st.selectbox("Month", ["All"] + month_names, index=0)
    
    with f4:
        date_mode = st.radio("Date basis", ["Month+Year", "Date range"], horizontal=False)

    if date_mode == "Date range":
        min_d = df["Date"].min().date()
        max_d = df["Date"].max().date()
        default_start = max(min_d, date.today().replace(day=1))
        default_end = min(max_d, date.today())
        if default_start > default_end:
            default_start, default_end = min_d, max_d
        start_date = st.date_input("From", value=default_start, min_value=min_d, max_value=max_d)
        end_date = st.date_input("To", value=default_end, min_value=min_d, max_value=max_d)

# Apply Filters
mask = df["Farm Name"].notna()
include_blank = "(blank)" in selected_farms
farm_mask = df["Farm Name"].isin([f for f in selected_farms if f != "(blank)"])
if include_blank:
    farm_mask |= df["Farm Name"].isna() | (df["Farm Name"] == "")
mask &= farm_mask

if date_mode == "Month+Year":
    if selected_year != "All": mask &= df["Year"] == selected_year
    if selected_month != "All": mask &= df["Month"] == selected_month
else:
    mask &= (df["Date"].dt.date >= start_date) & (df["Date"].dt.date <= end_date)

fdf = df.loc[mask].copy()

# ------------------------------------------------------------
# 5c. KPI CARDS
# ------------------------------------------------------------
st.markdown("---")
k1, k2, k3, k4, k5 = st.columns(5)
total_rows = len(fdf)
total_amt = fdf["Total amount"].sum() if not fdf.empty else 0
total_qty = fdf["Qty"].sum() if not fdf.empty else 0
total_farms = fdf["Farm Name"].nunique() if not fdf.empty else 0
total_parties = fdf["Party name"].nunique() if not fdf.empty else 0

with k1: st.metric("🧾 Purchases", f"{total_rows:,}")
with k2: st.metric("💰 Amount", f"₹ {total_amt:,.0f}")
with k3: st.metric("📦 Qty", f"{total_qty:,.0f}")
with k4: st.metric("🏞️ Farms", f"{total_farms}")
with k5: st.metric("🤝 Suppliers", f"{total_parties}")

# ------------------------------------------------------------
# 5d. TABS FOR REPORTS (CLEAN UI)
# ------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📈 Overview & Trends", "👷 Employee Report", "🏢 Supplier Report"])

# --- TAB 1: OVERVIEW ---
with tab1:
    chart_col, breakdown_col = st.columns([2, 1])
    with chart_col:
        st.markdown("#### 📈 Recent Purchases Amount")
        trend = fdf.dropna(subset=["Date"]).copy()
        if trend.empty:
            st.info("No dated purchases to chart.")
        else:
            recent_trend = trend.sort_values("Date", ascending=True).tail(10)
            recent_trend["_label"] = recent_trend["Date"].dt.strftime("%d-%b") + " (" + recent_trend["Purchase ID"].str[-3:] + ")"
            st.bar_chart(recent_trend.set_index("_label")["Total amount"], use_container_width=True, height=350, color="#2e7d32")

    with breakdown_col:
        st.markdown("#### 🏞️ Breakdown")
        toggle = st.radio("Group by:", ["Farm", "Month"], horizontal=True, label_visibility="collapsed")
        if not fdf.empty:
            group_col = fdf["Farm Name"].fillna("(blank)") if toggle == "Farm" else fdf["Month"].fillna("Unknown")
            bdf = fdf.assign(_group=group_col).groupby("_group")["Total amount"].sum().sort_values(ascending=False).reset_index().rename(columns={"_group": "Category", "Total amount": "Amount"})
            st.bar_chart(bdf.set_index("Category")["Amount"], use_container_width=True, height=350, color="#ff9800")

# --- TAB 2: EMPLOYEE REPORT ---
with tab2:
    st.markdown("#### 👷 Employee Performance Report")
    if fdf.empty:
        st.info("No data available.")
    else:
        emp_rows = []
        for emp_name, group in fdf.groupby("Employee Name"):
            if not emp_name or emp_name in ("None", "Unknown"): continue
            t_qty = group["Qty"].sum(); t_amt = group["Total amount"].sum(); t_frt = group["Transportation Amount"].sum()
            w_moisture = (group["Moisture %"] * group["Qty"]).sum() / t_qty if t_qty > 0 else 0
            qty_tonne = t_qty / 1000.0
            avg_cost_kg = (t_amt / t_qty) if t_qty > 0 else 0
            frt_per_kg = (t_frt / t_qty) if t_qty > 0 else 0
            total_cost_kg = avg_cost_kg + frt_per_kg
            total_cost_wo_moist = total_cost_kg / (1 - (w_moisture / 100)) if w_moisture < 100 else 0
            emp_rows.append({"EMPLOYEE": emp_name, "Qty(Tonne)": qty_tonne, "Moist %": w_moisture, "AVG COST KG": avg_cost_kg, "FRT PER KG": frt_per_kg, "TOTAL COST/KG": total_cost_kg, "TOTAL COST/KG W/O MOIST": total_cost_wo_moist})
        
        if emp_rows:
            emp_df = pd.DataFrame(emp_rows)
            tot_qty = fdf["Qty"].sum()
            tot_amt = fdf["Total amount"].sum()
            tot_frt = fdf["Transportation Amount"].sum()
            tot_moist = (fdf["Moisture %"] * fdf["Qty"]).sum() / tot_qty if tot_qty > 0 else 0
            tot_avg = tot_amt / tot_qty if tot_qty > 0 else 0
            tot_frt_kg = tot_frt / tot_qty if tot_qty > 0 else 0
            tot_cost = tot_avg + tot_frt_kg
            tot_wo = tot_cost / (1 - (tot_moist / 100)) if tot_moist < 100 else 0

            total_row = pd.DataFrame([{"EMPLOYEE": "TOTAL", "Qty(Tonne)": tot_qty/1000, "Moist %": tot_moist, "AVG COST KG": tot_avg, "FRT PER KG": tot_frt_kg, "TOTAL COST/KG": tot_cost, "TOTAL COST/KG W/O MOIST": tot_wo}])
            emp_df = pd.concat([emp_df, total_row], ignore_index=True)
            
            st.dataframe(emp_df.style.format({"Qty(Tonne)": "{:,.2f}", "Moist %": "{:.2f}%", "AVG COST KG": "{:.2f}", "FRT PER KG": "{:.2f}", "TOTAL COST/KG": "{:.2f}", "TOTAL COST/KG W/O MOIST": "{:.2f}"}, na_rep=""), use_container_width=True, hide_index=True)

# --- TAB 3: SUPPLIER REPORT ---
with tab3:
    st.markdown("#### 🏢 Supplier-wise Item Report")
    if fdf.empty:
        st.info("No data available.")
    else:
        items_df["Purchase ID"] = items_df["Purchase ID"].astype(str).str.strip()
        linked_ids = set(items_df.loc[items_df["Purchase ID"] != "", "Purchase ID"].unique())
        exploded_rows = []
        
        for _, p in fdf.iterrows():
            pid = str(p["Purchase ID"]).strip()
            header_item = str(p.get("Item", "") or "").strip()
            if pid in linked_ids:
                for _, li in items_df[items_df["Purchase ID"] == pid].iterrows():
                    exploded_rows.append({"Supplier Name": p.get("Party name", ""), "Item": str(li.get("Item", "")).strip(), "Qty": pd.to_numeric(li.get("Qty"), errors="coerce"), "Moisture %": pd.to_numeric(li.get("Moisture %"), errors="coerce"), "Amount": pd.to_numeric(li.get("Amount"), errors="coerce")})
            else:
                if header_item and header_item.lower() not in ("", "multiple items"):
                    exploded_rows.append({"Supplier Name": p.get("Party name", ""), "Item": header_item, "Qty": pd.to_numeric(p.get("Qty"), errors="coerce"), "Moisture %": pd.to_numeric(p.get("Moisture %"), errors="coerce"), "Amount": pd.to_numeric(p.get("Total amount"), errors="coerce")})

        exploded_df = pd.DataFrame(exploded_rows)
        if not exploded_df.empty:
            exploded_df = exploded_df.fillna({"Qty": 0, "Moisture %": 0, "Amount": 0})
            supp_rows = []
            for (party, item), group in exploded_df.groupby(["Supplier Name", "Item"]):
                if not party or party == "None": continue
                t_qty = group["Qty"].sum(); t_amt = group["Amount"].sum()
                w_moisture = (group["Moisture %"] * group["Qty"]).sum() / t_qty if t_qty > 0 else 0
                net_qty = t_qty * (1 - (w_moisture / 100))
                avg_per_kg = (t_amt / net_qty) if net_qty > 0 else 0
                supp_rows.append({"Supplier Name": party, "Item Purchased": item, "Qty": t_qty, "Avg Moist %": w_moisture, "Net Qty": net_qty, "Total Amount": t_amt, "Avg / KG": avg_per_kg})
            
            supp_df = pd.DataFrame(supp_rows).sort_values(["Supplier Name", "Total Amount"], ascending=[True, False])
            st.dataframe(supp_df.style.format({"Qty": "{:,.2f}", "Avg Moist %": "{:.2f}%", "Net Qty": "{:,.2f}", "Total Amount": "₹ {:,.2f}", "Avg / KG": "₹ {:,.2f}"}, na_rep=""), use_container_width=True, hide_index=True)
        else:
            st.info("No specific item data found.")

# ------------------------------------------------------------
# 5e. RECENT PURCHASES (At bottom)
# ------------------------------------------------------------
st.markdown("---")
st.markdown("#### 🕒 Recent Purchases")
if not fdf.empty:
    recent = fdf.sort_values("Date", ascending=False).head(10)[["Purchase ID", "Date", "Party name", "Farm Name", "Invoice no", "Item", "Qty", "Total amount"]]
    recent["Date"] = recent["Date"].dt.strftime("%d-%b-%Y")
    st.dataframe(recent.style.format({"Qty": "{:,.2f}", "Total amount": "₹ {:,.2f}"}, na_rep=""), use_container_width=True, hide_index=True)

with st.expander("⚙️ System Status"):
    if st.button("Run DB Healthcheck"):
        with st.spinner("Checking..."):
            hc = sheets_db.healthcheck()
            if hc.get("status") == "ok":
                st.success("Database connected successfully!")
            else:
                st.error(f"DB Error: {hc.get('message')}")
