# TESTPLAN.md — Invoice Processing Automation
## Complete Test Plan

> **How to use this file:** This is the verification harness for the project. It covers unit tests (per agent), integration tests (per sub-graph), and end-to-end tests (per invoice). Run the full suite before declaring any phase done. Every edge case from `PLAN.md` Section 4 has a corresponding test here.

---

## Table of Contents
1. [Test Strategy](#1-test-strategy)
2. [Test Environment Setup](#2-test-environment-setup)
3. [Layer 1 — Unit Tests](#3-layer-1--unit-tests)
4. [Layer 2 — Integration Tests (per agent)](#4-layer-2--integration-tests)
5. [Layer 3 — End-to-End Tests (per invoice)](#5-layer-3--end-to-end-tests)
6. [Edge Case Test Matrix](#6-edge-case-test-matrix)
7. [Reflection Loop Tests](#7-reflection-loop-tests)
8. [Negative & Failure Tests](#8-negative--failure-tests)
9. [Regression Checklist](#9-regression-checklist)
10. [Manual / UI Tests](#10-manual--ui-tests)
11. [Test Execution Commands](#11-test-execution-commands)

---

## 1. Test Strategy

Three layers, run bottom-up:

| Layer | What it tests | Speed | When to run |
|-------|--------------|-------|-------------|
| **Unit** | Single functions (parsers, get_stock, compute_flags, rule_based_approve) | Fast (<1s) | After each function written |
| **Integration** | One sub-graph in isolation (ingestion, validation, approval, payment) | Medium (LLM calls) | After each agent phase |
| **End-to-end** | Full graph, one test per invoice | Slow (full LLM pipeline) | After Phase 6, before done |

**Determinism principle:** Unit and validation tests must be 100% deterministic (no LLM). Only ingestion extraction and approval reflection tests involve the LLM — those assert on structure and outcome, not exact wording.

**Coverage target:** Every one of the 20 official invoices has an end-to-end test. Every one of the 14 complexity traps (PLAN.md Section 4.3) has a dedicated test.

---

## 2. Test Environment Setup

```python
# tests/conftest.py
import pytest
import sqlite3
import os
from pathlib import Path

@pytest.fixture(scope="session")
def test_db(tmp_path_factory):
    """Create a fresh inventory.db with official seed data for tests."""
    db_path = tmp_path_factory.mktemp("data") / "inventory.db"
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("CREATE TABLE inventory (item TEXT PRIMARY KEY, stock INTEGER, unit_price REAL, category TEXT)")
    cur.executemany(
        "INSERT INTO inventory VALUES (?,?,?,?)",
        [
            ("WidgetA", 15, 200.0, "widget"),
            ("WidgetB", 10, 150.0, "widget"),
            ("WidgetC", 0, None, "widget"),       # unknown / zero stock
            ("GadgetX", 5, 800.0, "gadget"),
            ("FakeItem", 0, None, "SENTINEL"),     # fraud marker
            ("SuperGizmo", 0, None, "unknown"),
            ("MegaSprocket", 0, None, "unknown"),
        ]
    )
    cur.execute("CREATE TABLE paid_invoices (invoice_id TEXT, vendor TEXT, amount REAL, paid_at TEXT)")
    conn.commit()
    conn.close()
    return str(db_path)

@pytest.fixture
def fresh_db(test_db, tmp_path):
    """A per-test copy so stock deductions don't leak between tests."""
    import shutil
    copy = tmp_path / "inventory.db"
    shutil.copy(test_db, copy)
    return str(copy)

@pytest.fixture
def invoice_dir():
    return "data/invoices"
```

---

## 3. Layer 1 — Unit Tests

### 3.1 Parser tests (`tests/test_parsers.py`)

| Test | Input | Assert |
|------|-------|--------|
| `test_parse_txt` | invoice_1001.txt | Returns non-empty string |
| `test_parse_json` | invoice_1004.json | Returns valid JSON string |
| `test_parse_csv_keyvalue` | invoice_1006.csv | Detects key-value style, returns "field: value" lines |
| `test_parse_csv_tabular` | invoice_1007.csv | Detects tabular style, returns comma rows |
| `test_parse_xml` | invoice_1014.xml | Returns text content, no crash |
| `test_parse_pdf_markitdown` | invoice_1011.pdf | Returns markdown text |
| `test_parse_pdf_fallback` | corrupt PDF | Falls back to pdfplumber, no crash |
| `test_load_invoice_router` | each extension | Routes to correct parser |

```python
def test_parse_csv_keyvalue(invoice_dir):
    from src.invoice_agents.agents.ingestion.parsers import _parse_csv
    result = _parse_csv(f"{invoice_dir}/invoice_1006.csv")
    assert "WidgetA" in result
    assert ":" in result  # key-value format

def test_load_invoice_router(invoice_dir):
    from src.invoice_agents.agents.ingestion.parsers import load_invoice
    for ext, fname in [("txt","invoice_1001.txt"), ("json","invoice_1004.json"),
                       ("csv","invoice_1006.csv"), ("xml","invoice_1014.xml")]:
        result = load_invoice(f"{invoice_dir}/{fname}")
        assert isinstance(result, str) and len(result) > 0
```

### 3.2 Database tests (`tests/test_db.py`)

| Test | Assert |
|------|--------|
| `test_get_stock_found` | get_stock("WidgetA") == 15 |
| `test_get_stock_zero` | get_stock("FakeItem") == 0 |
| `test_get_stock_unknown` | get_stock("Nonexistent") is None |
| `test_parameterised_no_injection` | get_stock("'; DROP TABLE inventory; --") returns None, table intact |
| `test_deduct_stock` | After deduct_stock("WidgetA", 10): stock == 5 |
| `test_check_duplicate_false` | check_duplicate("INV-9999") is False |
| `test_check_duplicate_true` | After record_payment("INV-1004",...): check_duplicate("INV-1004") is True |

```python
def test_parameterised_no_injection(fresh_db):
    from src.invoice_agents.agents.validation.db import get_stock
    # Malicious item name must NOT execute SQL
    result = get_stock("'; DROP TABLE inventory; --", db_path=fresh_db)
    assert result is None
    # Verify table still exists
    assert get_stock("WidgetA", db_path=fresh_db) == 15

def test_deduct_stock(fresh_db):
    from src.invoice_agents.agents.validation.db import get_stock, deduct_stock
    deduct_stock("WidgetA", 10, db_path=fresh_db)
    assert get_stock("WidgetA", db_path=fresh_db) == 5
```

### 3.3 Flag computation tests (`tests/test_flags.py`) — the most important unit tests

| Test | Invoice scenario | Expected flag |
|------|-----------------|---------------|
| `test_clean_passes` | WidgetA×10 (stock 15) | flags == [] |
| `test_stock_mismatch` | GadgetX×20 (stock 5) | STOCK_MISMATCH |
| `test_zero_stock` | FakeItem×1 (stock 0) | ZERO_STOCK_SUSPICIOUS |
| `test_unknown_item` | SuperGizmo×1 (not in DB) | UNKNOWN_ITEM |
| `test_negative_qty` | WidgetA×(-5) | NEGATIVE_QTY |
| `test_empty_vendor` | vendor="" | DATA_INTEGRITY_ERROR |
| `test_negative_amount` | amount=-250 | DATA_INTEGRITY_ERROR |
| `test_qty_aggregation` | WidgetA×8 + WidgetA×4 (stock 15) | flags == [] (12≤15) |
| `test_qty_aggregation_fail` | WidgetA×10 + WidgetA×8 (stock 15) | STOCK_MISMATCH (18>15) |
| `test_total_mismatch` | line sum $100, stated $150 | TOTAL_MISMATCH |
| `test_foreign_currency` | currency=EUR | FOREIGN_CURRENCY |
| `test_duplicate_invoice` | invoice_id already in paid_invoices | DUPLICATE_INVOICE |
| `test_multiple_flags` | INV-1009 (neg qty + empty vendor) | ≥2 flags |

```python
def test_qty_aggregation(fresh_db):
    """CRITICAL: same item on multiple lines must aggregate."""
    from src.invoice_agents.agents.validation.flags import compute_flags
    invoice = {
        "vendor": "Test Co", "amount": 5000, "currency": "USD",
        "items": [
            {"name": "WidgetA", "qty": 8},
            {"name": "WidgetA", "qty": 4},   # total 12, stock 15 → OK
        ]
    }
    flags = compute_flags(invoice, db_path=fresh_db)
    assert flags == []

def test_qty_aggregation_fail(fresh_db):
    """Aggregated qty exceeds stock even though each line is fine."""
    from src.invoice_agents.agents.validation.flags import compute_flags
    invoice = {
        "vendor": "Test Co", "amount": 5000, "currency": "USD",
        "items": [
            {"name": "WidgetA", "qty": 10},  # alone: OK
            {"name": "WidgetA", "qty": 8},   # alone: OK, but 18 > 15
        ]
    }
    flags = compute_flags(invoice, db_path=fresh_db)
    assert any(f["type"] == "STOCK_MISMATCH" for f in flags)
```

### 3.4 Approval rules tests (`tests/test_rules.py`)

| Test | Input | Assert |
|------|-------|--------|
| `test_rule_approve_clean_low` | $3K, no flags | rule_based_approve True |
| `test_rule_approve_high_amount` | $15K, no flags | rule_based_approve False (needs reflection) |
| `test_rule_approve_with_flags` | $3K, 1 flag | rule_based_approve False |
| `test_requires_reflection` | $15K, no flags | requires_reflection True |
| `test_has_blocking_flags` | 1 flag | has_blocking_flags True |

---

## 4. Layer 2 — Integration Tests

### 4.1 Ingestion sub-graph (`tests/test_ingestion.py`)

| Test | Invoice | Assert |
|------|---------|--------|
| `test_ingest_clean_txt` | invoice_1001.txt | extracted_invoice has vendor, amount, items, due_date |
| `test_ingest_json` | invoice_1004.json | All fields extracted |
| `test_ingest_csv` | invoice_1006.csv | Items extracted correctly |
| `test_ingest_xml` | invoice_1014.xml | currency == "EUR" detected |
| `test_ingest_pdf` | invoice_1011.pdf (or .md) | Fields extracted |
| `test_ingest_ocr_normalised` | invoice_1012 | Item names normalised ("Widget A" → "WidgetA") |
| `test_ingest_email_format` | invoice_1008.txt | Vendor/items extracted, email headers ignored |
| `test_ingest_retry_on_failure` | mock LLM fail once then succeed | Succeeds on retry |

```python
def test_ingest_ocr_normalised():
    """OCR-mangled names must be normalised to match DB."""
    from src.invoice_agents.agents.ingestion.agent import build_ingestion_graph
    from src.invoice_agents.llm import get_llm
    g = build_ingestion_graph(get_llm())
    state = g.invoke({
        "invoice_path": "data/invoices/invoice_1012.pdf",
        "validation_flags": [], "steps_taken": []
    })
    inv = state["extracted_invoice"]
    names = [item["name"] for item in inv["items"]]
    # No spaces in item names after normalisation
    assert all(" " not in n for n in names)
    assert any(n in ("WidgetA","WidgetB","GadgetX") for n in names)
```

### 4.2 Validation sub-graph (`tests/test_validation.py`)

Covers all 5 README scenarios + the data-driven extensions. Deterministic (no LLM).

```python
import pytest

VALIDATION_CASES = [
    # (invoice_dict, expected_flag_type_or_None)
    ("clean_1001", None),
    ("stock_mismatch_1002", "STOCK_MISMATCH"),
    ("zero_stock_1003", "ZERO_STOCK_SUSPICIOUS"),
    ("unknown_1008", "UNKNOWN_ITEM"),
    ("negative_1009", "NEGATIVE_QTY"),
    ("total_mismatch_1013", "TOTAL_MISMATCH"),
    ("foreign_currency_1014", "FOREIGN_CURRENCY"),
]

@pytest.mark.parametrize("case,expected_flag", VALIDATION_CASES)
def test_validation_scenarios(case, expected_flag, fresh_db, invoice_fixtures):
    from src.invoice_agents.agents.validation.flags import compute_flags
    invoice = invoice_fixtures[case]
    flags = compute_flags(invoice, db_path=fresh_db)
    if expected_flag is None:
        assert flags == []
    else:
        assert any(f["type"] == expected_flag for f in flags)
```

### 4.3 Approval sub-graph (`tests/test_approval.py`)

| Test | Scenario | Assert |
|------|----------|--------|
| `test_branch_a_blocking` | flags present | decision REJECT, reflection_count == 0 |
| `test_branch_c_clean_low` | $3K no flags | decision APPROVE, reflection_count == 0 |
| `test_branch_b_high_value` | $15K no flags | decision set, reflection_count ≥ 1 |
| `test_branch_b_loop_caps` | force REVISE | reflection_count ≤ 3 (never exceeds) |
| `test_branch_a_no_llm` | blocking flag | LLM not called (mock asserts zero calls) |
| `test_branch_c_no_llm` | clean low | LLM not called |

```python
def test_branch_b_loop_caps(monkeypatch):
    """Reflection loop must never exceed 3 iterations even if critic always says REVISE."""
    from src.invoice_agents.agents.approval import critic
    # Force critic to always return REVISE
    monkeypatch.setattr(critic, "critique_decision",
                        lambda state, llm: {"_critique_verdict": "REVISE",
                                            "_last_critique": "always revise",
                                            "steps_taken": ["critique"]})
    from src.invoice_agents.agents.approval.agent import build_approval_graph
    from src.invoice_agents.llm import get_llm
    g = build_approval_graph(get_llm())
    state = g.invoke({
        "extracted_invoice": {"vendor":"X","amount":15000,"currency":"USD",
                              "items":[{"name":"WidgetA","qty":5}]},
        "validation_flags": [], "reflection_count": 0, "steps_taken": []
    })
    assert state["reflection_count"] <= 3
    assert state["approval_decision"] in ("APPROVE", "REJECT")
```

### 4.4 Payment sub-graph (`tests/test_payment.py`)

| Test | Scenario | Assert |
|------|----------|--------|
| `test_payment_approved` | decision APPROVE | payment_result status success, transaction_id present |
| `test_payment_deducts_stock` | APPROVE WidgetA×10 | stock reduced from 15 to 5 |
| `test_payment_records_invoice` | APPROVE with invoice_id | paid_invoices has the record |
| `test_rejection_logged` | decision REJECT | rejection_log has invoice_id, flags, reasoning |
| `test_rejection_no_stock_change` | REJECT | stock unchanged |

---

## 5. Layer 3 — End-to-End Tests

One test per official invoice (`tests/test_end_to_end.py`). Runs the full graph.

```python
import pytest
from src.invoice_agents.graph import build_graph

# (filename, expected_status, expected_flag_substring_or_None)
E2E_CASES = [
    ("invoice_1001.txt",          "PAID",     None),
    ("invoice_1002.txt",          "REJECTED", "STOCK_MISMATCH"),
    ("invoice_1003.txt",          "REJECTED", "ZERO_STOCK"),
    ("invoice_1004.json",         "PAID",     None),
    ("invoice_1005.json",         "REJECTED", "STOCK_MISMATCH"),
    ("invoice_1006.csv",          "PAID",     None),
    ("invoice_1007.csv",          "REJECTED", "STOCK_MISMATCH"),
    ("invoice_1008.txt",          "REJECTED", "UNKNOWN_ITEM"),
    ("invoice_1009.json",         "REJECTED", "NEGATIVE_QTY"),
    ("invoice_1010.txt",          "PAID",     None),   # aggregation: 12 ≤ 15
    ("invoice_1011.pdf",          "PAID",     None),
    ("invoice_1012.pdf",          "PAID",     None),   # OCR normalised
    ("invoice_1013.json",         "REJECTED", "STOCK_MISMATCH"),
    ("invoice_1015.csv",          "PAID",     None),
    ("invoice_1016.json",         "REJECTED", "UNKNOWN_ITEM"),
]

@pytest.mark.parametrize("filename,expected_status,expected_flag", E2E_CASES)
def test_invoice_end_to_end(filename, expected_status, expected_flag, fresh_db, monkeypatch):
    monkeypatch.setenv("DB_PATH", fresh_db)
    graph = build_graph()
    state = graph.invoke({
        "invoice_path": f"data/invoices/{filename}",
        "validation_flags": [], "reflection_count": 0, "steps_taken": [],
        "run_id": f"test-{filename}"
    }, config={"configurable": {"thread_id": f"test-{filename}"}})

    if expected_status == "PAID":
        assert state["approval_decision"] == "APPROVE"
        assert state["payment_result"]["status"] == "success"
    else:
        assert state["approval_decision"] == "REJECT"
        if expected_flag:
            flags_str = str(state["validation_flags"]) + str(state.get("approval_reasoning",""))
            assert expected_flag in flags_str
```

---

## 6. Edge Case Test Matrix

Maps each of the 14 complexity traps from PLAN.md Section 4.3 to its test.

| # | Complexity trap | Test name | Layer | Pass condition |
|---|----------------|-----------|-------|----------------|
| 1 | Quantity aggregation | `test_qty_aggregation` + `test_invoice_1010` | Unit + E2E | INV-1010 PAID, INV-1013 catches aggregated overflow |
| 2 | Total reconciliation | `test_total_mismatch` | Unit | TOTAL_MISMATCH flag on $50 discrepancy |
| 3 | OCR artifacts | `test_ingest_ocr_normalised` | Integration | Names have no spaces, match DB |
| 4 | Name normalisation | `test_ingest_ocr_normalised` | Integration | "Widget A" → "WidgetA" |
| 5 | Duplicate invoices | `test_duplicate_invoice` | Unit | DUPLICATE_INVOICE when id in paid_invoices |
| 6 | Foreign currency | `test_foreign_currency` | Unit | FOREIGN_CURRENCY for EUR |
| 7 | Negative values | `test_negative_qty` + `test_negative_amount` | Unit | NEGATIVE_QTY, DATA_INTEGRITY_ERROR |
| 8 | Empty fields | `test_empty_vendor` | Unit | DATA_INTEGRITY_ERROR |
| 9 | Email format | `test_ingest_email_format` | Integration | INV-1008 extracts despite headers |
| 10 | Social engineering | `test_invoice_1003` | E2E | FakeItem stock=0 → REJECTED |
| 11 | Tax + shipping | `test_subtotal_total_split` | Unit | total used for amount, subtotal for items |
| 12 | Two CSV styles | `test_parse_csv_keyvalue` + `test_parse_csv_tabular` | Unit | Both styles parse |
| 13 | Stock deduction | `test_payment_deducts_stock` | Integration | Stock reduced after payment |
| 14 | Reflection runaway | `test_branch_b_loop_caps` | Integration | reflection_count ≤ 3 |

---

## 7. Reflection Loop Tests

The reflection loop is the assignment's key differentiator — test it thoroughly.

| Test | What it verifies |
|------|-----------------|
| `test_reflection_triggers_high_value` | $15K invoice enters Branch B, reflection_count ≥ 1 |
| `test_reflection_not_triggered_low_value` | $3K invoice uses Branch C, reflection_count == 0 |
| `test_reflection_accept_exits` | Critic ACCEPT exits loop immediately |
| `test_reflection_revise_loops` | Critic REVISE loops back to generator |
| `test_reflection_caps_at_3` | Even with always-REVISE, stops at 3 |
| `test_reflection_produces_reasoning` | Final approval_reasoning is non-empty and references iterations |
| `test_reflection_blocking_skips_loop` | Blocking flags skip reflection entirely (Branch A) |

```python
def test_reflection_produces_reasoning(fresh_db):
    """High-value approval must carry a reasoning chain for audit."""
    from src.invoice_agents.graph import build_graph
    graph = build_graph()
    state = graph.invoke({
        "invoice_path": "data/invoices/invoice_high_value.txt",  # any clean >$10K
        "validation_flags": [], "reflection_count": 0, "steps_taken": [],
        "run_id": "test-reflection"
    }, config={"configurable": {"thread_id": "test-reflection"}})
    assert state["approval_reasoning"]
    assert len(state["approval_reasoning"]) > 20
    assert state["reflection_count"] >= 1
```

---

## 8. Negative & Failure Tests

Test that the system fails gracefully.

| Test | Scenario | Expected behaviour |
|------|----------|-------------------|
| `test_missing_file` | nonexistent path | FileNotFoundError with clear message |
| `test_empty_file` | empty invoice | ingestion_error set, routed to rejection |
| `test_corrupt_pdf` | malformed PDF | pdfplumber fallback, or graceful error |
| `test_malformed_json` | invalid JSON | Parser handles, LLM extraction attempts |
| `test_llm_timeout` | mock LLM timeout | Retry policy kicks in |
| `test_llm_persistent_failure` | LLM fails 3× | ExtractionError raised, logged |
| `test_payment_failure` | mock_payment raises | RetryPolicy retries, then error_handler routes to rejection |
| `test_no_items` | invoice with empty items list | DATA_INTEGRITY_ERROR or graceful handling |
| `test_sql_injection_item_name` | item name with SQL | Parameterised query prevents injection |

```python
def test_empty_file(tmp_path, fresh_db):
    from src.invoice_agents.graph import build_graph
    empty = tmp_path / "empty.txt"
    empty.write_text("")
    graph = build_graph()
    state = graph.invoke({
        "invoice_path": str(empty), "validation_flags": [],
        "reflection_count": 0, "steps_taken": [], "run_id": "test-empty"
    }, config={"configurable": {"thread_id": "test-empty"}})
    # Should not crash — either rejected or ingestion_error set
    assert state.get("ingestion_error") or state.get("approval_decision") == "REJECT"
```

---

## 9. Regression Checklist

Run this full checklist before declaring the project done. Every box must be checked.

**Inventory data integrity**
- [ ] WidgetA=15, WidgetB=10, GadgetX=5, FakeItem=0 seeded correctly
- [ ] `python main.py --setup` is idempotent (safe to run twice)

**All 6 formats**
- [ ] TXT parses (invoice_1001)
- [ ] JSON parses (invoice_1004)
- [ ] CSV key-value parses (invoice_1006)
- [ ] CSV tabular parses (invoice_1007)
- [ ] PDF parses (invoice_1011)
- [ ] XML parses (invoice_1014)

**All routing branches**
- [ ] Branch A reached (any blocking flag invoice) — zero LLM calls
- [ ] Branch B reached ($15K clean invoice) — reflection runs
- [ ] Branch C reached ($3K clean invoice) — zero LLM calls

**All 10 flag types fire**
- [ ] STOCK_MISMATCH (INV-1002)
- [ ] UNKNOWN_ITEM (INV-1008)
- [ ] ZERO_STOCK_SUSPICIOUS (INV-1003)
- [ ] NEGATIVE_QTY (INV-1009)
- [ ] DATA_INTEGRITY_ERROR (INV-1009 empty vendor)
- [ ] DUPLICATE_INVOICE (INV-1004 then INV-1004_revised)
- [ ] TOTAL_MISMATCH (INV-1013)
- [ ] FOREIGN_CURRENCY (INV-1014)
- [ ] FRAUD_SIGNAL (INV-1003)
- [ ] (fuzzy match fallback verified)

**Critical behaviours**
- [ ] Quantity aggregation: INV-1010 PAID (12≤15), aggregation overflow caught
- [ ] Stock deducted after payment (re-run same invoice → may fail 2nd time)
- [ ] Reflection loop caps at 3
- [ ] SQL injection blocked
- [ ] No state mutated in-place (review node return values)

**Output**
- [ ] Every run produces structured JSON log
- [ ] PAID log has vendor, amount, transaction_id
- [ ] REJECTED log has flags and reasoning

---

## 10. Manual / UI Tests

Streamlit UI tests (run manually, not automated).

| Test | Steps | Expected |
|------|-------|----------|
| Upload TXT | Upload invoice_1001.txt, click Process | "PAID" banner, line items in table |
| Upload rejected | Upload invoice_1002.txt, click Process | "REJECTED" banner, STOCK_MISMATCH warning |
| High-value reflection | Upload $15K invoice | System Trace tab shows reflection steps |
| Inventory sidebar | Open app | Sidebar shows current inventory table |
| Session history | Process 3 invoices | History shows last 3 with status |
| Invoice Data tab | Process any | Vendor/Amount/Due Date metrics + line item table |
| Executive Summary tab | Process rejected | Clear status + reasoning displayed |
| All formats via UI | Upload one of each (txt, json, csv, pdf, xml) | All process without crash |

---

## 11. Test Execution Commands

```bash
# Full suite (run before declaring done)
pytest tests/ -v --tb=short

# Fast feedback during development (stop at first failure, terse)
pytest tests/ -x --tb=short -q 2>&1 | head -80

# Unit tests only (no LLM, fast, deterministic)
pytest tests/test_parsers.py tests/test_db.py tests/test_flags.py tests/test_rules.py -v

# Validation tests (deterministic, all 5 README scenarios + extensions)
pytest tests/test_validation.py -v

# Integration tests per agent
pytest tests/test_ingestion.py -v          # uses LLM
pytest tests/test_approval.py -v           # uses LLM
pytest tests/test_payment.py -v

# End-to-end (slow, full pipeline)
pytest tests/test_end_to_end.py -v

# Edge cases only
pytest tests/ -k "aggregation or total_mismatch or duplicate or currency or ocr" -v

# Reflection loop suite
pytest tests/ -k "reflection or branch_b" -v

# Negative / failure tests
pytest tests/ -k "empty or corrupt or injection or failure or timeout" -v

# Coverage report
pytest tests/ --cov=src/invoice_agents --cov-report=term-missing

# Single invoice manual run (smoke test)
python main.py --setup
python main.py --invoice_path=data/invoices/invoice_1001.txt   # expect PAID
python main.py --invoice_path=data/invoices/invoice_1002.txt   # expect REJECTED
python main.py --invoice_path=data/invoices/invoice_1003.txt   # expect REJECTED
python main.py --invoice_path=data/invoices/invoice_1013.json  # expect REJECTED (aggregation + total)
```

---

## Test Pass Criteria Summary

| Phase | Minimum passing tests before moving on |
|-------|----------------------------------------|
| Phase 1 | All parser unit tests + DB unit tests |
| Phase 2 | Model imports + flag type definitions |
| Phase 3 | All ingestion integration tests (incl. OCR, email, all formats) |
| Phase 4 | All validation tests + all 10 flag unit tests + aggregation tests |
| Phase 5 | All approval tests + all reflection loop tests |
| Phase 6 | All end-to-end tests (15 parametrized invoices) |
| Phase 7 | All manual UI tests |
| Phase 8 | Full regression checklist — every box checked |

**The project is test-complete when:**
- All 15 parametrized end-to-end invoices route correctly
- All 14 complexity traps have passing tests
- All 7 reflection loop tests pass
- All 9 negative/failure tests pass
- The full regression checklist is 100% checked
