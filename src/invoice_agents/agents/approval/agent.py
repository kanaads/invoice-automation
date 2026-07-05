"""Approval sub-graph: 3-way router (blocking-reject / reflection / rule-approve)."""
from langgraph.graph import END, START, StateGraph

from src.invoice_agents.agents.approval import critic, generator
from src.invoice_agents.agents.approval.rules import (
    APPROVAL_THRESHOLD,
    MAX_REFLECTION_ITERATIONS,
    has_blocking_flags,
    requires_reflection,
)
from src.invoice_agents.state import InvoiceState


def _entry_router(state: InvoiceState) -> str:
    flags = state["validation_flags"]
    amount = state["extracted_invoice"]["total"]
    if has_blocking_flags(flags):
        return "reject_blocking"
    if requires_reflection(amount, flags):
        return "generate"
    return "approve_rule"


def _reject_blocking_node(state: InvoiceState) -> dict:
    flag_types = [f["type"] for f in state["validation_flags"]]
    return {
        "approval_decision": "REJECT",
        "approval_reasoning": f"Blocked by validation flags: {flag_types}",
        "steps_taken": ["reject_blocking"],
    }


def _approve_rule_node(state: InvoiceState) -> dict:
    amount = state["extracted_invoice"]["total"]
    return {
        "approval_decision": "APPROVE",
        "approval_reasoning": f"Clean invoice, amount {amount} at or below the {APPROVAL_THRESHOLD} threshold",
        "steps_taken": ["approve_rule"],
    }


def _generate_node(state: InvoiceState, llm) -> dict:
    decision = generator.generate_decision(
        invoice=state["extracted_invoice"],
        previous_draft=state.get("_draft_decision"),
        critique=state.get("_last_critique"),
        llm=llm,
    )
    return {"_draft_decision": decision.model_dump(), "steps_taken": ["generate"]}


def _critique_node(state: InvoiceState, llm) -> dict:
    result = critic.critique_decision(
        invoice=state["extracted_invoice"], draft_decision=state["_draft_decision"], llm=llm
    )
    return {
        "_critique_verdict": result.verdict,
        "_last_critique": result.feedback,
        "reflection_count": state.get("reflection_count", 0) + 1,
        "steps_taken": ["critique"],
    }


def _critique_router(state: InvoiceState) -> str:
    if state["_critique_verdict"] == "ACCEPT" or state["reflection_count"] >= MAX_REFLECTION_ITERATIONS:
        return "finalize"
    return "generate"


def _finalize_node(state: InvoiceState) -> dict:
    draft = state["_draft_decision"]
    return {
        "approval_decision": draft["decision"],
        "approval_reasoning": (
            f"{draft['reasoning']} (after {state['reflection_count']} reflection iteration(s))"
        ),
        "steps_taken": ["finalize"],
    }


def build_approval_graph(llm):
    graph = StateGraph(InvoiceState)
    graph.add_node("reject_blocking", _reject_blocking_node)
    graph.add_node("approve_rule", _approve_rule_node)
    graph.add_node("generate", lambda state: _generate_node(state, llm))
    graph.add_node("critique", lambda state: _critique_node(state, llm))
    graph.add_node("finalize", _finalize_node)

    graph.add_conditional_edges(
        START,
        _entry_router,
        {"reject_blocking": "reject_blocking", "approve_rule": "approve_rule", "generate": "generate"},
    )
    graph.add_edge("generate", "critique")
    graph.add_conditional_edges("critique", _critique_router, {"generate": "generate", "finalize": "finalize"})
    graph.add_edge("reject_blocking", END)
    graph.add_edge("approve_rule", END)
    graph.add_edge("finalize", END)

    return graph.compile()
