from src.invoice_agents.agents.validation.db import record_payment
from src.invoice_agents.agents.validation.flags import (
    DATA_INTEGRITY_ERROR,
    DUPLICATE_INVOICE,
    FOREIGN_CURRENCY,
    FRAUD_SIGNAL,
    NEGATIVE_QTY,
    STOCK_MISMATCH,
    TOTAL_MISMATCH,
    UNKNOWN_ITEM,
    ZERO_STOCK_SUSPICIOUS,
    compute_flags,
)


def _invoice(**overrides):
    base = {
        "invoice_id": "INV-TEST",
        "vendor": "Test Co",
        "items": [{"name": "WidgetA", "qty": 5, "unit_price": 250.0}],
        "subtotal": 1250.0,
        "tax_amount": 0.0,
        "shipping": 0.0,
        "total": 1250.0,
        "currency": "USD",
        "fraud_signals": [],
    }
    base.update(overrides)
    return base


def test_clean_passes(fresh_db):
    invoice = _invoice(items=[{"name": "WidgetA", "qty": 10, "unit_price": 250.0}])
    assert compute_flags(invoice, db_path=fresh_db) == []


def test_stock_mismatch(fresh_db):
    invoice = _invoice(items=[{"name": "GadgetX", "qty": 20, "unit_price": 750.0}])
    flags = compute_flags(invoice, db_path=fresh_db)
    assert any(f["type"] == STOCK_MISMATCH for f in flags)


def test_zero_stock(fresh_db):
    invoice = _invoice(items=[{"name": "FakeItem", "qty": 1, "unit_price": None}])
    flags = compute_flags(invoice, db_path=fresh_db)
    assert any(f["type"] == ZERO_STOCK_SUSPICIOUS for f in flags)


def test_unknown_item(fresh_db):
    # Option B: WidgetC / SuperGizmo / MegaSprocket are unseeded -> UNKNOWN_ITEM.
    invoice = _invoice(items=[{"name": "SuperGizmo", "qty": 1, "unit_price": 400.0}])
    flags = compute_flags(invoice, db_path=fresh_db)
    assert any(f["type"] == UNKNOWN_ITEM for f in flags)


def test_negative_qty(fresh_db):
    invoice = _invoice(items=[{"name": "WidgetA", "qty": -5, "unit_price": 250.0}])
    flags = compute_flags(invoice, db_path=fresh_db)
    assert any(f["type"] == NEGATIVE_QTY for f in flags)


def test_empty_vendor(fresh_db):
    invoice = _invoice(vendor="")
    flags = compute_flags(invoice, db_path=fresh_db)
    assert any(f["type"] == DATA_INTEGRITY_ERROR for f in flags)


def test_negative_amount(fresh_db):
    invoice = _invoice(total=-250.0)
    flags = compute_flags(invoice, db_path=fresh_db)
    assert any(f["type"] == DATA_INTEGRITY_ERROR for f in flags)


def test_qty_aggregation(fresh_db):
    """CRITICAL: same item on multiple lines must aggregate before comparing to stock."""
    invoice = _invoice(
        items=[
            {"name": "WidgetA", "qty": 8, "unit_price": 250.0},
            {"name": "WidgetA", "qty": 4, "unit_price": 250.0},
        ]
    )
    assert compute_flags(invoice, db_path=fresh_db) == []


def test_qty_aggregation_fail(fresh_db):
    """Aggregated qty exceeds stock even though each individual line is fine."""
    invoice = _invoice(
        items=[
            {"name": "WidgetA", "qty": 10, "unit_price": 250.0},
            {"name": "WidgetA", "qty": 8, "unit_price": 250.0},
        ]
    )
    flags = compute_flags(invoice, db_path=fresh_db)
    assert any(f["type"] == STOCK_MISMATCH for f in flags)


def test_total_mismatch(fresh_db):
    invoice = _invoice(subtotal=100.0, tax_amount=0.0, total=150.0)
    flags = compute_flags(invoice, db_path=fresh_db)
    assert any(f["type"] == TOTAL_MISMATCH for f in flags)


def test_foreign_currency(fresh_db):
    invoice = _invoice(currency="EUR")
    flags = compute_flags(invoice, db_path=fresh_db)
    assert any(f["type"] == FOREIGN_CURRENCY for f in flags)


def test_foreign_currency_is_non_blocking(fresh_db):
    """PLAN.md: INV-1014 (EUR) should be PAID w/ warning, not rejected."""
    invoice = _invoice(currency="EUR")
    flags = compute_flags(invoice, db_path=fresh_db)
    currency_flag = next(f for f in flags if f["type"] == FOREIGN_CURRENCY)
    assert currency_flag["blocking"] is False


def test_stock_mismatch_is_blocking(fresh_db):
    invoice = _invoice(items=[{"name": "GadgetX", "qty": 20, "unit_price": 750.0}])
    flags = compute_flags(invoice, db_path=fresh_db)
    mismatch_flag = next(f for f in flags if f["type"] == STOCK_MISMATCH)
    assert mismatch_flag["blocking"] is True


def test_duplicate_invoice(fresh_db):
    record_payment("INV-TEST", "Test Co", 1250.0, "2026-01-01T00:00:00", db_path=fresh_db)
    invoice = _invoice()
    flags = compute_flags(invoice, db_path=fresh_db)
    assert any(f["type"] == DUPLICATE_INVOICE for f in flags)


def test_fraud_signal(fresh_db):
    invoice = _invoice(fraud_signals=["urgency language: URGENT"])
    flags = compute_flags(invoice, db_path=fresh_db)
    assert any(f["type"] == FRAUD_SIGNAL for f in flags)


def test_multiple_flags(fresh_db):
    """INV-1009: negative qty + empty vendor + negative total -> at least 2 flags."""
    invoice = _invoice(
        vendor="",
        total=-250.0,
        items=[
            {"name": "WidgetA", "qty": -5, "unit_price": 250.0},
            {"name": "WidgetB", "qty": 2, "unit_price": 500.0},
        ],
    )
    flags = compute_flags(invoice, db_path=fresh_db)
    assert len(flags) >= 2


def test_invoice_1013_stock_and_total_mismatch(fresh_db):
    """INV-1013: aggregated quantities over stock on all 3 items, plus a $50 tax->total gap."""
    invoice = _invoice(
        invoice_id="INV-1013",
        vendor="Atlas Industrial Supply",
        items=[
            {"name": "WidgetA", "qty": 15, "unit_price": 250.0},
            {"name": "WidgetB", "qty": 10, "unit_price": 500.0},
            {"name": "GadgetX", "qty": 5, "unit_price": 750.0},
            {"name": "WidgetA", "qty": 5, "unit_price": 240.0},
            {"name": "WidgetB", "qty": 8, "unit_price": 480.0},
            {"name": "GadgetX", "qty": 3, "unit_price": 750.0},
            {"name": "WidgetA", "qty": 2, "unit_price": 250.0},
            {"name": "GadgetX", "qty": 1, "unit_price": 750.0},
        ],
        subtotal=21040.0,
        tax_amount=1472.80,
        total=22562.80,
    )
    flags = compute_flags(invoice, db_path=fresh_db)
    types = {f["type"] for f in flags}
    assert STOCK_MISMATCH in types
    assert TOTAL_MISMATCH in types


def test_invoice_1010_aggregation_passes(fresh_db):
    """INV-1010: WidgetA appears twice (8 + 4 = 12), still within stock of 15."""
    invoice = _invoice(
        invoice_id="INV-1010",
        vendor="Consolidated Materials Group",
        items=[
            {"name": "WidgetA", "qty": 8, "unit_price": 250.0},
            {"name": "WidgetB", "qty": 4, "unit_price": 500.0},
            {"name": "GadgetX", "qty": 2, "unit_price": 750.0},
            {"name": "WidgetA", "qty": 4, "unit_price": 300.0},
        ],
        subtotal=6700.0,
        tax_amount=335.0,
        shipping=150.0,
        total=7185.0,
    )
    assert compute_flags(invoice, db_path=fresh_db) == []
