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
            
        st.markdown("<h1 style='text-align: center; color: #1e5631; margin-bottom: 0;'>Rupan Renewables</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666; font-size: 1.1em; margin-top: 5px;'>Sustainable Energy Solutions for a Greener Tomorrow</p>", unsafe_allow_html=True)
        
        st.write("") 
        
        with st.container():
            st.markdown("""
            <style>
            .login-container {
                background-color: #ffffff;
                padding: 2rem;
                border-radius: 12px;
                box-shadow: 0 10px 20px rgba(0,0,0,0.05);
                border-top: 6px solid #2e7d32;
            }
            </style>
            <div class="login-container">
            """, unsafe_allow_html=True)
            
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
    try:
        st.image("logo.png", use_container_width=True)
    except:
        pass
        
    st.markdown("<h2 style='text-align: center; color: #1e5631; margin-bottom: 0;'>Rupan Renewables</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #888; font-size: 0.85em;'>Biomass ERP System</p>", unsafe_allow_html=True)
    st.divider()
    
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

@st.cache_data(ttl=300, show_spinner="Loading dashboard…")
def load_dashboard_data():
    return (
        sheets_db.list_all("purchases"),
        sheets_db.list_all("purchase_items")
    )

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
            color="#2e7d32"
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
            color="#ff9800"
        )

# ------------------------------------------------------------
# 5f. EMPLOYEE PERFORMANCE REPORT
# ------------------------------------------------------------
st.markdown("---")
st.markdown("#### 👷 Employee Performance Report")

if fdf.empty:
    st.info("No data available for the selected filters.")
else:
    emp_rows = []
    for emp_name, group in fdf.groupby("Employee Name"):
        if not emp_name or emp_name == "None" or emp_name == "Unknown":
            continue
            
        t_qty = group["Qty"].sum()
        t_amt = group["Total amount"].sum()
        t_frt = group["Transportation Amount"].sum()
        
        w_moisture = (group["Moisture %"] * group["Qty"]).sum() / t_qty if t_qty > 0 else 0
        qty_tonne = t_qty / 1000.0
        avg_cost_kg = (t_amt / t_qty) if t_qty > 0 else 0
        frt_per_kg = (t_frt / t_qty) if t_qty > 0 else 0
        total_cost_kg = avg_cost_kg + frt_per_kg
        total_cost_wo_moist = total_cost_kg / (1 - (w_moisture / 100)) if w_moisture < 100 else 0

        emp_rows.append({
            "EMPLOYEE": emp_name,
            "Qty(Tonne)": qty_tonne,
            "Moist %": w_moisture,
            "AVG COST KG": avg_cost_kg,
            "FRT PER KG": frt_per_kg,
            "TOTAL COST PER KG": total_cost_kg,
            "TOTAL COST / KG W/O MOISTURE": total_cost_wo_moist
        })

    if emp_rows:
        emp_df = pd.DataFrame(emp_rows)
        
        tot_qty = emp_df["Qty(Tonne)"].sum()
        tot_amt = fdf["Total amount"].sum()
        tot_frt = fdf["Transportation Amount"].sum()
        tot_moist = (fdf["Moisture %"] * fdf["Qty"]).sum() / fdf["Qty"].sum() if fdf["Qty"].sum() > 0 else 0
        
        tot_avg_cost = (tot_amt / fdf["Qty"].sum()) if fdf["Qty"].sum() > 0 else 0
        tot_frt = (tot_frt / fdf["Qty"].sum()) if fdf["Qty"].sum() > 0 else 0
        tot_total_cost = tot_avg_cost + tot_frt
        tot_wo_moist = tot_total_cost / (1 - (tot_moist / 100)) if tot_moist < 100 else 0

        total_row_df = pd.DataFrame([{
            "EMPLOYEE": "TOTAL",
            "Qty(Tonne)": tot_qty,
            "Moist %": tot_moist,
            "AVG COST KG": tot_avg_cost,
            "FRT PER KG": tot_frt,
            "TOTAL COST PER KG": tot_total_cost,
            "TOTAL COST / KG W/O MOISTURE": tot_wo_moist
        }])
        
        emp_df = pd.concat([emp_df, total_row_df], ignore_index=True)
        
        st.dataframe(
            emp_df.style.format({
                "Qty(Tonne)": "{:,.2f}",
                "Moist %": "{:.2f}%",
                "AVG COST KG": "{:.2f}",
                "FRT PER KG": "{:.2f}",
                "TOTAL COST PER KG": "{:.2f}",
                "TOTAL COST / KG W/O MOISTURE": "{:.2f}"
            }, na_rep=""),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No Employee data available.")

# ------------------------------------------------------------
# 5g. SUPPLIER-WISE ITEM REPORT (FIXED)
# ------------------------------------------------------------
st.markdown("---")
st.markdown("#### 🏢 Supplier-wise Item Report")

if fdf.empty:
    st.info("No data available for the selected filters.")
else:
    # We rebuild the line items dynamically to handle both single and multi-item entries.
    # This prevents any KeyError issues from merging tables.
    
    items_df["Purchase ID"] = items_df["Purchase ID"].astype(str).str.strip()
    
    # Identify which purchases have linked line items
    linked_ids = set(items_df.loc[items_df["Purchase ID"] != "", "Purchase ID"].unique())
    
    exploded_rows = []
    for _, p in fdf.iterrows():
        pid = str(p["Purchase ID"]).strip()
        header_item = str(p.get("Item", "") or "").strip()
        
        # If it's a multi-item purchase with linked items
        if pid in linked_ids:
            sub = items_df[items_df["Purchase ID"] == pid]
            for _, li in sub.iterrows():
                exploded_rows.append({
                    "Supplier Name": p.get("Party name", ""),
                    "Item": str(li.get("Item", "")).strip(),
                    "Qty": pd.to_numeric(li.get("Qty"), errors="coerce"),
                    "Moisture %": pd.to_numeric(li.get("Moisture %"), errors="coerce"),
                    "Amount": pd.to_numeric(li.get("Amount"), errors="coerce"),
                })
        else:
            # If it's a single-item purchase (or legacy without line items)
            if header_item and header_item.lower() not in ("", "multiple items"):
                exploded_rows.append({
                    "Supplier Name": p.get("Party name", ""),
                    "Item": header_item,
                    "Qty": pd.to_numeric(p.get("Qty"), errors="coerce"),
                    "Moisture %": pd.to_numeric(p.get("Moisture %"), errors="coerce"),
                    "Amount": pd.to_numeric(p.get("Total amount"), errors="coerce"), 
                })

    exploded_df = pd.DataFrame(exploded_rows)

    if exploded_df.empty:
        st.info("No specific item data found for these purchases.")
    else:
        exploded_df = exploded_df.fillna({"Qty": 0, "Moisture %": 0, "Amount": 0})
        
        supp_rows = []
        # Group by BOTH Supplier and Item
        for (party, item), group in exploded_df.groupby(["Supplier Name", "Item"]):
            if not party or party == "None":
                continue
                
            t_qty = group["Qty"].sum()
            t_amt = group["Amount"].sum()
            
            # Weighted average moisture
            w_moisture = (group["Moisture %"] * group["Qty"]).sum() / t_qty if t_qty > 0 else 0
            
            # Net Qty after moisture
            net_qty = t_qty * (1 - (w_moisture / 100))
            
            # Average per kg based on Net Qty
            avg_per_kg = (t_amt / net_qty) if net_qty > 0 else 0

            supp_rows.append({
                "Supplier Name": party,
                "Item Purchased": item,
                "Qty": t_qty,
                "Avg Moist %": w_moisture,
                "Net Qty": net_qty,
                "Total Amount": t_amt,
                "Avg / KG (Net Qty)": avg_per_kg
            })

        if supp_rows:
            supp_df = pd.DataFrame(supp_rows)
            
            # Sort by Supplier Name
            supp_df = supp_df.sort_values(["Supplier Name", "Total Amount"], ascending=[True, False])
            
            st.dataframe(
                supp_df.style.format({
                    "Qty": "{:,.2f}",
                    "Avg Moist %": "{:.2f}%",
                    "Net Qty": "{:,.2f}",
                    "Total Amount": "₹ {:,.2f}",
                    "Avg / KG (Net Qty)": "₹ {:,.2f}"
                }, na_rep=""),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No Supplier data available.")

# ------------------------------------------------------------
# 5h. RECENT PURCHASES
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
# 5i. SYSTEM STATUS
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
