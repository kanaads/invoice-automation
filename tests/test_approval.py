from src.invoice_agents.agents.approval.agent import build_approval_graph
from src.invoice_agents.llm import get_llm


def _base_state(**overrides):
    state = {
        "extracted_invoice": {
            "invoice_id": "INV-TEST",
            "vendor": "Test Co",
            "total": 3000.0,
            "items": [{"name": "WidgetA", "qty": 5, "unit_price": 250.0}],
        },
        "validation_flags": [],
        "reflection_count": 0,
        "steps_taken": [],
    }
    state.update(overrides)
    return state


def test_branch_a_blocking():
    graph = build_approval_graph(llm=None)  # Branch A makes zero LLM calls
    state = graph.invoke(
        _base_state(validation_flags=[{"type": "STOCK_MISMATCH"}], extracted_invoice={"total": 3000.0})
    )
    assert state["approval_decision"] == "REJECT"
    assert state["reflection_count"] == 0


def test_branch_c_clean_low():
    graph = build_approval_graph(llm=None)  # Branch C makes zero LLM calls
    state = graph.invoke(_base_state())
    assert state["approval_decision"] == "APPROVE"
    assert state["reflection_count"] == 0


def test_branch_b_high_value():
    graph = build_approval_graph(llm=get_llm())
    state = graph.invoke(
        _base_state(extracted_invoice={"invoice_id": "INV-TEST", "vendor": "Test Co", "total": 15000.0, "items": []})
    )
    assert state["approval_decision"] in ("APPROVE", "REJECT")
    assert state["reflection_count"] >= 1


def test_branch_b_loop_caps(monkeypatch):
    """Reflection loop must never exceed MAX_REFLECTION_ITERATIONS even if the critic always says REVISE."""
    from src.invoice_agents.agents.approval import critic
    from src.invoice_agents.state import CritiqueResult

    monkeypatch.setattr(
        critic,
        "critique_decision",
        lambda invoice, draft_decision, llm: CritiqueResult(verdict="REVISE", feedback="always revise"),
    )
    graph = build_approval_graph(llm=get_llm())
    state = graph.invoke(
        _base_state(extracted_invoice={"invoice_id": "INV-TEST", "vendor": "Test Co", "total": 15000.0, "items": []})
    )
    assert state["reflection_count"] <= 3
    assert state["approval_decision"] in ("APPROVE", "REJECT")


def test_reflection_accept_exits_immediately(monkeypatch):
    from src.invoice_agents.agents.approval import critic
    from src.invoice_agents.state import CritiqueResult

    monkeypatch.setattr(
        critic,
        "critique_decision",
        lambda invoice, draft_decision, llm: CritiqueResult(verdict="ACCEPT", feedback=""),
    )
    graph = build_approval_graph(llm=get_llm())
    state = graph.invoke(
        _base_state(extracted_invoice={"invoice_id": "INV-TEST", "vendor": "Test Co", "total": 15000.0, "items": []})
    )
    assert state["reflection_count"] == 1


def test_reflection_produces_reasoning():
    graph = build_approval_graph(llm=get_llm())
    state = graph.invoke(
        _base_state(extracted_invoice={"invoice_id": "INV-TEST", "vendor": "Test Co", "total": 15000.0, "items": []})
    )
    assert state["approval_reasoning"]
    assert len(state["approval_reasoning"]) > 20
