import streamlit as st
import pandas as pd
from datetime import date
import io

# Adjust this import to match your project (core.sheets_db is what your repo shows)
from core import sheets_db

st.set_page_config(page_title="Purchase Register — Download", page_icon="⬇️", layout="wide")
st.title("⬇️ Purchase Register — Filter & Download")

# ------------------------------------------------------------
# 1. LOAD THE PURCHASES SHEET (tab name = "purchases")
# ------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner="Loading purchases…")
def load_purchases() -> pd.DataFrame:
    # 👇 Replace `read_sheet("purchases")` with your real reader function if named differently.
    # Common patterns in sheets_db.py:
    #   read_sheet("purchases") / get_sheet("purchases") / read_purchases()
    if hasattr(sheets_db, "read_sheet"):
        df = sheets_db.read_sheet("purchases")
    elif hasattr(sheets_db, "get_sheet"):
        df = sheets_db.get_sheet("purchases")
    elif hasattr(sheets_db, "read_purchases"):
        df = sheets_db.read_purchases()
    else:
        raise RuntimeError(
            "No known reader found in core.sheets_db. "
            "Add one of: read_sheet('purchases'), get_sheet('purchases'), read_purchases()."
        )
    return df

try:
    df = load_purchases()
except Exception as e:
    st.error(f"Failed to load purchases: {e}")
    st.stop()

if df is None or df.empty:
    st.warning("The `purchases` tab is empty.")
    st.stop()

# ------------------------------------------------------------
# 2. CLEAN TYPES (safe even if already correct)
# ------------------------------------------------------------
# Date -> datetime
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

# Year came as 2026.0 -> make it a clean int for display (keep original column too)
if "Year" in df.columns:
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")

# Farm Name -> string, strip spaces, keep blanks as "(blank)"
df["Farm Name"] = df["Farm Name"].astype("string").str.strip()

# ------------------------------------------------------------
# 3. FILTERS: Farm name + Period (Month/Year  OR  Date range)
# ------------------------------------------------------------
st.subheader("Filters")

f1, f2, f3 = st.columns([2, 2, 2])

# ---- Farm name ----
farm_values = (
    df["Farm Name"].dropna().unique().tolist()
)
farm_values = sorted([v for v in farm_values if v not in ("", "None")])
if (df["Farm Name"].isna() | (df["Farm Name"] == "")).any():
    farm_values.append("(blank)")

with f1:
    selected_farms = st.multiselect(
        "Farm name",
        options=farm_values,
        default=farm_values,
        help="Leave all selected to include every farm, including blanks.",
    )

# ---- Period: choose mode ----
with f2:
    period_mode = st.radio(
        "Period filter by",
        options=["Month + Year", "Date range"],
        horizontal=True,
    )

if period_mode == "Month + Year":
    # Build available (Year, Month) pairs from data
    pairs = (
        df.dropna(subset=["Date"])
          .assign(_y=df["Date"].dt.year, _m=df["Date"].dt.month)
          .loc[:, ["_y", "_m"]]
          .drop_duplicates()
          .sort_values(["_y", "_m"])
    )
    pair_labels = [f"{y}-{m:02d}" for y, m in pairs.itertuples(index=False)]

    with f3:
        selected_periods = st.multiselect(
            "Period (YYYY-MM)",
            options=pair_labels,
            default=pair_labels,
            help="Pick one or more months.",
        )

    # Apply
    df["_period"] = df["Date"].dt.strftime("%Y-%m")
    mask_period = df["_period"].isin(selected_periods)

else:
    min_d = df["Date"].min().date()
    max_d = df["Date"].max().date()
    today = date.today()
    default_start = max(min_d, today.replace(day=1))
    default_end = min(max_d, today)
    if default_start > default_end:
        default_start, default_end = min_d, max_d

    with f3:
        start_date = st.date_input("From", value=default_start, min_value=min_d, max_value=max_d)
        end_date   = st.date_input("To",   value=default_end,   min_value=min_d, max_value=max_d)

    if start_date > end_date:
        st.error("'From' must be ≤ 'To'.")
        st.stop()

    mask_period = (df["Date"].dt.date >= start_date) & (df["Date"].dt.date <= end_date)

# ---- Farm mask (handle blanks) ----
include_blank = "(blank)" in selected_farms
mask_farm = df["Farm Name"].isin([f for f in selected_farms if f != "(blank)"])
if include_blank:
    mask_farm |= df["Farm Name"].isna() | (df["Farm Name"] == "")

# ---- Combine ----
filtered = df.loc[mask_farm & mask_period].copy()

# Drop helper col before display/download
filtered = filtered.drop(columns=["_period"], errors="ignore")

st.caption(
    f"**{len(filtered):,}** of **{len(df):,}** rows match. "
    f"Showing all **{filtered.shape[1]}** columns."
)

# ------------------------------------------------------------
# 4. PREVIEW — ALL HEADERS
# ------------------------------------------------------------
st.subheader("Preview")
st.dataframe(filtered, use_container_width=True, hide_index=True, height=420)

# ------------------------------------------------------------
# 5. DOWNLOAD (Excel + CSV)
# ------------------------------------------------------------
st.subheader("Download")

def to_excel(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Purchase Register")
    return buf.getvalue()

# Filename reflects the filter mode
if period_mode == "Month + Year":
    label = "_".join(selected_periods) if selected_periods else "none"
else:
    label = f"{start_date}_to_{end_date}"
file_base = f"purchase_register_{label}"

c1, c2 = st.columns(2)
with c1:
    st.download_button(
        "⬇️ Download Excel (.xlsx)",
        data=to_excel(filtered),
        file_name=f"{file_base}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        disabled=filtered.empty,
    )
with c2:
    st.download_button(
        "⬇️ Download CSV (.csv)",
        data=filtered.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{file_base}.csv",
        mime="text/csv",
        use_container_width=True,
        disabled=filtered.empty,
    )

if filtered.empty:
    st.info("No rows match the current filters — downloads are disabled.")
