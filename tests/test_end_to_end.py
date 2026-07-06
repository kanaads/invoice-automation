import pytest

from src.invoice_agents.graph import build_graph

# (filename, expected_status, expected_flag_substring_or_None)
E2E_CASES = [
    ("invoice_1001.txt", "PAID", None),
    ("invoice_1002.txt", "REJECTED", "STOCK_MISMATCH"),
    ("invoice_1003.txt", "REJECTED", "ZERO_STOCK"),
    ("invoice_1004.json", "PAID", None),
    ("invoice_1005.json", "REJECTED", "STOCK_MISMATCH"),
    ("invoice_1006.csv", "PAID", None),
    ("invoice_1007.csv", "REJECTED", "STOCK_MISMATCH"),
    ("invoice_1008.txt", "REJECTED", "UNKNOWN_ITEM"),
    ("invoice_1009.json", "REJECTED", None),  # NEGATIVE_QTY or DATA_INTEGRITY_ERROR
    ("invoice_1010.txt", "PAID", None),  # aggregation: 8+4=12 <= 15
    ("invoice_1011.pdf", "PAID", None),
    ("invoice_1012.txt", "PAID", None),  # OCR normalised
    ("invoice_1013.json", "REJECTED", "STOCK_MISMATCH"),
    ("invoice_1014.xml", "PAID", None),  # foreign currency -- warning only, not blocking
    ("invoice_1015.csv", "PAID", None),
    ("invoice_1016.json", "REJECTED", "UNKNOWN_ITEM"),
]


@pytest.mark.parametrize("filename,expected_status,expected_flag", E2E_CASES)
def test_invoice_end_to_end(filename, expected_status, expected_flag, fresh_db):
    graph = build_graph(db_path=fresh_db)
    state = graph.invoke(
        {
            "invoice_path": f"data/invoices/{filename}",
            "validation_flags": [],
            "reflection_count": 0,
            "steps_taken": [],
        }
    )

    if expected_status == "PAID":
        assert state["approval_decision"] == "APPROVE", state.get("approval_reasoning")
        assert state["payment_result"]["status"] == "success"
    else:
        assert state["approval_decision"] == "REJECT"
        if expected_flag:
            flags_str = str(state["validation_flags"])
            assert expected_flag in flags_str


def test_extraction_failure_routes_to_structured_rejection(fresh_db, monkeypatch):
    """Exhausting MAX_EXTRACTION_ATTEMPTS must not crash the pipeline -- it must flow
    through the same rejection handler blocked invoices use, with reason EXTRACTION_FAILED."""
    from src.invoice_agents.agents.ingestion import extractor

    def always_fails(raw_text, llm):
        raise RuntimeError("simulated permanent failure")

    monkeypatch.setattr(extractor, "extract_invoice", always_fails)

    graph = build_graph(db_path=fresh_db)
    state = graph.invoke(
        {
            "invoice_path": "data/invoices/invoice_1001.txt",
            "validation_flags": [],
            "reflection_count": 0,
            "steps_taken": [],
        }
    )

    assert state["extracted_invoice"] is None
    assert state["approval_decision"] == "REJECT"
    assert "EXTRACTION_FAILED" in str(state["validation_flags"])
    assert state["rejection_log"] is not None
    assert "EXTRACTION_FAILED" in str(state["rejection_log"]["flags"])
    assert state.get("payment_result") is None


def test_duplicate_invoice_is_stateful(fresh_db):
    """INV-1004 must be paid first; only then does INV-1004_revised get flagged as a duplicate."""
    graph = build_graph(db_path=fresh_db)

    first = graph.invoke(
        {
            "invoice_path": "data/invoices/invoice_1004.json",
            "validation_flags": [],
            "reflection_count": 0,
            "steps_taken": [],
        }
    )
    assert first["approval_decision"] == "APPROVE"

    second = graph.invoke(
        {
            "invoice_path": "data/invoices/invoice_1004_revised.json",
            "validation_flags": [],
            "reflection_count": 0,
            "steps_taken": [],
        }
    )
    assert second["approval_decision"] == "REJECT"
    assert "DUPLICATE_INVOICE" in str(second["validation_flags"])
