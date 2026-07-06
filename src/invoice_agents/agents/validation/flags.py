"""Deterministic validation flags. No LLM involved -- must be 100% reproducible."""
from collections import defaultdict

from src.invoice_agents.agents.validation.db import check_duplicate, get_stock

STOCK_MISMATCH = "STOCK_MISMATCH"
ZERO_STOCK_SUSPICIOUS = "ZERO_STOCK_SUSPICIOUS"
UNKNOWN_ITEM = "UNKNOWN_ITEM"
NEGATIVE_QTY = "NEGATIVE_QTY"
DATA_INTEGRITY_ERROR = "DATA_INTEGRITY_ERROR"
DUPLICATE_INVOICE = "DUPLICATE_INVOICE"
TOTAL_MISMATCH = "TOTAL_MISMATCH"
FOREIGN_CURRENCY = "FOREIGN_CURRENCY"
FRAUD_SIGNAL = "FRAUD_SIGNAL"
EXTRACTION_FAILED = "EXTRACTION_FAILED"

ALL_FLAG_TYPES = (
    STOCK_MISMATCH,
    ZERO_STOCK_SUSPICIOUS,
    UNKNOWN_ITEM,
    NEGATIVE_QTY,
    DATA_INTEGRITY_ERROR,
    DUPLICATE_INVOICE,
    TOTAL_MISMATCH,
    FOREIGN_CURRENCY,
    FRAUD_SIGNAL,
    EXTRACTION_FAILED,
)

TOTAL_MISMATCH_TOLERANCE = 0.01

# FOREIGN_CURRENCY is informational only -- PLAN.md's scenario table expects
# INV-1014 (EUR) to be "PAID w/ warning", not rejected.
NON_BLOCKING_FLAG_TYPES = {FOREIGN_CURRENCY}


def _flag(flag_type: str, message: str, **details) -> dict:
    return {
        "type": flag_type,
        "message": message,
        "blocking": flag_type not in NON_BLOCKING_FLAG_TYPES,
        **details,
    }


def aggregate_quantities(items: list[dict]) -> dict:
    """Group by item name and sum quantities -- same item on multiple lines must combine."""
    totals: dict[str, int] = defaultdict(int)
    for item in items:
        totals[item["name"]] += item["qty"]
    return dict(totals)


def compute_flags(invoice: dict, db_path: str) -> list[dict]:
    flags: list[dict] = []

    vendor = invoice.get("vendor") or ""
    total = invoice.get("total", 0)
    if not vendor.strip():
        flags.append(_flag(DATA_INTEGRITY_ERROR, "Vendor is empty"))
    if total < 0:
        flags.append(_flag(DATA_INTEGRITY_ERROR, f"Total is negative: {total}"))

    invoice_id = invoice.get("invoice_id")
    if invoice_id and check_duplicate(invoice_id, db_path=db_path):
        flags.append(_flag(DUPLICATE_INVOICE, f"{invoice_id} has already been paid"))

    aggregated = aggregate_quantities(invoice.get("items", []))
    for name, qty in aggregated.items():
        if qty < 0:
            flags.append(_flag(NEGATIVE_QTY, f"{name} has negative aggregated quantity: {qty}", item=name))
            continue
        stock = get_stock(name, db_path=db_path)
        if stock is None:
            flags.append(_flag(UNKNOWN_ITEM, f"{name} is not in the inventory catalogue", item=name))
        elif stock == 0:
            flags.append(_flag(ZERO_STOCK_SUSPICIOUS, f"{name} has zero stock on hand", item=name))
        elif qty > stock:
            flags.append(
                _flag(STOCK_MISMATCH, f"{name} requested qty {qty} exceeds stock {stock}", item=name, requested=qty, stock=stock)
            )

    subtotal = invoice.get("subtotal")
    tax_amount = invoice.get("tax_amount")
    shipping = invoice.get("shipping") or 0.0
    if subtotal is not None and tax_amount is not None:
        computed_total = subtotal + tax_amount + shipping
        diff = abs(computed_total - total)
        if diff > TOTAL_MISMATCH_TOLERANCE:
            flags.append(
                _flag(
                    TOTAL_MISMATCH,
                    f"subtotal+tax+shipping={computed_total} but stated total={total} (diff {diff:.2f})",
                    computed_total=computed_total,
                    stated_total=total,
                )
            )

    currency = invoice.get("currency") or "USD"
    if currency != "USD":
        flags.append(_flag(FOREIGN_CURRENCY, f"Currency is {currency}, not USD", currency=currency))

    for signal in invoice.get("fraud_signals") or []:
        flags.append(_flag(FRAUD_SIGNAL, signal))

    return flags
