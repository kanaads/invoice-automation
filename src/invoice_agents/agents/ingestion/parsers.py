"""Format parsers: each returns the invoice content as plain text for LLM extraction."""
import csv
import io
import json
import xml.etree.ElementTree as ET
from pathlib import Path


def _parse_txt(path: str) -> str:
    return Path(path).read_text()


def _parse_json(path: str) -> str:
    data = json.loads(Path(path).read_text())
    return json.dumps(data, indent=2)


def _parse_csv(path: str) -> str:
    raw = Path(path).read_text()
    reader = csv.reader(io.StringIO(raw))
    rows = list(reader)
    if rows and rows[0][:2] == ["field", "value"]:
        # Key-value style: "field,value" header, one field per row.
        return "\n".join(f"{row[0]}: {row[1]}" for row in rows[1:] if row)
    # Tabular style: header row + one row per line item.
    return "\n".join(",".join(row) for row in rows)


def _parse_xml(path: str) -> str:
    tree = ET.parse(path)
    return ET.tostring(tree.getroot(), encoding="unicode")


def _parse_pdf(path: str) -> str:
    try:
        from markitdown import MarkItDown

        text = MarkItDown().convert(path).text_content
        if text and text.strip():
            return text
    except Exception:
        pass

    import pdfplumber

    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


_PARSERS = {
    ".txt": _parse_txt,
    ".json": _parse_json,
    ".csv": _parse_csv,
    ".xml": _parse_xml,
    ".pdf": _parse_pdf,
}


def load_invoice(path: str) -> str:
    ext = Path(path).suffix.lower()
    parser = _PARSERS.get(ext)
    if parser is None:
        raise ValueError(f"Unsupported invoice format: {ext}")
    return parser(path)
