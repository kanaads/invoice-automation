"""Validation sub-graph: deterministic flag computation against the inventory DB."""
from langgraph.graph import END, StateGraph

from src.invoice_agents.agents.validation.db import DEFAULT_DB_PATH
from src.invoice_agents.agents.validation.flags import EXTRACTION_FAILED, _flag, compute_flags
from src.invoice_agents.state import InvoiceState
from src.invoice_agents.utils.logging import get_logger

logger = get_logger()


def _validate_node(state: InvoiceState, db_path: str) -> dict:
    if state.get("ingestion_error"):
        flags = [_flag(EXTRACTION_FAILED, state["ingestion_error"] or "extraction failed")]
        logger.warning("validate: skipped, ingestion_error=%s", state["ingestion_error"])
        return {"validation_flags": flags, "steps_taken": ["validate_skipped_extraction_failed"]}
    flags = compute_flags(state["extracted_invoice"], db_path=db_path)
    blocking = sum(1 for f in flags if f.get("blocking", True))
    logger.info("validate: %d flag(s), %d blocking", len(flags), blocking)
    return {"validation_flags": flags, "steps_taken": ["validate"]}


def build_validation_graph(db_path: str = DEFAULT_DB_PATH):
    graph = StateGraph(InvoiceState)
    graph.add_node("validate", lambda state: _validate_node(state, db_path))
    graph.add_edge("validate", END)
    graph.set_entry_point("validate")
    return graph.compile()
