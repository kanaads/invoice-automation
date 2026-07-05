"""Validation sub-graph: deterministic flag computation against the inventory DB."""
from langgraph.graph import END, StateGraph

from src.invoice_agents.agents.validation.db import DEFAULT_DB_PATH
from src.invoice_agents.agents.validation.flags import compute_flags
from src.invoice_agents.state import InvoiceState


def _validate_node(state: InvoiceState, db_path: str) -> dict:
    flags = compute_flags(state["extracted_invoice"], db_path=db_path)
    return {"validation_flags": flags, "steps_taken": ["validate"]}


def build_validation_graph(db_path: str = DEFAULT_DB_PATH):
    graph = StateGraph(InvoiceState)
    graph.add_node("validate", lambda state: _validate_node(state, db_path))
    graph.add_edge("validate", END)
    graph.set_entry_point("validate")
    return graph.compile()
