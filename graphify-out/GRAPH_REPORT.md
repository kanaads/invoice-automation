# Graph Report - invoiceApproval  (2026-07-05)

## Corpus Check
- 43 files · ~18,675 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 282 nodes · 429 edges · 26 communities (24 shown, 2 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 14 edges (avg confidence: 0.56)
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
- [[_COMMUNITY_test_rules.py|test_rules.py]]
- [[_COMMUNITY_agent.py|agent.py]]

## God Nodes (most connected - your core abstractions)
1. `compute_flags()` - 24 edges
2. `InvoiceState` - 18 edges
3. `_invoice()` - 17 edges
4. `build_approval_graph()` - 16 edges
5. `PLAN.md — Invoice Processing Automation (Galatiq Case)` - 16 edges
6. `TESTPLAN.md — Invoice Processing Automation` - 15 edges
7. `DATA_MODEL.md — Invoice Processing Automation (Galatiq Case)` - 12 edges
8. `Phase 0 — Claude Code Development Plan` - 12 edges
9. `_run()` - 11 edges
10. `load_invoice()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `test_has_blocking_flags()` --calls--> `has_blocking_flags()`  [EXTRACTED]
  tests/test_rules.py → src/invoice_agents/agents/approval/rules.py
- `test_has_blocking_flags_false()` --calls--> `has_blocking_flags()`  [EXTRACTED]
  tests/test_rules.py → src/invoice_agents/agents/approval/rules.py
- `test_requires_reflection()` --calls--> `requires_reflection()`  [EXTRACTED]
  tests/test_rules.py → src/invoice_agents/agents/approval/rules.py
- `test_requires_reflection_false_when_flagged()` --calls--> `requires_reflection()`  [EXTRACTED]
  tests/test_rules.py → src/invoice_agents/agents/approval/rules.py
- `test_requires_reflection_false_when_low()` --calls--> `requires_reflection()`  [EXTRACTED]
  tests/test_rules.py → src/invoice_agents/agents/approval/rules.py

## Import Cycles
- None detected.

## Communities (26 total, 2 thin omitted)

### Community 0 - "Phase 0 — Claude Code Development Plan"
Cohesion: 0.06
Nodes (34): 1. Token Optimization Stack, 2. CLAUDE.md Rules File, 4. Model Strategy, 5.1 bash-ban-raw-tools Hook, 5.2 Test Output Filtering Hook, 5.3 SQL Safety Hook, 5. Pre-Processing Hooks & Enforcement, 6. Phased Development Plan (+26 more)

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
Cohesion: 0.29
Nodes (8): BaseModel, generate_decision(), Generator: drafts an approval decision for high-value, clean invoices., extract_invoice(), LLM-based structured extraction from raw invoice text., ApprovalDecision, Invoice, LineItem

### Community 5 - "DATA_MODEL.md — Invoice Processing Automation (Galatiq Case)"
Cohesion: 0.12
Nodes (15): 10. Alignment note for PLAN.md and TESTPLAN.md, 1.1 Baseline (as given in README.md — verified exact), 1.2 Extended schema (per PLAN.md / TESTPLAN.md), 1.3 Full seed data (extended) — **[CORRECTED]** unit prices now match the invoices, 1. Table: `inventory`, 2. Table: `paid_invoices`, 3. Entity relationship, 4. Operations against the model (+7 more)

### Community 6 - "test_ingestion.py"
Cohesion: 0.19
Nodes (16): build_ingestion_graph(), _extract_node(), _parse_node(), Ingestion sub-graph: format router -> LLM extraction with retry., OCR-mangled names ('Widget A', 'Gadget X') must be normalised to match the DB., Invoice embedded in an email; vendor/items must extract despite headers., A transient extraction failure must be retried, not fatal., _run() (+8 more)

### Community 7 - "Galatiq Case: Invoice Processing Automation"
Cohesion: 0.14
Nodes (13): Background, Evaluation Criteria, Galatiq Case: Invoice Processing Automation, Grok API Setup, Mock Inventory Database (Required Setup), Mock Invoice Data, Mock Payment API, Objective (+5 more)

### Community 8 - "test_db.py"
Cohesion: 0.20
Nodes (16): check_duplicate(), deduct_stock(), get_stock(), record_payment(), _aggregate_quantities(), _flag(), Deterministic validation flags. No LLM involved -- must be 100% reproducible., Group by item name and sum quantities -- same item on multiple lines must combin (+8 more)

### Community 9 - "6. Phased Development Plan"
Cohesion: 0.17
Nodes (24): _approve_rule_node(), build_approval_graph(), _critique_node(), _critique_router(), _entry_router(), _finalize_node(), _generate_node(), Approval sub-graph: 3-way router (blocking-reject / reflection / rule-approve). (+16 more)

### Community 10 - "3. Essential Skills & Docs Reference Library"
Cohesion: 0.25
Nodes (8): 3.1 LangGraph (Primary Framework), 3.2 LangChain (LLM Integration), 3.3 SQLite (Inventory Database), 3.4 PDF/Document Parsing, 3.5 Pydantic v2 (Data Models), 3.6 Streamlit (UI), 3.7 Testing, 3. Essential Skills & Docs Reference Library

### Community 11 - "conftest.py"
Cohesion: 0.33
Nodes (4): fresh_db(), A per-test copy so stock deductions don't leak between tests., Create a fresh inventory.db with the project's seed data for tests., test_db()

### Community 12 - "flags.py"
Cohesion: 0.20
Nodes (23): compute_flags(), _invoice(), INV-1009: negative qty + empty vendor + negative total -> at least 2 flags., INV-1013: aggregated quantities over stock on all 3 items, plus a $50 tax->total, INV-1010: WidgetA appears twice (8 + 4 = 12), still within stock of 15., CRITICAL: same item on multiple lines must aggregate before comparing to stock., Aggregated qty exceeds stock even though each individual line is fine., test_clean_passes() (+15 more)

### Community 24 - "test_rules.py"
Cohesion: 0.21
Nodes (14): has_blocking_flags(), Rule-based routing thresholds for the approval sub-graph. No LLM involved., Branch B: high-value AND clean. Blocking flags always win over the amount thresh, Branch C: low-value AND clean -- auto-approve with zero LLM calls., requires_reflection(), rule_based_approve(), test_has_blocking_flags(), test_has_blocking_flags_false() (+6 more)

### Community 25 - "agent.py"
Cohesion: 0.48
Nodes (5): build_validation_graph(), Validation sub-graph: deterministic flag computation against the inventory DB., _validate_node(), test_validation_scenarios(), test_validation_writes_steps_taken()

## Knowledge Gaps
- **101 isolated node(s):** `graphify`, `Purpose`, `1.1 Baseline (as given in README.md — verified exact)`, `1.2 Extended schema (per PLAN.md / TESTPLAN.md)`, `1.3 Full seed data (extended) — **[CORRECTED]** unit prices now match the invoices` (+96 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `InvoiceState` connect `6. Phased Development Plan` to `agent.py`, `agent.py`, `test_ingestion.py`?**
  _High betweenness centrality (0.099) - this node is a cross-community bridge._
- **Why does `compute_flags()` connect `flags.py` to `test_db.py`, `agent.py`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Why does `load_invoice()` connect `test_parsers.py` to `test_ingestion.py`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `InvoiceState` (e.g. with `build_approval_graph()` and `build_ingestion_graph()`) actually correct?**
  _`InvoiceState` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `build_approval_graph()` (e.g. with `_approve_rule_node()` and `_critique_router()`) actually correct?**
  _`build_approval_graph()` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Creates and seeds inventory.db. Run with: python setup_db.py`, `Approval sub-graph: 3-way router (blocking-reject / reflection / rule-approve).`, `Critic: reviews the Generator's draft decision and either accepts or requests re` to the rest of the system?**
  _126 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Phase 0 — Claude Code Development Plan` be split into smaller, more focused modules?**
  _Cohesion score 0.05714285714285714 - nodes in this community are weakly interconnected._