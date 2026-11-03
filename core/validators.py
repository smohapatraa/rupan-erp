"""GSTIN validation + GST calculation engine."""
import re

GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")

GST_RATES = [0, 5, 12, 18, 28]

def validate_gstin(gstin: str) -> bool:
    if not gstin:
        return True  # optional
    gstin = gstin.strip().upper()
    return bool(GSTIN_REGEX.match(gstin))

def compute_line(qty: float, moisture_pct: float, price: float,
                 discount_pct: float, gst_rate: float,
                 is_intra_state: bool) -> dict:
    moisture_qty = round(qty * moisture_pct / 100, 3)
    actual_qty = round(qty - moisture_qty, 3)
    gross_amount = round(qty * price, 2)
    discount_amt = round(gross_amount * discount_pct / 100, 2)
    taxable_value = round(gross_amount - discount_amt, 2)

    if is_intra_state:
        cgst = round(taxable_value * gst_rate / 200, 2)
        sgst = cgst
        igst = 0.0
    else:
        cgst = 0.0
        sgst = 0.0
        igst = round(taxable_value * gst_rate / 100, 2)

    line_total = round(taxable_value + cgst + sgst + igst, 2)
    return {
        "moisture_qty": moisture_qty,
        "actual_qty": actual_qty,
        "gross_amount": gross_amount,
        "discount_amt": discount_amt,
        "taxable_value": taxable_value,
        "cgst": cgst,
        "sgst": sgst,
        "igst": igst,
        "line_total": line_total,
    }

def compute_totals(lines: list[dict]) -> dict:
    subtotal = round(sum(l["taxable_value"] for l in lines), 2)
    total_discount = round(sum(l["discount_amt"] for l in lines), 2)
    cgst = round(sum(l["cgst"] for l in lines), 2)
    sgst = round(sum(l["sgst"] for l in lines), 2)
    igst = round(sum(l["igst"] for l in lines), 2)
    pre_round = round(subtotal + cgst + sgst + igst, 2)
    round_off = round(round(pre_round) - pre_round, 2)
    total = round(pre_round + round_off, 2)
    return {
        "subtotal": subtotal,
        "total_discount": total_discount,
        "cgst": cgst,
        "sgst": sgst,
        "igst": igst,
        "round_off": round_off,
        "total_amount": total,
    }
