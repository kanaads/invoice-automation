from src.invoice_agents.agents.payment.agent import build_payment_graph
from src.invoice_agents.agents.validation.db import check_duplicate, get_stock


def _state(**overrides):
    state = {
        "approval_decision": "APPROVE",
        "extracted_invoice": {
            "invoice_id": "INV-TEST",
            "vendor": "Test Co",
            "total": 2500.0,
            "items": [{"name": "WidgetA", "qty": 10, "unit_price": 250.0}],
        },
        "validation_flags": [],
        "approval_reasoning": "clean invoice",
        "steps_taken": [],
    }
    state.update(overrides)
    return state


def test_payment_approved(fresh_db):
    graph = build_payment_graph(db_path=fresh_db)
    state = graph.invoke(_state())
    assert state["payment_result"]["status"] == "success"
    assert state["payment_result"]["transaction_id"]


def test_payment_deducts_stock(fresh_db):
    graph = build_payment_graph(db_path=fresh_db)
    graph.invoke(_state())
    assert get_stock("WidgetA", db_path=fresh_db) == 5


def test_payment_aggregates_before_deducting(fresh_db):
    """Same item across multiple lines must deduct the aggregated total once."""
    graph = build_payment_graph(db_path=fresh_db)
    graph.invoke(
        _state(
            extracted_invoice={
                "invoice_id": "INV-TEST",
                "vendor": "Test Co",
                "total": 3000.0,
                "items": [
                    {"name": "WidgetA", "qty": 8, "unit_price": 250.0},
                    {"name": "WidgetA", "qty": 4, "unit_price": 250.0},
                ],
            }
        )
    )
    assert get_stock("WidgetA", db_path=fresh_db) == 3


def test_payment_records_invoice(fresh_db):
    graph = build_payment_graph(db_path=fresh_db)
    graph.invoke(_state())
    assert check_duplicate("INV-TEST", db_path=fresh_db) is True


def test_rejection_logged(fresh_db):
    graph = build_payment_graph(db_path=fresh_db)
    state = graph.invoke(
        _state(approval_decision="REJECT", validation_flags=[{"type": "STOCK_MISMATCH", "blocking": True}])
    )
    assert state["rejection_log"]["invoice_id"] == "INV-TEST"
    assert state["rejection_log"]["flags"]


def test_rejection_no_stock_change(fresh_db):
    graph = build_payment_graph(db_path=fresh_db)
    graph.invoke(_state(approval_decision="REJECT"))
    assert get_stock("WidgetA", db_path=fresh_db) == 15
