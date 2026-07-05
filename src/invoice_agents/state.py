import operator
from typing import Annotated, Optional
from typing_extensions import TypedDict

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    name: str = Field(description="Normalised item name, no spaces, e.g. WidgetA")
    qty: int = Field(description="Quantity ordered; negative values indicate a data integrity issue")
    unit_price: Optional[float] = Field(default=None, description="Price per unit as stated on the invoice")


class Invoice(BaseModel):
    invoice_id: str = Field(description="Invoice number, e.g. INV-1004")
    vendor: str = Field(description="Vendor name; empty string indicates a data integrity issue")
    items: list[LineItem] = Field(description="Line items, normalised names, OCR-corrected")
    subtotal: Optional[float] = Field(default=None, description="Sum of line items before tax")
    tax_amount: Optional[float] = Field(default=None, description="Tax charged on the invoice")
    shipping: float = Field(default=0.0, description="Shipping/handling charge, if stated separately")
    total: float = Field(description="Total amount due, used for the $10K approval threshold")
    currency: str = Field(default="USD", description="ISO currency code, e.g. USD, EUR")
    due_date: Optional[str] = Field(default=None, description="Due date as stated on the invoice")
    fraud_signals: list[str] = Field(
        default_factory=list, description="Suspicious phrases noticed during extraction, e.g. urgency language"
    )


class ApprovalDecision(BaseModel):
    decision: str = Field(description='Exactly "APPROVE" or "REJECT"')
    reasoning: str = Field(description="Explanation for the decision, for the audit log")


class CritiqueResult(BaseModel):
    verdict: str = Field(description='Exactly "ACCEPT" or "REVISE"')
    feedback: str = Field(description="Critique of the draft decision; empty if ACCEPT")


class InvoiceState(TypedDict):
    # CLI sets
    invoice_path: str
    run_id: Optional[str]

    # Ingestion writes
    raw_text: Optional[str]
    extracted_invoice: Optional[dict]
    ingestion_error: Optional[str]

    # Validation writes (operator.add -- APPENDS)
    validation_flags: Annotated[list[dict], operator.add]

    # Approval writes
    approval_decision: Optional[str]
    approval_reasoning: Optional[str]
    reflection_count: int
    _draft_decision: Optional[dict]
    _critique_verdict: Optional[str]
    _last_critique: Optional[str]

    # Payment writes
    payment_result: Optional[dict]
    rejection_log: Optional[dict]

    # Audit (operator.add -- APPENDS)
    steps_taken: Annotated[list[str], operator.add]
