"""Critic: reviews the Generator's draft decision and either accepts or requests revision."""
from langchain_core.prompts import ChatPromptTemplate

from src.invoice_agents.state import CritiqueResult

SYSTEM_PROMPT = """You are a skeptical auditor reviewing a draft approval decision \
for a high-value invoice. Check that the reasoning is sound, specific to this \
invoice (not generic), and actually justifies the decision. Return ACCEPT if the \
reasoning holds up, or REVISE with concrete feedback on what's missing or weak. \
Don't demand revision just to be difficult -- accept solid reasoning.
"""

_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "Invoice: {invoice}\n\nDraft decision: {draft_decision}\n\nReview it."),
    ]
)


def critique_decision(invoice: dict, draft_decision: dict, llm) -> CritiqueResult:
    structured_llm = llm.with_structured_output(CritiqueResult)
    chain = _prompt | structured_llm
    return chain.invoke({"invoice": invoice, "draft_decision": draft_decision})
