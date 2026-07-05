"""Parent orchestrator: wires the 4 sub-graphs into a single StateGraph."""
from langgraph.graph import END, StateGraph

from src.invoice_agents.agents.approval.agent import build_approval_graph
from src.invoice_agents.agents.ingestion.agent import build_ingestion_graph
from src.invoice_agents.agents.payment.agent import build_payment_graph
from src.invoice_agents.agents.validation.agent import build_validation_graph
from src.invoice_agents.agents.validation.db import DEFAULT_DB_PATH
from src.invoice_agents.llm import get_llm
from src.invoice_agents.state import InvoiceState

# Fields that use an operator.add reducer. A sub-graph's .invoke() already merges
# its own additions into the full state it was given, so only the *new* slice must
# be returned to the parent -- otherwise the parent's reducer double-counts
# everything the child already had on input.
_REDUCER_FIELDS = ("steps_taken", "validation_flags")


def _run_subgraph(compiled_graph, state: InvoiceState) -> dict:
    result = dict(compiled_graph.invoke(state))
    for field in _REDUCER_FIELDS:
        prior_len = len(state.get(field) or [])
        result[field] = result[field][prior_len:]
    return result


def build_graph(db_path: str = DEFAULT_DB_PATH, llm=None):
    llm = llm or get_llm()

    ingestion_graph = build_ingestion_graph(llm)
    validation_graph = build_validation_graph(db_path)
    approval_graph = build_approval_graph(llm)
    payment_graph = build_payment_graph(db_path)

    graph = StateGraph(InvoiceState)
    graph.add_node("ingestion", lambda state: _run_subgraph(ingestion_graph, state))
    graph.add_node("validation", lambda state: _run_subgraph(validation_graph, state))
    graph.add_node("approval", lambda state: _run_subgraph(approval_graph, state))
    graph.add_node("payment", lambda state: _run_subgraph(payment_graph, state))

    graph.set_entry_point("ingestion")
    graph.add_edge("ingestion", "validation")
    graph.add_edge("validation", "approval")
    graph.add_edge("approval", "payment")
    graph.add_edge("payment", END)

    return graph.compile()
