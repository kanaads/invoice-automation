# Graph Report - invoiceApproval  (2026-07-05)

## Corpus Check
- 37 files · ~17,734 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 240 nodes · 325 edges · 24 communities (22 shown, 2 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 8 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Phase 0 — Claude Code Development Plan|Phase 0 — Claude Code Development Plan]]
- [[_COMMUNITY_PLAN.md — Invoice Processing Automation (Galatiq Case)|PLAN.md — Invoice Processing Automation (Galatiq Case)]]
- [[_COMMUNITY_TESTPLAN.md — Invoice Processing Automation|TESTPLAN.md — Invoice Processing Automation]]
- [[_COMMUNITY_test_parsers.py|test_parsers.py]]
- [[_COMMUNITY_agent.py|agent.py]]
- [[_COMMUNITY_DATA_MODEL.md — Invoice Processing Automation (Galatiq Case)|DATA_MODEL.md — Invoice Processing Automation (Galatiq Case)]]
- [[_COMMUNITY_test_ingestion.py|test_ingestion.py]]
- [[_COMMUNITY_Galatiq Case Invoice Processing Automation|Galatiq Case: Invoice Processing Automation]]
- [[_COMMUNITY_test_db.py|test_db.py]]
- [[_COMMUNITY_6. Phased Development Plan|6. Phased Development Plan]]
- [[_COMMUNITY_3. Essential Skills & Docs Reference Library|3. Essential Skills & Docs Reference Library]]
- [[_COMMUNITY_conftest.py|conftest.py]]
- [[_COMMUNITY_flags.py|flags.py]]
- [[_COMMUNITY_setup_db.py|setup_db.py]]
- [[_COMMUNITY_CLAUDE|CLAUDE.md]]

## God Nodes (most connected - your core abstractions)
1. `compute_flags()` - 24 edges
2. `_invoice()` - 17 edges
3. `PLAN.md — Invoice Processing Automation (Galatiq Case)` - 16 edges
4. `TESTPLAN.md — Invoice Processing Automation` - 15 edges
5. `DATA_MODEL.md — Invoice Processing Automation (Galatiq Case)` - 12 edges
6. `Phase 0 — Claude Code Development Plan` - 12 edges
7. `_run()` - 11 edges
8. `load_invoice()` - 10 edges
9. `get_stock()` - 10 edges
10. `InvoiceState` - 9 edges

## Surprising Connections (you probably didn't know these)
- `_run()` --calls--> `build_ingestion_graph()`  [EXTRACTED]
  tests/test_ingestion.py → src/invoice_agents/agents/ingestion/agent.py
- `test_all_official_invoices_parse()` --calls--> `load_invoice()`  [EXTRACTED]
  tests/test_parsers.py → src/invoice_agents/agents/ingestion/parsers.py
- `test_load_invoice_router()` --calls--> `load_invoice()`  [EXTRACTED]
  tests/test_parsers.py → src/invoice_agents/agents/ingestion/parsers.py
- `test_parse_json()` --calls--> `load_invoice()`  [EXTRACTED]
  tests/test_parsers.py → src/invoice_agents/agents/ingestion/parsers.py
- `test_parse_pdf_markitdown()` --calls--> `load_invoice()`  [EXTRACTED]
  tests/test_parsers.py → src/invoice_agents/agents/ingestion/parsers.py

## Import Cycles
- None detected.

## Communities (24 total, 2 thin omitted)

### Community 0 - "Phase 0 — Claude Code Development Plan"
Cohesion: 0.08
Nodes (25): 1. Token Optimization Stack, 2. CLAUDE.md Rules File, 4. Model Strategy, 5.1 bash-ban-raw-tools Hook, 5.2 Test Output Filtering Hook, 5.3 SQL Safety Hook, 5. Pre-Processing Hooks & Enforcement, 7. Session Management Protocol (+17 more)

### Community 1 - "PLAN.md — Invoice Processing Automation (Galatiq Case)"
Cohesion: 0.08
Nodes (23): 10. Build Sequence, 11. Definition of Done, 12. Risk Register, 1. The Assignment, 2. Evaluation Criteria, 3. Architecture Overview, 4.1 Format coverage (6 formats), 4.2 The complete invoice-to-outcome map (+15 more)

### Community 2 - "TESTPLAN.md — Invoice Processing Automation"
Cohesion: 0.08
Nodes (23): 10. Manual / UI Tests, 11. Test Execution Commands, 1. Test Strategy, 2. Test Environment Setup, 3.1 Parser tests (`tests/test_parsers.py`), 3.2 Database tests (`tests/test_db.py`), 3.3 Flag computation tests (`tests/test_flags.py`) — the most important unit tests, 3.4 Approval rules tests (`tests/test_rules.py`) (+15 more)

### Community 3 - "test_parsers.py"
Cohesion: 0.19
Nodes (11): load_invoice(), _parse_csv(), Format parsers: each returns the invoice content as plain text for LLM extractio, test_all_official_invoices_parse(), test_load_invoice_router(), test_parse_csv_keyvalue(), test_parse_csv_tabular(), test_parse_json() (+3 more)

### Community 4 - "agent.py"
Cohesion: 0.16
Nodes (18): BaseModel, build_ingestion_graph(), _extract_node(), _parse_node(), Ingestion sub-graph: format router -> LLM extraction with retry., extract_invoice(), LLM-based structured extraction from raw invoice text., build_validation_graph() (+10 more)

### Community 5 - "DATA_MODEL.md — Invoice Processing Automation (Galatiq Case)"
Cohesion: 0.12
Nodes (15): 10. Alignment note for PLAN.md and TESTPLAN.md, 1.1 Baseline (as given in README.md — verified exact), 1.2 Extended schema (per PLAN.md / TESTPLAN.md), 1.3 Full seed data (extended) — **[CORRECTED]** unit prices now match the invoices, 1. Table: `inventory`, 2. Table: `paid_invoices`, 3. Entity relationship, 4. Operations against the model (+7 more)

### Community 6 - "test_ingestion.py"
Cohesion: 0.21
Nodes (14): get_llm(), Swappable LLM factory. Default backend is Groq (free tier); override with LLM_BA, OCR-mangled names ('Widget A', 'Gadget X') must be normalised to match the DB., Invoice embedded in an email; vendor/items must extract despite headers., A transient extraction failure must be retried, not fatal., _run(), test_ingest_clean_txt(), test_ingest_csv() (+6 more)

### Community 7 - "Galatiq Case: Invoice Processing Automation"
Cohesion: 0.14
Nodes (13): Background, Evaluation Criteria, Galatiq Case: Invoice Processing Automation, Grok API Setup, Mock Inventory Database (Required Setup), Mock Invoice Data, Mock Payment API, Objective (+5 more)

### Community 8 - "test_db.py"
Cohesion: 0.20
Nodes (16): check_duplicate(), deduct_stock(), get_stock(), record_payment(), _aggregate_quantities(), _flag(), Deterministic validation flags. No LLM involved -- must be 100% reproducible., Group by item name and sum quantities -- same item on multiple lines must combin (+8 more)

### Community 9 - "6. Phased Development Plan"
Cohesion: 0.22
Nodes (9): 6. Phased Development Plan, Phase 1 — Scaffold + DB + Parsers (Session 1, ~45 min), Phase 2 — State + Models + LLM Factory (Session 2, ~30 min), Phase 3 — Ingestion Agent (Session 3, ~45 min), Phase 4 — Validation Agent (Session 4, ~45 min), Phase 5 — Approval Agent with Reflection Loop (Session 5, ~60 min), Phase 6 — Payment Agent + Orchestrator (Session 6, ~45 min), Phase 7 — Streamlit UI (Session 7, ~60 min) (+1 more)

### Community 10 - "3. Essential Skills & Docs Reference Library"
Cohesion: 0.25
Nodes (8): 3.1 LangGraph (Primary Framework), 3.2 LangChain (LLM Integration), 3.3 SQLite (Inventory Database), 3.4 PDF/Document Parsing, 3.5 Pydantic v2 (Data Models), 3.6 Streamlit (UI), 3.7 Testing, 3. Essential Skills & Docs Reference Library

### Community 11 - "conftest.py"
Cohesion: 0.33
Nodes (4): fresh_db(), A per-test copy so stock deductions don't leak between tests., Create a fresh inventory.db with the project's seed data for tests., test_db()

### Community 12 - "flags.py"
Cohesion: 0.20
Nodes (23): compute_flags(), _invoice(), INV-1009: negative qty + empty vendor + negative total -> at least 2 flags., INV-1013: aggregated quantities over stock on all 3 items, plus a $50 tax->total, INV-1010: WidgetA appears twice (8 + 4 = 12), still within stock of 15., CRITICAL: same item on multiple lines must aggregate before comparing to stock., Aggregated qty exceeds stock even though each individual line is fine., test_clean_passes() (+15 more)

## Knowledge Gaps
- **101 isolated node(s):** `graphify`, `Purpose`, `1.1 Baseline (as given in README.md — verified exact)`, `1.2 Extended schema (per PLAN.md / TESTPLAN.md)`, `1.3 Full seed data (extended) — **[CORRECTED]** unit prices now match the invoices` (+96 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `compute_flags()` connect `flags.py` to `test_db.py`, `agent.py`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Why does `Phase 0 — Claude Code Development Plan` connect `Phase 0 — Claude Code Development Plan` to `6. Phased Development Plan`, `3. Essential Skills & Docs Reference Library`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **What connects `Creates and seeds inventory.db. Run with: python setup_db.py`, `Ingestion sub-graph: format router -> LLM extraction with retry.`, `LLM-based structured extraction from raw invoice text.` to the rest of the system?**
  _119 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Phase 0 — Claude Code Development Plan` be split into smaller, more focused modules?**
  _Cohesion score 0.07692307692307693 - nodes in this community are weakly interconnected._
- **Should `PLAN.md — Invoice Processing Automation (Galatiq Case)` be split into smaller, more focused modules?**
  _Cohesion score 0.08333333333333333 - nodes in this community are weakly interconnected._
- **Should `TESTPLAN.md — Invoice Processing Automation` be split into smaller, more focused modules?**
  _Cohesion score 0.08333333333333333 - nodes in this community are weakly interconnected._
- **Should `DATA_MODEL.md — Invoice Processing Automation (Galatiq Case)` be split into smaller, more focused modules?**
  _Cohesion score 0.125 - nodes in this community are weakly interconnected._