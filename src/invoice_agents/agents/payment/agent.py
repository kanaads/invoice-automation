"""Payment sub-graph: pay + deduct stock + record, or log the rejection."""
from datetime import datetime, timezone

from langgraph.graph import END, START, StateGraph

from src.invoice_agents.agents.payment.mock_api import mock_payment
from src.invoice_agents.agents.validation.db import (
    DEFAULT_DB_PATH,
    deduct_stock,
    record_payment,
    record_rejection,
)
from src.invoice_agents.agents.validation.flags import aggregate_quantities
from src.invoice_agents.state import InvoiceState
from src.invoice_agents.utils.logging import get_logger

logger = get_logger()


def _entry_router(state: InvoiceState) -> str:
    return "pay" if state["approval_decision"] == "APPROVE" else "reject"


def _pay_node(state: InvoiceState, db_path: str) -> dict:
    invoice = state["extracted_invoice"]
    result = mock_payment(invoice["vendor"], invoice["total"])

    aggregated = aggregate_quantities(invoice.get("items", []))
    for name, qty in aggregated.items():
        if qty > 0:
            deduct_stock(name, qty, db_path=db_path)

    record_payment(invoice["invoice_id"], invoice["vendor"], invoice["total"], result["paid_at"], db_path=db_path)
    logger.info("pay: $%s to %s (%s)", invoice["total"], invoice["vendor"], invoice["invoice_id"])
    return {"payment_result": result, "steps_taken": ["pay"]}


def _reject_node(state: InvoiceState, db_path: str) -> dict:
    invoice = state["extracted_invoice"] or {}
    log = {
        "invoice_id": invoice.get("invoice_id"),
        "vendor": invoice.get("vendor"),
        "flags": state["validation_flags"],
        "reasoning": state.get("approval_reasoning"),
    }
    record_rejection(
        log["invoice_id"],
        log["vendor"],
        log["reasoning"] or "",
        log["flags"],
        datetime.now(timezone.utc).isoformat(),
        db_path=db_path,
    )
    logger.info("reject: %s (%s)", log["invoice_id"], log["reasoning"])
    return {"rejection_log": log, "steps_taken": ["reject"]}


def build_payment_graph(db_path: str = DEFAULT_DB_PATH):
    graph = StateGraph(InvoiceState)
    graph.add_node("pay", lambda state: _pay_node(state, db_path))
    graph.add_node("reject", lambda state: _reject_node(state, db_path))
    graph.add_conditional_edges(START, _entry_router, {"pay": "pay", "reject": "reject"})
    graph.add_edge("pay", END)
    graph.add_edge("reject", END)
    return graph.compile()
