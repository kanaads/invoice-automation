"""Ingestion sub-graph: format router -> LLM extraction with retry."""
from langgraph.graph import END, StateGraph

from src.invoice_agents.agents.ingestion import extractor
from src.invoice_agents.agents.ingestion.parsers import load_invoice
from src.invoice_agents.state import InvoiceState
from src.invoice_agents.utils.logging import get_logger

MAX_EXTRACTION_ATTEMPTS = 3

logger = get_logger()


def _parse_node(state: InvoiceState) -> dict:
    raw_text = load_invoice(state["invoice_path"])
    logger.info("parse: loaded %d chars from %s", len(raw_text), state["invoice_path"])
    return {"raw_text": raw_text, "steps_taken": ["parse"]}


def _extract_node(state: InvoiceState, llm) -> dict:
    last_error = None
    for attempt in range(1, MAX_EXTRACTION_ATTEMPTS + 1):
        try:
            invoice = extractor.extract_invoice(state["raw_text"], llm)
            logger.info("extract: succeeded on attempt %d/%d", attempt, MAX_EXTRACTION_ATTEMPTS)
            return {
                "extracted_invoice": invoice.model_dump(),
                "ingestion_error": None,
                "steps_taken": ["extract"],
            }
        except Exception as exc:  # noqa: BLE001 -- retry any extraction failure
            last_error = str(exc)
            logger.warning("extract: attempt %d/%d failed: %s", attempt, MAX_EXTRACTION_ATTEMPTS, last_error)
    logger.error("extract: gave up after %d attempts: %s", MAX_EXTRACTION_ATTEMPTS, last_error)
    return {
        "extracted_invoice": None,
        "ingestion_error": last_error,
        "steps_taken": ["extract_failed"],
    }


def build_ingestion_graph(llm):
    graph = StateGraph(InvoiceState)
    graph.add_node("parse", _parse_node)
    graph.add_node("extract", lambda state: _extract_node(state, llm))
    graph.add_edge("parse", "extract")
    graph.add_edge("extract", END)
    graph.set_entry_point("parse")
    return graph.compile()
