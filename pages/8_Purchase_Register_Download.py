import streamlit as st
import pandas as pd
from datetime import date
import io

from core import sheets_db
from core import auth

auth.require_login()

st.title("⬇️ Purchase Register — Filter & Download")

# Manual refresh — useful after new entries
if st.button("🔄 Refresh data"):
    st.cache_data.clear()
    st.rerun()

# ------------------------------------------------------------
# 1. LOAD DATA — purchases + purchase_items
# ------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner="Loading purchases…")
def load_data():
    return sheets_db.list_all("purchases"), sheets_db.list_all("purchase_items")

try:
    purchase_rows, item_rows = load_data()
except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.stop()

if not purchase_rows:
    st.info("No purchases recorded yet.")
    st.stop()

df = pd.DataFrame(purchase_rows)
items_df = pd.DataFrame(item_rows) if item_rows else pd.DataFrame(
    columns=["Purchase ID", "Item"]
)

# ------------------------------------------------------------
# 2. RESOLVE ITEM COLUMN
#    - single line item   -> real item name
#    - multiple line items -> comma-joined list
#    - no line items      -> keep original Item value
# ------------------------------------------------------------
def resolve_item_names(purchases: pd.DataFrame, items: pd.DataFrame) -> pd.Series:
    if items.empty or "Purchase ID" not in items.columns:
        return purchases["Item"].astype("string")

    items = items.copy()
    items["Purchase ID"] = items["Purchase ID"].astype(str).str.strip()
    items["Item"] = items["Item"].astype("string").str.strip()

    grouped = (
        items.loc[items["Item"].notna() & (items["Item"] != "")]
             .drop_duplicates(subset=["Purchase ID", "Item"])
             .groupby("Purchase ID")["Item"]
             .apply(lambda s: ", ".join(s.tolist()))
    )

    orig = purchases["Item"].astype("string")
    pid  = purchases["Purchase ID"].astype("string").str.strip()

    resolved = orig.copy()
    for i, (p, o) in enumerate(zip(pid, orig)):
        if p in grouped.index:
            names = grouped.loc[p]
            if isinstance(names, pd.Series):
                names = ", ".join(names.tolist())
            resolved.iloc[i] = names
    return resolved

df["Item"] = resolve_item_names(df, items_df)

# ------------------------------------------------------------
# 3. TYPE CLEANUP
# ------------------------------------------------------------
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Year"] = pd.to_numeric(df.get("Year"), errors="coerce")
df["Farm Name"] = df["Farm Name"].astype("string").str.strip()

# ------------------------------------------------------------
# 4. FILTERS — Farm name + Period
# ------------------------------------------------------------
st.subheader("Filters")
f1, f2, f3 = st.columns([2, 2, 2])

farm_vals = sorted(
    [v for v in df["Farm Name"].dropna().unique().tolist() if v not in ("", "None")]
)
has_blank = (df["Farm Name"].isna() | (df["Farm Name"] == "")).any()
farm_options = farm_vals + (["(blank)"] if has_blank else [])

with f1:
    selected_farms = st.multiselect(
        "Farm name", options=farm_options, default=farm_options
    )

with f2:
    period_mode = st.radio(
        "Period filter by", ["Month + Year", "Date range"], horizontal=True
    )

if period_mode == "Month + Year":
    pairs = (
        df.dropna(subset=["Date"])
          .assign(_y=df["Date"].dt.year, _m=df["Date"].dt.month)
          .loc[:, ["_y", "_m"]]
          .drop_duplicates()
          .sort_values(["_y", "_m"])
    )
    period_labels = [f"{int(y)}-{int(m):02d}" for y, m in pairs.itertuples(index=False)]

    with f3:
        selected_periods = st.multiselect(
            "Period (YYYY-MM)", options=period_labels, default=period_labels
        )

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

include_blank = "(blank)" in selected_farms
mask_farm = df["Farm Name"].isin([f for f in selected_farms if f != "(blank)"])
if include_blank:
    mask_farm |= df["Farm Name"].isna() | (df["Farm Name"] == "")

filtered = df.loc[mask_farm & mask_period].copy()
filtered = filtered.drop(columns=["_period"], errors="ignore")

st.caption(
    f"**{len(filtered):,}** of **{len(df):,}** rows match. "
    f"Showing all **{filtered.shape[1]}** columns."
)

# ------------------------------------------------------------
# 5. PREVIEW
# ------------------------------------------------------------
st.subheader("Preview")
st.dataframe(filtered, use_container_width=True, hide_index=True, height=420)

# ------------------------------------------------------------
# 6. DOWNLOAD
# ------------------------------------------------------------
st.subheader("Download")

def to_excel(d: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        d.to_excel(w, index=False, sheet_name="Purchase Register")
    return buf.getvalue()

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
    st.info("No rows match the current filters — downloads disabled.")
