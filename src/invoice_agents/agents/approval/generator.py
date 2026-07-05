"""Generator: drafts an approval decision for high-value, clean invoices."""
from langchain_core.prompts import ChatPromptTemplate

from src.invoice_agents.state import ApprovalDecision

SYSTEM_PROMPT = """You are simulating VP-level review of a high-value invoice (over \
$10,000) that has already passed automated validation (no stock/data/duplicate \
issues found). Decide whether to APPROVE or REJECT, and explain your reasoning \
as you would to an auditor. Consider vendor legitimacy, amount reasonableness, \
and anything unusual, but default toward APPROVE when nothing is actually wrong -- \
validation already cleared this invoice, so only reject for a genuinely strong reason.

If you are revising a previous draft based on critic feedback, address that \
feedback directly in your new reasoning.
"""

_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        (
            "human",
            "Invoice: {invoice}\n\n"
            "Previous draft (if any): {previous_draft}\n"
            "Critic feedback (if any): {critique}\n\n"
            "Produce your decision.",
        ),
    ]
)


def generate_decision(invoice: dict, previous_draft: dict | None, critique: str | None, llm) -> ApprovalDecision:
    structured_llm = llm.with_structured_output(ApprovalDecision)
    chain = _prompt | structured_llm
    return chain.invoke(
        {
            "invoice": invoice,
            "previous_draft": previous_draft or "none",
            "critique": critique or "none",
        }
    )
