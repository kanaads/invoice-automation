"""Parent orchestrator: wires the 4 sub-graphs into a single StateGraph."""
from langgraph.graph import END, StateGraph

from src.invoice_agents.agents.approval.agent import build_approval_graph
from src.invoice_agents.agents.ingestion.agent import build_ingestion_graph
from src.invoice_agents.agents.payment.agent import build_payment_graph
from src.invoice_agents.agents.validation.agent import build_validation_graph
from src.invoice_agents.agents.validation.db import DEFAULT_DB_PATH
from src.invoice_agents.llm import get_llm
from src.invoice_agents.state import InvoiceState


def build_graph(db_path: str = DEFAULT_DB_PATH, llm=None):
    llm = llm or get_llm()

    graph = StateGraph(InvoiceState)
    graph.add_node("ingestion", build_ingestion_graph(llm))
    graph.add_node("validation", build_validation_graph(db_path))
    graph.add_node("approval", build_approval_graph(llm))
    graph.add_node("payment", build_payment_graph(db_path))

    graph.set_entry_point("ingestion")
    graph.add_edge("ingestion", "validation")
    graph.add_edge("validation", "approval")
    graph.add_edge("approval", "payment")
    graph.add_edge("payment", END)

    return graph.compile()
