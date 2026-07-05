from src.invoice_agents.agents.ingestion.parsers import _parse_csv, load_invoice


def test_parse_txt(invoice_dir):
    result = load_invoice(f"{invoice_dir}/invoice_1001.txt")
    assert isinstance(result, str) and len(result) > 0


def test_parse_json(invoice_dir):
    result = load_invoice(f"{invoice_dir}/invoice_1004.json")
    assert isinstance(result, str) and len(result) > 0


def test_parse_csv_keyvalue(invoice_dir):
    result = _parse_csv(f"{invoice_dir}/invoice_1006.csv")
    assert "WidgetA" in result
    assert ":" in result


def test_parse_csv_tabular(invoice_dir):
    result = _parse_csv(f"{invoice_dir}/invoice_1007.csv")
    assert "WidgetA" in result
    assert "," in result


def test_parse_xml(invoice_dir):
    result = load_invoice(f"{invoice_dir}/invoice_1014.xml")
    assert isinstance(result, str) and len(result) > 0


def test_parse_pdf_markitdown(invoice_dir):
    result = load_invoice(f"{invoice_dir}/invoice_1011.pdf")
    assert isinstance(result, str) and len(result) > 0


def test_load_invoice_router(invoice_dir):
    for fname in (
        "invoice_1001.txt",
        "invoice_1004.json",
        "invoice_1006.csv",
        "invoice_1007.csv",
        "invoice_1014.xml",
        "invoice_1011.pdf",
    ):
        result = load_invoice(f"{invoice_dir}/{fname}")
        assert isinstance(result, str) and len(result) > 0


def test_all_official_invoices_parse(invoice_dir):
    import os

    for fname in sorted(os.listdir(invoice_dir)):
        result = load_invoice(f"{invoice_dir}/{fname}")
        assert isinstance(result, str) and len(result) > 0, f"{fname} produced empty text"
