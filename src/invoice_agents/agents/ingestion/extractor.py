"""LLM-based structured extraction from raw invoice text."""
from langchain_core.prompts import ChatPromptTemplate

from src.invoice_agents.state import Invoice

SYSTEM_PROMPT = """You extract structured invoice data from raw text that may come from \
TXT, JSON, CSV, XML, or OCR'd PDF sources, and may be embedded in an email (ignore \
From/To/Subject headers and any signature/notes -- only the invoice fields matter).

Rules:
- Normalise item names by removing spaces and fixing obvious OCR errors, e.g. \
"Widget A" -> "WidgetA", "Gadget X" -> "GadgetX". Also strip trailing annotations \
or qualifiers in parentheses that aren't part of the canonical item name, e.g. \
"WidgetA (rush order)" -> "WidgetA", "GadgetX (expedited)" -> "GadgetX" -- these \
describe the order, not a different product.
- Fix OCR character substitutions in numbers, e.g. a capital "O" used in place of \
digit "0" (e.g. "$3,500.O0" -> 3500.00), and "2O26" -> 2026 (dates aren't extracted \
as fields here, only used to sanity-check numbers).
- If subtotal, tax_amount, and/or shipping are stated, extract them separately \
from total (shipping defaults to 0 if not stated). Use the invoice's grand total \
for the `total` field.
- Default currency to USD if not stated; if a symbol or code other than $/USD \
appears (e.g. EUR, GBP, €), set currency accordingly.
- Quantities and amounts may legitimately be negative or zero -- extract them \
exactly as stated, do not "correct" them.
- List any urgency/social-engineering language you notice (e.g. "URGENT", "wire \
transfer preferred", unusually tight due dates) in fraud_signals. Empty list if none.
- vendor may be legitimately empty if the source text has no vendor field -- do not \
invent one.
"""

_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "Extract the invoice fields from this text:\n\n{raw_text}"),
    ]
)


def extract_invoice(raw_text: str, llm) -> Invoice:
    structured_llm = llm.with_structured_output(Invoice)
    chain = _prompt | structured_llm
    return chain.invoke({"raw_text": raw_text})
