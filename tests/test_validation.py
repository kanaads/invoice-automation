import pytest

from src.invoice_agents.agents.validation.agent import build_validation_graph

INVOICE_FIXTURES = {
    "clean_1001": {
        "invoice_id": "INV-1001",
        "vendor": "Acme Vendor",
        "items": [{"name": "WidgetA", "qty": 10, "unit_price": 250.0}, {"name": "WidgetB", "qty": 5, "unit_price": 500.0}],
        "subtotal": 5000.0,
        "tax_amount": 0.0,
        "shipping": 0.0,
        "total": 5000.0,
        "currency": "USD",
        "fraud_signals": [],
    },
    "stock_mismatch_1002": {
        "invoice_id": "INV-1002",
        "vendor": "Some Vendor",
        "items": [{"name": "GadgetX", "qty": 20, "unit_price": 750.0}],
        "subtotal": 15000.0,
        "tax_amount": 0.0,
        "shipping": 0.0,
        "total": 15000.0,
        "currency": "USD",
        "fraud_signals": [],
    },
    "zero_stock_1003": {
        "invoice_id": "INV-1003",
        "vendor": "Suspicious Vendor",
        "items": [{"name": "FakeItem", "qty": 100, "unit_price": 1000.0}],
        "subtotal": 100000.0,
        "tax_amount": 0.0,
        "shipping": 0.0,
        "total": 100000.0,
        "currency": "USD",
        "fraud_signals": ["urgency language: URGENT"],
    },
    "unknown_1008": {
        "invoice_id": "INV-1008",
        "vendor": "NoProd Industries",
        "items": [{"name": "SuperGizmo", "qty": 12, "unit_price": 400.0}, {"name": "MegaSprocket", "qty": 6, "unit_price": 850.0}],
        "subtotal": 9900.0,
        "tax_amount": 0.0,
        "shipping": 0.0,
        "total": 9900.0,
        "currency": "USD",
        "fraud_signals": [],
    },
    "negative_1009": {
        "invoice_id": "INV-1009",
        "vendor": "",
        "items": [{"name": "WidgetA", "qty": -5, "unit_price": 250.0}, {"name": "WidgetB", "qty": 2, "unit_price": 500.0}],
        "subtotal": 1000.0,
        "tax_amount": 0.0,
        "shipping": 0.0,
        "total": -250.0,
        "currency": "USD",
        "fraud_signals": [],
    },
    "total_mismatch_1013": {
        "invoice_id": "INV-1013",
        "vendor": "Atlas Industrial Supply",
        "items": [
            {"name": "WidgetA", "qty": 22, "unit_price": 250.0},
            {"name": "WidgetB", "qty": 18, "unit_price": 500.0},
            {"name": "GadgetX", "qty": 9, "unit_price": 750.0},
        ],
        "subtotal": 21040.0,
        "tax_amount": 1472.80,
        "shipping": 0.0,
        "total": 22562.80,
        "currency": "USD",
        "fraud_signals": [],
    },
    "foreign_currency_1014": {
        "invoice_id": "INV-1014",
        "vendor": "TechParts International",
        "items": [{"name": "WidgetA", "qty": 4, "unit_price": 225.0}, {"name": "WidgetB", "qty": 6, "unit_price": 475.0}],
        "subtotal": 3750.0,
        "tax_amount": 375.0,
        "shipping": 0.0,
        "total": 4125.0,
        "currency": "EUR",
        "fraud_signals": [],
    },
}

VALIDATION_CASES = [
    ("clean_1001", None),
    ("stock_mismatch_1002", "STOCK_MISMATCH"),
    ("zero_stock_1003", "ZERO_STOCK_SUSPICIOUS"),
    ("unknown_1008", "UNKNOWN_ITEM"),
    ("negative_1009", "NEGATIVE_QTY"),
    ("total_mismatch_1013", "TOTAL_MISMATCH"),
    ("foreign_currency_1014", "FOREIGN_CURRENCY"),
]


@pytest.mark.parametrize("case,expected_flag", VALIDATION_CASES)
def test_validation_scenarios(case, expected_flag, fresh_db):
    graph = build_validation_graph(db_path=fresh_db)
    state = graph.invoke(
        {"extracted_invoice": INVOICE_FIXTURES[case], "validation_flags": [], "steps_taken": []}
    )
    flags = state["validation_flags"]
    if expected_flag is None:
        assert flags == []
    else:
        assert any(f["type"] == expected_flag for f in flags)


def test_validation_writes_steps_taken(fresh_db):
    graph = build_validation_graph(db_path=fresh_db)
    state = graph.invoke(
        {"extracted_invoice": INVOICE_FIXTURES["clean_1001"], "validation_flags": [], "steps_taken": []}
    )
    assert "validate" in state["steps_taken"]
