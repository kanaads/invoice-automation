# PLAN.md — Invoice Processing Automation (Galatiq Case)
## Master Development Plan

> **How to use this file:** This is the single entry point for the project in a fresh workspace. It contains the complete requirements, architecture, build sequence, and every edge case discovered from analysing the official test data. Read this first. Then follow the phase sequence. Companion files: `IMPLEMENTATION_SPEC.md` (detailed code spec), `TESTPLAN.md` (test cases), `COMPARATIVE_STUDY.md` (data corrections).

---

## Table of Contents
1. [The Assignment — What We Must Deliver](#1-the-assignment)
2. [Evaluation Criteria — What We're Scored On](#2-evaluation-criteria)
3. [Architecture Overview](#3-architecture-overview)
4. [The Complete Edge Case Catalogue](#4-edge-case-catalogue)
5. [Technology Decisions](#5-technology-decisions)
6. [Project Structure](#6-project-structure)
7. [State Design](#7-state-design)
8. [The Four Agents](#8-the-four-agents)
9. [Routing Logic](#9-routing-logic)
10. [Build Sequence (8 Phases)](#10-build-sequence)
11. [Definition of Done](#11-definition-of-done)
12. [Risk Register](#12-risk-register)

---

## 1. The Assignment

**Company:** Acme Corp — a PE-backed manufacturer losing **$2M/year** on manual invoice processing. Current state: 30% error rate, 5-day processing delays, frustrated stakeholders.

**Mandate:** Build a **multi-agent system** that automates end-to-end invoice processing as a **working prototype** (not slides, not designs — running code).

**The four workflow stages (all required):**

1. **Ingestion** — Extract structured data (Vendor, Amount, Items+quantities, Due Date) from invoice documents in multiple formats. Expect unstructured text, typos, missing data, and fraudulent entries.
2. **Validation** — Verify extracted data against a mock SQLite inventory database. Flag mismatches: quantity exceeding stock, items not found, out-of-stock items.
3. **Approval** — Simulate VP-level review with rule-based decisions (invoices over $10K require extra scrutiny). **Must include a reflection or critique loop.**
4. **Payment** — If approved, call a mock payment function. If rejected, log the rejection with reasoning.

**Hard technical requirements:**
- LLM integration (xAI Grok suggested; any model acceptable)
- Multi-agent orchestration framework (LangGraph chosen)
- Function calling / tool use, structured outputs, self-correction loops
- Runs entirely locally — no internet for external APIs, simulate everything
- Python, executable from CLI: `python main.py --invoice_path=...`
- Output: structured logs and results

---

## 2. Evaluation Criteria

These are the seven dimensions we are scored on. Each phase must contribute to these.

| Criterion | What it means | How we win it |
|-----------|--------------|---------------|
| **Functionality** | Does it work end-to-end? | All 20 official invoices route to correct outcomes |
| **Code Quality** | Clean, testable, error handling, observability | Typed state, parameterised SQL, retry logic, full test suite |
| **Agentic Sophistication** | LLM integration, multi-agent flow, tool use, self-correction | Sub-graphs + Generator/Critic reflection loop + structured output |
| **Shipping Mindset** | Valuable MVP under ambiguity, ruthless scoping | Phased build, working CLI before UI, Branch C avoids LLM when unneeded |
| **Presentation** | Translate technical decisions to business impact | Demo docs framing $2M/5-day → seconds, structured logs |
| **Above & Beyond** | Made it your own, extra features, expanded assumptions, added test cases | 10 flag types, fraud detection, stock deduction, quantity aggregation |
| **UI/UX** | Users understand and enjoy using it | Streamlit 3-tab dashboard |

**The single biggest differentiator: the reflection/critique loop.** The assignment names it explicitly. A competitor implementation (DevDizzle) shipped a polished UI but made a single LLM call with no reflection loop — this is the gap that separates a passing solution from a strong one.

---

## 3. Architecture Overview

**Pattern:** Supervisor orchestrator over four compiled sub-graphs, sharing one `InvoiceState` TypedDict.

```
CLI (main.py)
   │
   ▼
Orchestrator (parent StateGraph, conditional routing)
   │
   ├─► Ingestion Sub-Graph    (format router → LLM extraction)
   │       │ writes: extracted_invoice
   ▼       │
   ├─► Validation Sub-Graph   (aggregate → integrity → SQLite → reconcile → flags)
   │       │ writes: validation_flags
   ▼       │
   ├─► Approval Sub-Graph      (3-way router)
   │       ├─ Branch A: blocking flags → REJECT (no LLM)
   │       ├─ Branch B: >$10K clean → Generator→Critic reflection loop (max 3)
   │       └─ Branch C: ≤$10K clean → rule approve (no LLM)
   │       │ writes: approval_decision, approval_reasoning, reflection_count
   ▼       │
   └─► Payment Sub-Graph       (pay → deduct stock → record  OR  log rejection)
           │ writes: payment_result OR rejection_log
   ▼
Structured log output (PAID or REJECTED)
```

**Why this design meets every requirement:**
- **Multi-agent**: 4 compiled sub-graphs, each independently testable, not a monolith and not over-granular.
- **Tool use**: SQLite queries, mock_payment, structured output extraction.
- **Self-correction**: extraction retry loop (3×) + approval reflection loop (Generator→Critic, max 3).
- **Structured output**: `with_structured_output()` for Invoice, ApprovalDecision, CritiqueResult.
- **Runs locally**: SQLite + mock payment, no external calls except the LLM.
- **Deterministic where it matters**: validation and routing are pure Python; LLM only where judgment adds value (extraction, high-value approval).

---

## 4. Edge Case Catalogue

**This is the heart of the project.** The official repo has 20 files across 6 formats. The README table describes only 5 scenarios — the actual data is far richer. Every one of these must be handled.

### 4.1 Format coverage (6 formats)

| Format | Files | Parser approach |
|--------|-------|-----------------|
| TXT | 7 files (incl. email-format INV-1008, messy INV-1002) | Plain read |
| JSON | 6 files (incl. broken INV-1009, bulk INV-1013) | json.load → json.dumps |
| CSV | 3 files — TWO styles: key-value (INV-1006) and tabular (INV-1007, INV-1015) | Detect style, parse accordingly |
| PDF | 3 files (INV-1011, 1012-messy/OCR, 1013-bulk) | MarkItDown → pdfplumber fallback |
| XML | 1 file (INV-1014, EUR currency) | xml.etree.ElementTree |

### 4.2 The complete invoice-to-outcome map

| Invoice | Items (real data) | Amount | Flag(s) | Branch | Outcome |
|---------|-------------------|--------|---------|--------|---------|
| 1001 | WidgetA×10, WidgetB×5 | $5,000 | none | C | PAID |
| 1002 | GadgetX×20 (stock=5) | $15,000 | STOCK_MISMATCH | A | REJECTED |
| 1003 | FakeItem×100 (stock=0) | $100,000 | ZERO_STOCK_SUSPICIOUS + FRAUD_SIGNAL | A | REJECTED |
| 1004 | WidgetA×3, WidgetB×2 | $1,890 | none | C | PAID |
| 1004_revised | WidgetA×3, WidgetB×2, GadgetX×5 | $5,940 | DUPLICATE_INVOICE (if 1004 paid) | A or C | DEPENDS |
| 1005 | WidgetA×14, GadgetX×8, WidgetB×10 | $15,225 | STOCK_MISMATCH (GadgetX 8>5) | A | REJECTED |
| 1006 | WidgetA×5, WidgetB×3 | $2,750 | none | C | PAID |
| 1007 | WidgetA×20, WidgetB×15, GadgetX×3 | $15,525 | STOCK_MISMATCH (WidgetA 20>15, WidgetB 15>10) | A | REJECTED |
| 1008 | SuperGizmo×12, MegaSprocket×6 | $9,900 | UNKNOWN_ITEM ×2 | A | REJECTED |
| 1009 | WidgetA×(-5), WidgetB×2 | -$250 | NEGATIVE_QTY + EMPTY_VENDOR + DATA_INTEGRITY | A | REJECTED |
| 1010 | WidgetA×8 + WidgetA×4, WidgetB×4, GadgetX×2 | $7,185 | none (aggregated 12≤15) | C | PAID |
| 1011 | WidgetA×6, WidgetB×3 | $3,000 | none | C | PAID |
| 1012 | WidgetA×12, WidgetB×7, GadgetX×4 (OCR-mangled names) | $9,975 | none (after normalisation) | C | PAID |
| 1013 | WidgetA×22 (3 lines aggregated), WidgetB×18, GadgetX×9 | $22,562.80 | STOCK_MISMATCH + TOTAL_MISMATCH | A | REJECTED |
| 1014 | WidgetA×4, WidgetB×6 | €4,125 | FOREIGN_CURRENCY | C+warn | PAID w/ warning |
| 1015 | WidgetA×10, WidgetB×5, GadgetX×2 | $6,500 | none | C | PAID |
| 1016 | WidgetA×4, WidgetB×2, WidgetC×3 | $3,233 | UNKNOWN_ITEM or ZERO_STOCK (WidgetC) | A | REJECTED |

### 4.3 The complexity traps (must handle, easy to miss)

| # | Complexity | Which invoice | Why it's a trap | Solution |
|---|-----------|---------------|-----------------|----------|
| 1 | **Quantity aggregation** | INV-1010, INV-1013 | Same item appears on multiple lines. Checking each line individually passes (15≤15) but the true total fails (22>15) | Group by item name, SUM quantities, THEN compare to stock |
| 2 | **Total reconciliation** | INV-1013 | PDF grand total is $50 higher than the sum of line items — deliberate fraud | Compare stated total vs computed sum, flag if diff > $0.01 |
| 3 | **OCR artifacts** | INV-1012 | "2O26" (letter O), "$3,500.O0", "Widget A" with space | LLM extraction prompt must fix OCR errors and normalise names |
| 4 | **Item name normalisation** | INV-1012 | "Widget A" vs "WidgetA", "Gadget X" vs "GadgetX" | Normalise at extraction (remove spaces) + fuzzy match fallback |
| 5 | **Duplicate invoices** | INV-1004 + INV-1004_revised | Same invoice_id, "revision: R1" — double payment risk | Check paid_invoices table before approving |
| 6 | **Foreign currency** | INV-1014 | EUR not USD — $10K threshold comparison is wrong | Extract currency field, flag if not USD |
| 7 | **Negative values** | INV-1009 | qty=-5, total=-$250 | Check qty>0 AND amount>0 |
| 8 | **Empty/null fields** | INV-1009 | Empty vendor "", null due_date | Check vendor non-empty, warn on missing date |
| 9 | **Email format** | INV-1008 | Invoice embedded in email with From/To/Subject headers | Extraction prompt ignores email headers |
| 10 | **Social engineering** | INV-1003 | "URGENT", "Wire transfer preferred", "due yesterday" | Extraction flags fraud signals; FakeItem stock=0 = blocking |
| 11 | **Tax + shipping** | Multiple | Total includes tax/shipping — which figure for $10K threshold? | Extract subtotal AND total; use total for amount, subtotal for line validation |
| 12 | **Two CSV styles** | INV-1006 vs INV-1007 | Key-value rows vs tabular rows | Detect format in parser |
| 13 | **Stock depletion after payment** | Any approved | Paying doesn't reduce inventory → next invoice re-validates against stale stock | deduct_stock() after successful payment |
| 14 | **Reflection loop runaway** | Any >$10K | LLM keeps saying REVISE forever | MAX_REFLECTION_ITERATIONS=3 hard cap |

---

## 5. Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Orchestration | **LangGraph** | Sub-graphs, conditional edges, checkpointing, native reflection loop support |
| State | **TypedDict** with `operator.add` reducers | Lightweight, no runtime overhead, partial updates merge cleanly |
| Extraction models | **Pydantic v2** | Type-safe, field descriptions inject into LLM prompts |
| LLM | **ChatXAI (Grok)** via factory, swappable | Assignment suggests Grok; factory allows OpenAI/local fallback |
| LLM output | **with_structured_output()** | Type-safe, schema-constrained — never JsonOutputParser |
| Validation | **Deterministic Python** | Objective checks must be 100% reproducible for audit |
| Database | **SQLite** (`inventory.db` + `paid_invoices`) | Local, no server, parameterised queries |
| PDF parsing | **MarkItDown → pdfplumber fallback** | 30-70% token reduction, pdfplumber for complex tables |
| Checkpointing | **SqliteSaver** (≥3.0.1, CVE-patched) | Durable, resumable runs, thread per invoice |
| UI | **Streamlit** | Fast to build, 3-tab dashboard, proven layout |
| Testing | **pytest** | One test per scenario, parametrized |

**Security note:** `langgraph-checkpoint-sqlite>=3.0.1` is mandatory (CVE-2025-67644 SQL injection fix). All SQL uses parameterised `?` placeholders — never f-strings.

---

## 6. Project Structure

```
invoice-agents/
├── main.py                          # CLI entry: --invoice_path, --setup
├── setup_db.py                      # Seeds inventory.db (official data + extensions)
├── streamlit_app.py                 # 3-tab UI
├── requirements.txt
├── .env.example
├── langgraph.json
├── Dockerfile
├── CLAUDE.md                        # Claude Code rules
├── PLAN.md                          # this file
├── IMPLEMENTATION_SPEC.md           # detailed code spec
├── TESTPLAN.md                      # test cases
├── COMPARATIVE_STUDY.md             # data corrections
│
├── src/invoice_agents/
│   ├── state.py                     # InvoiceState + Pydantic models
│   ├── llm.py                       # LLM factory (swappable)
│   ├── graph.py                     # Parent StateGraph wiring
│   ├── agents/
│   │   ├── ingestion/
│   │   │   ├── agent.py             # ingestion sub-graph
│   │   │   ├── parsers.py           # 6 format parsers
│   │   │   └── extractor.py         # LLM extraction + retry
│   │   ├── validation/
│   │   │   ├── agent.py             # validation sub-graph
│   │   │   ├── db.py                # parameterised SQLite
│   │   │   └── flags.py             # 10 flag types + compute_flags
│   │   ├── approval/
│   │   │   ├── agent.py             # approval sub-graph (3 branches)
│   │   │   ├── generator.py         # LLM Generator
│   │   │   ├── critic.py            # LLM Critic
│   │   │   └── rules.py             # thresholds + rule_based_approve
│   │   └── payment/
│   │       ├── agent.py             # payment sub-graph
│   │       └── mock_api.py          # mock_payment + transaction_id
│   └── utils/
│       ├── logging.py               # structured LogEntry
│       └── errors.py                # custom exceptions
│
├── data/
│   ├── invoices/                    # 20 official files (+ .md conversions of PDFs)
│   └── inventory.db                 # gitignored, created by setup_db.py
│
└── tests/
    ├── test_ingestion.py
    ├── test_validation.py
    ├── test_approval.py
    └── test_end_to_end.py           # one test per invoice
```

---

## 7. State Design

```python
class InvoiceState(TypedDict):
    # CLI sets
    invoice_path: str
    run_id: Optional[str]

    # Ingestion writes
    raw_text: Optional[str]
    extracted_invoice: Optional[dict]      # Invoice model serialised
    ingestion_error: Optional[str]

    # Validation writes (operator.add — APPENDS)
    validation_flags: Annotated[list[dict], operator.add]

    # Approval writes
    approval_decision: Optional[str]       # "APPROVE" | "REJECT" (exact strings)
    approval_reasoning: Optional[str]
    reflection_count: int                  # default 0, capped at 3
    _draft_decision: Optional[dict]        # internal to approval sub-graph
    _critique_verdict: Optional[str]       # internal
    _last_critique: Optional[str]          # internal

    # Payment writes
    payment_result: Optional[dict]
    rejection_log: Optional[dict]

    # Audit (operator.add — APPENDS)
    steps_taken: Annotated[list[str], operator.add]
```

**Pydantic models:** `LineItem`, `Invoice` (with currency, subtotal, total), `ApprovalDecision`, `CritiqueResult`.

**Non-negotiable state rules:**
1. Never mutate state in-place — return new dicts from nodes.
2. `validation_flags` and `steps_taken` use `operator.add` — returning them APPENDS, not overwrites.
3. Every node returns `{"steps_taken": ["node_name"]}`.
4. `approval_decision` is exactly `"APPROVE"` or `"REJECT"` — payment router does strict `== "APPROVE"`.

---

## 8. The Four Agents

### Agent 1 — Ingestion
- **Format router** by extension → 6 parsers (TXT, JSON, CSV×2, PDF, XML)
- **LLM extraction** via `with_structured_output(Invoice)` with prompt handling: OCR fix, name normalisation, currency detection, subtotal+total extraction, email header stripping, fraud signal flagging
- **Retry loop**: 3 attempts, inject error into context on failure
- Writes `extracted_invoice` to state

### Agent 2 — Validation (deterministic, no LLM)
Order of operations in `compute_flags()`:
1. Empty vendor / negative amount → DATA_INTEGRITY_ERROR
2. Duplicate invoice_id check → DUPLICATE_INVOICE
3. **Aggregate quantities by item name** (critical for INV-1010, INV-1013)
4. Per aggregated item: UNKNOWN_ITEM / ZERO_STOCK_SUSPICIOUS / STOCK_MISMATCH / NEGATIVE_QTY
5. Total reconciliation → TOTAL_MISMATCH
6. Currency check → FOREIGN_CURRENCY
7. Fuzzy match fallback for near-miss item names
- Writes `validation_flags` to state

### Agent 3 — Approval (reflection loop — the differentiator)
Three-way entry router:
- **Branch A** (blocking flags present): immediate REJECT, zero LLM calls
- **Branch B** (amount >$10K, no blocking flags): Generator→Critic reflection loop
  - Generator produces draft ApprovalDecision
  - Critic returns ACCEPT or REVISE
  - REVISE + count<3 → loop back; ACCEPT or count≥3 → finalise
- **Branch C** (amount ≤$10K, no flags): rule_based_approve, zero LLM calls
- Writes `approval_decision`, `approval_reasoning`, `reflection_count`

### Agent 4 — Payment
- Entry router: `approval_decision == "APPROVE"` → pay, else → reject
- **Pay node**: `mock_payment()` returns `{status, transaction_id}`, then `deduct_stock()` per item, then `record_payment()` for duplicate guard
- **Reject node**: structured `rejection_log` with invoice_id, flags, reasoning
- Writes `payment_result` or `rejection_log`

---

## 9. Routing Logic

| Decision point | Condition | Routes to |
|----------------|-----------|-----------|
| Approval entry | `len(validation_flags) > 0` | Branch A (reject) |
| Approval entry | `amount > 10000 AND flags == []` | Branch B (reflection) |
| Approval entry | `amount <= 10000 AND flags == []` | Branch C (rule approve) |
| Critique exit | `verdict == ACCEPT OR count >= 3` | finalise |
| Critique exit | `verdict == REVISE AND count < 3` | loop to generator |
| Payment entry | `approval_decision == "APPROVE"` | pay |
| Payment entry | `approval_decision == "REJECT"` | reject log |

**Branch priority:** blocking flags ALWAYS win over amount threshold. A $5K invoice with a fraud flag goes to Branch A, not Branch C.

---

## 10. Build Sequence

**One phase = one Claude Code session = one commit.** Models per phase optimise cost.

| Phase | Scope | Model | Milestone |
|-------|-------|-------|-----------|
| 1 | Scaffold, setup_db, 6 parsers | Haiku | `python setup_db.py` works; parsers read all 20 files |
| 2 | InvoiceState, Pydantic models, LLM factory, flag types | Sonnet | All imports succeed, types validate |
| 3 | Ingestion sub-graph + extraction + retry | Sonnet | Extracts INV-1001, INV-1012 (OCR) correctly |
| 4 | Validation sub-graph + 10 flags + aggregation | Sonnet | All 5 README scenarios flag correctly |
| 5 | Approval sub-graph + reflection loop | **Opus** | All 3 branches work; reflection_count tracks |
| 6 | Payment + graph wiring + CLI | Sonnet | End-to-end: all 4 demo invoices route correctly |
| 7 | Streamlit UI (3 tabs) | Sonnet | Upload → process → display works |
| 8 | Docs, Dockerfile, README, final tests | Haiku | All 8 test scenarios pass |

Estimated total cost with optimization stack: ~$4-6.

---

## 11. Definition of Done

The project is complete when ALL of these are true:

**Functionality**
- [ ] `python main.py --setup` creates and seeds inventory.db
- [ ] `python main.py --invoice_path=X` runs end-to-end for all 20 official invoices
- [ ] Each invoice routes to its correct outcome (see Section 4.2 table)
- [ ] Structured JSON log printed for every run (PAID or REJECTED with reasons)

**Agentic sophistication**
- [ ] 4 sub-graphs wired into parent StateGraph
- [ ] Reflection loop runs for >$10K invoices (verify reflection_count > 0)
- [ ] Reflection loop caps at 3 iterations (no infinite loops)
- [ ] Extraction uses with_structured_output (not JsonOutputParser)
- [ ] Extraction retries 3× on failure
- [ ] Branch A and Branch C make zero LLM calls

**Edge cases (all 14 from Section 4.3)**
- [ ] Quantity aggregation works (INV-1010, INV-1013)
- [ ] Total reconciliation catches INV-1013 $50 overcharge
- [ ] OCR artifacts normalised (INV-1012)
- [ ] Duplicate detection works (INV-1004_revised)
- [ ] Foreign currency flagged (INV-1014)
- [ ] Negative qty/amount caught (INV-1009)
- [ ] Empty vendor caught (INV-1009)
- [ ] All 6 formats parse (TXT, JSON, CSV×2, PDF, XML)
- [ ] Stock deducted after payment

**Code quality**
- [ ] All SQL uses parameterised ? placeholders
- [ ] State never mutated in-place
- [ ] Type hints on all function signatures
- [ ] pytest suite passes (one test per scenario)
- [ ] Error handling on every node

**Delivery**
- [ ] Streamlit UI runs and processes invoices
- [ ] docs/presentation.md with business framing
- [ ] README.md with setup + run instructions
- [ ] Dockerfile builds

---

## 12. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LLM extraction non-deterministic | High | Medium | temperature=0, keep validation deterministic, log confidence |
| Reflection loop infinite | Medium | High | MAX_REFLECTION_ITERATIONS=3 hard cap in router |
| SQL injection via item names | Low | High | Parameterised queries only, never f-strings |
| Quantity aggregation missed | Medium | High | Explicit test for INV-1010, INV-1013 in TESTPLAN |
| Wrong inventory data | Low | Critical | Use official seed (WidgetA=15, WidgetB=10, GadgetX=5, FakeItem=0) |
| PDF parsing fails | Medium | Medium | MarkItDown primary, pdfplumber fallback |
| Context bloat in Claude Code | High | Medium | One agent per session, /compact at 75% |
| Currency comparison wrong | Medium | Medium | Extract currency field, flag non-USD |
| Over-engineering | Medium | Medium | Ponytail skill, Branch C avoids LLM, scope ruthlessly |

---

## Quick Start (in a fresh workspace)

```bash
# 1. Clone official test data
git clone --depth 1 https://github.com/galatiq-ai/galatiq-case-invoices.git /tmp/off
cp -r /tmp/off/data ./data

# 2. Pre-convert PDFs to Markdown (token savings)
pip install 'markitdown[all]'
python3 -c "from markitdown import MarkItDown; from pathlib import Path; md=MarkItDown(); [Path(p).with_suffix('.md').write_text(md.convert(str(p)).text_content) for p in Path('data/invoices').glob('*.pdf')]"

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up the database
python main.py --setup

# 5. Build (follow Phase 1-8 in Section 10, one session each)

# 6. Run
python main.py --invoice_path=data/invoices/invoice_1001.txt
streamlit run streamlit_app.py
```
