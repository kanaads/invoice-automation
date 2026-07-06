"""Mock payment API -- simulates a banking call."""
import uuid
from datetime import datetime, timezone


def mock_payment(vendor: str, amount: float) -> dict:
    print(f"Paid {amount} to {vendor}")
    return {
        "status": "success",
        "transaction_id": str(uuid.uuid4()),
        "paid_at": datetime.now(timezone.utc).isoformat(),
    }
