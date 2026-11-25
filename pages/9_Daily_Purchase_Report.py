import streamlit as st
import pandas as pd
from datetime import date
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)

from core import sheets_db
from core import auth

auth.require_login()

st.title("📅 Daily Purchase Report")

if st.button("🔄 Refresh data"):
    st.cache_data.clear()
    st.rerun()

# ------------------------------------------------------------
# 1. LOAD DATA
# ------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner="Loading…")
def load_data():
    return (
        sheets_db.list_all("purchases"),
        sheets_db.list_all("purchase_items"),
    )

try:
    purchase_rows, item_rows = load_data()
except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.stop()

if not purchase_rows:
    st.info("No purchases recorded yet.")
    st.stop()

purch_df = pd.DataFrame(purchase_rows)
items_df = (
    pd.DataFrame(item_rows)
    if item_rows
    else pd.DataFrame(columns=["Purchase ID", "Item", "Qty", "Moisture %", "Amount"])
)

purch_df["Date"] = pd.to_datetime(purch_df["Date"], errors="coerce")
purch_df["Farm Name"] = purch_df["Farm Name"].astype("string").str.strip()

# ------------------------------------------------------------
# 2. FILTERS — Date + Farm
# ------------------------------------------------------------
st.subheader("Filters")
f1, f2 = st.columns(2)

with f1:
    report_date = st.date_input("Date", value=date.today())

farm_vals = sorted(
    [v for v in purch_df["Farm Name"].dropna().unique().tolist() if v not in ("", "None")]
)
with f2:
    selected_farm = st.selectbox("Farm", ["All"] + farm_vals)

# ------------------------------------------------------------
# 3. EXPLODE INTO (purchase × item) LONG FORM
# ------------------------------------------------------------
def explode_purchases(purch: pd.DataFrame, items: pd.DataFrame) -> pd.DataFrame:
    items = items.copy()
    if "Purchase ID" not in items.columns:
        items["Purchase ID"] = ""
    items["Purchase ID"] = items["Purchase ID"].astype(str).str.strip()

    linked_ids = set(items.loc[items["Purchase ID"] != "", "Purchase ID"].unique())

    rows = []
    for _, p in purch.iterrows():
        pid = str(p["Purchase ID"]).strip()
        header_item = str(p.get("Item", "") or "").strip()

        if pid in linked_ids:
            sub = items[items["Purchase ID"] == pid]
            for _, li in sub.iterrows():
                rows.append({
                    "Purchase ID": pid,
                    "Date": p["Date"],
                    "Farm Name": p.get("Farm Name", ""),
                    "Party name": p.get("Party name", ""),
                    "Item": str(li.get("Item", "")).strip(),
                    "Qty": pd.to_numeric(li.get("Qty"), errors="coerce"),
                    "Moisture %": pd.to_numeric(li.get("Moisture %"), errors="coerce"),
                    "Amount": pd.to_numeric(li.get("Amount"), errors="coerce"),
                })
        else:
            if header_item and header_item.lower() not in ("", "multiple items"):
                rows.append({
                    "Purchase ID": pid,
                    "Date": p["Date"],
                    "Farm Name": p.get("Farm Name", ""),
                    "Party name": p.get("Party name", ""),
                    "Item": header_item,
                    "Qty": pd.to_numeric(p.get("Qty"), errors="coerce"),
                    "Moisture %": pd.to_numeric(p.get("Moisture %"), errors="coerce"),
                    "Amount": pd.to_numeric(p.get("Amount"), errors="coerce"),
                })

    return pd.DataFrame(rows)


long_df = explode_purchases(purch_df, items_df)

if long_df.empty:
    st.warning("No item data available.")
    st.stop()

# ------------------------------------------------------------
# 4. APPLY FILTERS
# ------------------------------------------------------------
mask = long_df["Date"].dt.date == report_date
if selected_farm != "All":
    mask &= long_df["Farm Name"] == selected_farm

day_df = long_df.loc[mask].copy()

if day_df.empty:
    st.warning(f"No purchases found for {report_date} / farm = {selected_farm}.")
    st.stop()

# ------------------------------------------------------------
# 5. ITEM SUMMARY
# ------------------------------------------------------------
st.subheader("📦 Item Summary")

item_qty = day_df.groupby("Item", dropna=False)["Qty"].sum()
item_amt = day_df.groupby("Item", dropna=False)["Amount"].sum()

summary_rows = []
for item in sorted(day_df["Item"].dropna().unique().tolist()):
    summary_rows.append({
        "Item": item,
        "Qty (Kgs)": float(item_qty.get(item, 0.0) or 0.0),
        "Amount (₹)": float(item_amt.get(item, 0.0) or 0.0),
    })

total_qty = sum(r["Qty (Kgs)"] for r in summary_rows)
total_amt = float(day_df["Amount"].sum())
summary_rows.append({"Item": "TOTAL", "Qty (Kgs)": total_qty, "Amount (₹)": total_amt})
summary_df = pd.DataFrame(summary_rows)

st.dataframe(
    summary_df.style.format({"Qty (Kgs)": "{:,.2f}", "Amount (₹)": "{:,.2f}"}),
    use_container_width=True,
    hide_index=True,
)

# ------------------------------------------------------------
# 6. PURCHASE LIST (dynamic item columns)
# ------------------------------------------------------------
st.subheader("📋 List of Purchases")

pivot = (
    day_df.pivot_table(
        index="Party name",
        columns="Item",
        values="Qty",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()
)

item_cols = sorted([c for c in pivot.columns if c != "Party name"])
pivot = pivot[["Party name"] + item_cols]

def weighted_moisture(g: pd.DataFrame) -> float:
    q = g["Qty"].fillna(0)
    m = g["Moisture %"].fillna(0)
    tq = q.sum()
    return float((q * m).sum() / tq) if tq > 0 else 0.0

moisture_by_party = (
    day_df.groupby("Party name", dropna=False).apply(weighted_moisture).to_dict()
)
total_qty_by_party = day_df.groupby("Party name", dropna=False)["Qty"].sum().to_dict()
amount_by_party = day_df.groupby("Party name", dropna=False)["Amount"].sum().to_dict()

rename = {c: f"{c} (Kgs)" for c in item_cols}
pivot = pivot.rename(columns=rename)

pivot.insert(1, "Moisture %", [round(moisture_by_party.get(p, 0.0), 2) for p in pivot["Party name"]])
pivot["Total (Kgs)"] = [float(total_qty_by_party.get(p, 0.0) or 0.0) for p in pivot["Party name"]]
pivot["Amount (₹)"] = [float(amount_by_party.get(p, 0.0) or 0.0) for p in pivot["Party name"]]
pivot.insert(0, "S.No", range(1, len(pivot) + 1))

total_row = {"S.No": "", "Party name": "TOTAL", "Moisture %": ""}
for c in [c for c in pivot.columns if c not in ("S.No", "Party name", "Moisture %")]:
    total_row[c] = float(pivot[c].sum())
pivot = pd.concat([pivot, pd.DataFrame([total_row])], ignore_index=True)

fmt = {"Moisture %": "{:,.2f}"}
for c in pivot.columns:
    if c.endswith("(Kgs)") or c.endswith("(₹)"):
        fmt[c] = "{:,.2f}"

st.dataframe(
    pivot.style.format(fmt, na_rep=""),
    use_container_width=True,
    hide_index=True,
)

# ------------------------------------------------------------
# 7. PDF BUILDER
#    - All columns always fit on ONE page width (auto-shrink font/width)
#    - Rows paginate to extra pages if needed (header repeats)
# ------------------------------------------------------------
farm_label = "All Farms" if selected_farm == "All" else selected_farm

def build_pdf() -> bytes:
    buf = io.BytesIO()
    page = landscape(A4)
    page_w, page_h = page
    margin_lr = 8 * mm
    margin_tb = 10 * mm
    printable_w = page_w - 2 * margin_lr

    doc = SimpleDocTemplate(
        buf,
        pagesize=page,
        leftMargin=margin_lr,
        rightMargin=margin_lr,
        topMargin=margin_tb,
        bottomMargin=margin_tb,
        title=f"Daily Purchase {report_date}",
    )

    styles = getSampleStyleSheet()
    h_company = ParagraphStyle("h_company", parent=styles["Title"], fontSize=14, leading=16, spaceAfter=2)
    h_sub     = ParagraphStyle("h_sub", parent=styles["Normal"], fontSize=10, leading=12)
    h_section = ParagraphStyle("h_section", parent=styles["Heading2"], fontSize=11, leading=13, spaceBefore=6, spaceAfter=4)
    h_small   = ParagraphStyle("h_small", parent=styles["Normal"], fontSize=8, leading=10)

    story = []

    # --- Header block ---
    story.append(Paragraph("Rupan Renewables", h_company))
    story.append(Paragraph(f"Farm: <b>{farm_label}</b>", h_sub))
    story.append(Paragraph("Address: Kharupetia, Assam", h_sub))
    story.append(Paragraph("Daily Purchase Sheet", h_sub))
    story.append(Paragraph(f"Dated: <b>{report_date.strftime('%d/%m/%Y')}</b>", h_sub))
    story.append(Spacer(1, 6))

    # --- Item Summary table ---
    story.append(Paragraph("Item Summary", h_section))
    sum_data = [["Item", "Qty (Kgs)", "Unit", "Amount (Rs)"]]
    for _, r in summary_df.iterrows():
        q = r["Qty (Kgs)"]
        a = r["Amount (₹)"]
        sum_data.append([
            str(r["Item"]),
            f"{float(q):,.2f}" if pd.notna(q) else "",
            "Kgs",
            f"{float(a):,.2f}" if pd.notna(a) else "",
        ])

    sum_col_w = [printable_w * w for w in (0.45, 0.20, 0.10, 0.25)]
    sum_tbl = Table(sum_data, colWidths=sum_col_w, hAlign="LEFT", repeatRows=1)
    sum_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF7")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F4F4F4")),
    ]))
    story.append(sum_tbl)
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"<b>Purchase Amount:</b> Rs {total_amt:,.2f}", h_small))
    story.append(Spacer(1, 10))

    # --- List of Purchases (dynamic cols, auto-fit to ONE page width) ---
    story.append(Paragraph("List of Purchases", h_section))

    headers = list(pivot.columns)
    ncols = len(headers)

    # Auto font size: shrink as column count grows (min 5pt)
    if ncols <= 6:      base_fs = 8.5
    elif ncols <= 8:    base_fs = 8.0
    elif ncols <= 10:   base_fs = 7.5
    elif ncols <= 13:   base_fs = 6.8
    elif ncols <= 16:   base_fs = 6.2
    elif ncols <= 20:   base_fs = 5.6
    else:               base_fs = 5.0

    header_fs = min(base_fs + 0.5, 9)

    # Column width weights
    weights = []
    for h in headers:
        if h == "S.No":              weights.append(0.5)
        elif h == "Party name":      weights.append(2.4)
        elif h == "Moisture %":      weights.append(0.9)
        elif h == "Total (Kgs)":     weights.append(1.3)
        elif h == "Amount (₹)":      weights.append(1.4)
        else:                        weights.append(1.0)  # per-item columns

    total_w = sum(weights)
    col_widths = [printable_w * w / total_w for w in weights]

    # Build data rows
    cell_style = ParagraphStyle(
        "cell", fontSize=base_fs, leading=base_fs + 1.5, wordWrap="CJK"
    )

    data = [headers]
    for _, r in pivot.iterrows():
        row = []
        for h in headers:
            v = r[h]
            if h == "S.No":
                row.append(str(v) if pd.notna(v) and str(v) != "" else "")
            elif h == "Party name":
                txt = str(v) if pd.notna(v) else ""
                row.append(Paragraph(txt, cell_style))
            elif h == "Moisture %":
                row.append(f"{float(v):,.2f}" if pd.notna(v) and str(v) != "" else "")
            else:
                row.append(f"{float(v):,.2f}" if pd.notna(v) and str(v) != "" else "")
        data.append(row)

    tbl = Table(
        data,
        colWidths=col_widths,
        repeatRows=1,
        hAlign="LEFT",
    )

    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF7")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), header_fs),
        ("FONTSIZE", (0, 1), (-1, -1), base_fs),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
        ("ALIGN", (1, 1), (1, -1), "LEFT"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F4F4F4")),
    ]
    tbl.setStyle(TableStyle(style))
    story.append(tbl)

    # --- Signatures ---
    story.append(Spacer(1, 20))
    sig_data = [["Prepared By:", "Verified By:", "Approved By:"]]
    sig_tbl = Table(sig_data, colWidths=[printable_w / 3] * 3, hAlign="LEFT")
    sig_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 24),
    ]))
    story.append(sig_tbl)

    doc.build(story)
    return buf.getvalue()


# ------------------------------------------------------------
# 8. DOWNLOAD BUTTONS
# ------------------------------------------------------------
st.subheader("⬇️ Download")

st.download_button(
    "⬇️ Download PDF",
    data=build_pdf(),
    file_name=f"daily_purchase_{report_date.strftime('%Y%m%d')}_{farm_label.replace(' ', '_')}.pdf",
    mime="application/pdf",
    use_container_width=True,
)

st.download_button(
    "⬇️ Download CSV (raw rows)",
    data=day_df.to_csv(index=False).encode("utf-8-sig"),
    file_name=f"daily_purchase_raw_{report_date.strftime('%Y%m%d')}.csv",
    mime="text/csv",
    use_container_width=True,
)
