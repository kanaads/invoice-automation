from src.invoice_agents.agents.ingestion.agent import build_ingestion_graph
from src.invoice_agents.llm import get_llm


def _run(invoice_path: str) -> dict:
    graph = build_ingestion_graph(get_llm())
    return graph.invoke(
        {"invoice_path": invoice_path, "validation_flags": [], "steps_taken": []}
    )


def test_ingest_clean_txt():
    state = _run("data/invoices/invoice_1001.txt")
    inv = state["extracted_invoice"]
    assert inv["vendor"]
    assert inv["total"] > 0
    assert len(inv["items"]) > 0
    assert state["ingestion_error"] is None


def test_ingest_json():
    state = _run("data/invoices/invoice_1004.json")
    inv = state["extracted_invoice"]
    assert inv["invoice_id"] == "INV-1004"
    assert len(inv["items"]) == 2


def test_ingest_csv():
    state = _run("data/invoices/invoice_1006.csv")
    inv = state["extracted_invoice"]
    names = [item["name"] for item in inv["items"]]
    assert any("Widget" in n for n in names)


def test_ingest_xml():
    state = _run("data/invoices/invoice_1014.xml")
    inv = state["extracted_invoice"]
    assert inv["currency"] == "EUR"


def test_ingest_pdf():
    state = _run("data/invoices/invoice_1011.pdf")
    inv = state["extracted_invoice"]
    assert inv["vendor"]
    assert len(inv["items"]) > 0


def test_ingest_ocr_normalised():
    """OCR-mangled names ('Widget A', 'Gadget X') must be normalised to match the DB."""
    state = _run("data/invoices/invoice_1012.txt")
    inv = state["extracted_invoice"]
    names = [item["name"] for item in inv["items"]]
    assert all(" " not in n for n in names)
    assert any(n in ("WidgetA", "WidgetB", "GadgetX") for n in names)


def test_ingest_email_format():
    """Invoice embedded in an email; vendor/items must extract despite headers."""
    state = _run("data/invoices/invoice_1008.txt")
    inv = state["extracted_invoice"]
    assert inv["vendor"]
    names = [item["name"] for item in inv["items"]]
    assert any(n in ("SuperGizmo", "MegaSprocket") for n in names)


def test_ingest_retry_on_failure(monkeypatch):
    """A transient extraction failure must be retried, not fatal."""
    from src.invoice_agents.agents.ingestion import extractor

    calls = {"n": 0}
    real_extract = extractor.extract_invoice

    def flaky_extract(raw_text, llm):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("simulated transient failure")
        return real_extract(raw_text, llm)

    monkeypatch.setattr(extractor, "extract_invoice", flaky_extract)
    state = _run("data/invoices/invoice_1001.txt")
    assert calls["n"] >= 2
    assert state["extracted_invoice"] is not None
