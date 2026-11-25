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

    # --- Item Summary table (small, fixed 4 cols) ---
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

    # Column width weights (S.No narrow, Party wide, Amount wide, others equal)
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

    # Build data rows with formatted strings
    data = [headers]
    for _, r in pivot.iterrows():
        row = []
        for h in headers:
            v = r[h]
            if h in ("S.No",):
                row.append(str(v) if pd.notna(v) and str(v) != "" else "")
            elif h == "Party name":
                # wrap long party names
                txt = str(v) if pd.notna(v) else ""
                row.append(Paragraph(txt, ParagraphStyle(
                    "cell", fontSize=base_fs, leading=base_fs + 1.5, wordWrap="CJK"
                )))
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
        ("FONTSIZE", (0, 0), (-1, 0), header_fs),       # header font
        ("FONTSIZE", (0, 1), (-1, -1), base_fs),        # body font
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),     # S.No
        ("ALIGN", (1, 1), (1, -1), "LEFT"),       # Party
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),     # numeric
        # Bold TOTAL row
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
