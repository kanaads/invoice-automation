# Invoice Processing Automation

A multi-agent LangGraph pipeline that automates invoice processing end-to-end: **Ingestion → Validation → Approval → Payment**. Built for the Galatiq/Acme Corp case study (see `docs/PLAN.md` for the full spec).

## Setup

```bash
# 1. Install dependencies
.venv/bin/pip install -r requirements.txt

# 2. Configure an LLM backend in .env (LLM_BACKEND=groq|gemini|xai|openai|anthropic|ollama|bedrock)
cp .env.example .env   # then fill in the relevant API key(s)

# 3. Seed the inventory database
.venv/bin/python main.py --setup

# 4. Run any invoice
.venv/bin/python main.py --invoice_path=data/invoices/invoice_1001.txt
```

## Architecture

```
CLI (main.py)
   └─► Orchestrator (src/invoice_agents/graph.py)
         ├─► Ingestion   — format router (6 parsers) → LLM structured extraction, 3× retry
         ├─► Validation  — deterministic SQL + Python checks, zero LLM calls
         ├─► Approval    — 3-way router: blocking-reject / reflection loop / rule-approve
         └─► Payment     — mock payment → stock deduction → audit record
```

Each stage is its own compiled LangGraph sub-graph (`src/invoice_agents/agents/*/agent.py`), independently testable. Full test suite: `.venv/bin/python -m pytest tests/ -v` (90 tests).

## Scope & Assumptions

Deliberate cuts, so scope is explicit rather than something to infer from the code:

- **CLI-only.** No web UI — `main.py` is the only interface. `streamlit` is in
  `requirements.txt` but unused; adding a UI is future work, not part of this MVP.
- **Single SQLite file, no concurrency handling.** `data/inventory.db` assumes one
  process at a time; there's no locking/retry strategy for concurrent writers.
- **Payment is a mock API.** `agents/payment/mock_api.py` simulates a successful
  payment call — no real payment gateway integration.
- **No invoice-revision/versioning support.** A resubmitted invoice with the same
  `invoice_id` is flagged `DUPLICATE_INVOICE` and rejected outright, even if it's a
  legitimate correction (see `docs/DATA_MODEL.md`'s note on this — adding a
  `revision` column was explicitly out of scope for this assignment).
- **LLM backend is swappable but only one is exercised by default.** `LLM_BACKEND`
  supports `groq|gemini|xai|openai|anthropic|ollama|bedrock` (`src/invoice_agents/llm.py`),
  but CI/local runs default to `groq`; the others aren't continuously verified.

---

## Demo: 4 corner-case scenarios

These are the four edge cases most worth walking an interviewer through — each one demonstrates a specific design decision, not just "does it work end-to-end."

**Before each scenario below, reset the database** so scenarios don't interfere with each other (payment deducts real stock):

```bash
rm -f data/inventory.db && .venv/bin/python main.py --setup
```

### 1. Quantity aggregation across split line items

**Command:**
```bash
.venv/bin/python main.py --invoice_path=data/invoices/invoice_1013.json
```

**What it demos:** INV-1013 orders `WidgetA` on *three separate lines* (15 + 5 + 2 units). Stock for WidgetA is 15. Each individual line is ≤15, so a naive "check each line against stock" validator would **pass this invoice**. My validator aggregates by item name *before* comparing to stock, catching the real total (22 > 15) — plus a second, independent issue: the stated total ($22,562.80) doesn't reconcile with subtotal+tax ($22,512.80), a $50 gap.

**Reasoning:** Real invoices split identical items across lines (bulk discount rows, rush-order add-ons, etc.). Validating line-by-line is the obvious-but-wrong implementation; aggregating first is what actually matches how inventory depletes in the real world.

**Code:** `src/invoice_agents/agents/validation/flags.py::aggregate_quantities()` groups by item name and sums *before* `compute_flags()` does any stock comparison. Same aggregated map is reused later by `payment/agent.py::_pay_node()` when deducting stock, so validation and deduction can never disagree about "how many of X was this invoice for."

**Expected result:** `REJECTED`, flags include `STOCK_MISMATCH` (×3 items) and `TOTAL_MISMATCH`.

---

### 2. The reflection loop (Generator → Critic) — the assignment's explicit differentiator

None of the 20 official invoices happen to be both clean *and* over $10K (the ones over $10K all have a stock issue), so I added one small synthetic fixture to actually exercise this path live.

**Command:**
```bash
.venv/bin/python main.py --invoice_path=data/invoices/invoice_9001_demo_highvalue.txt
```

**What it demos:** A clean $11,500 invoice (over the $10K threshold, no validation flags) routes to a **Generator → Critic loop**: an LLM drafts an APPROVE/REJECT decision with reasoning, a second LLM call critiques that draft (ACCEPT or REVISE), and only an ACCEPT (or hitting the iteration cap) finalizes the decision. `reflection_count` in the output tells you how many rounds it took.

**Reasoning:** The assignment explicitly names a "reflection or critique loop" as a requirement, not just an LLM call. A single LLM call can't self-correct; a second independent pass that's specifically prompted to be skeptical can catch weak reasoning before it becomes an audit trail. I capped it at 3 iterations (`MAX_REFLECTION_ITERATIONS` in `rules.py`) so a stubborn critic can't loop forever — verified by a test that force-monkeypatches the critic to always return REVISE and confirms the loop still terminates.

**Code:** `src/invoice_agents/agents/approval/agent.py` — `_generate_node` → `_critique_node` → conditional edge (`_critique_router`) either loops back to `generate` or moves to `finalize`. Branches A (blocking flags) and C (≤$10K clean) skip this entirely and make **zero LLM calls** — the reflection loop only runs where judgment genuinely matters.

**Expected result:** `PAID`, `steps_taken` includes `generate, critique, finalize`, `reflection_count >= 1`.

---

### 3. Fraud / social-engineering detection

**Command:**
```bash
.venv/bin/python main.py --invoice_path=data/invoices/invoice_1003.txt
```

**What it demos:** INV-1003 is a fabricated invoice for 100 units of `FakeItem` ($100,000 total) from "Fraudster LLC," with urgency language ("Pay immediately to avoid penalties!!!"), a preference for wire transfer, and a due date of "yesterday." The extraction step doesn't just pull vendor/amount/items — it's explicitly prompted to notice social-engineering patterns and surface them as `fraud_signals`, which validation then turns into blocking `FRAUD_SIGNAL` flags. Separately, `FakeItem` is a real row in the inventory DB seeded at zero stock specifically as a fraud sentinel — so even without the language cues, ordering it trips `ZERO_STOCK_SUSPICIOUS`.

**Reasoning:** The README's brief only asks for "flag items not in inventory or out of stock" — treating suspicious *language* as a first-class signal is deliberately going beyond that, because in the real world (per the assignment's own framing: 30% error rate, frequent fraud) the content of the invoice, not just its numbers, is a fraud signal.

**Code:** `extractor.py`'s system prompt instructs the LLM to populate `fraud_signals` on the `Invoice` model; `flags.py::compute_flags()` converts each into a blocking `FRAUD_SIGNAL` flag (last block in the function).

**Expected result:** `REJECTED`, flags include `ZERO_STOCK_SUSPICIOUS` and multiple `FRAUD_SIGNAL` entries.

---

### 4. Stateful duplicate-invoice detection (double-payment prevention)

**Command (run in this order, same database):**
```bash
.venv/bin/python main.py --invoice_path=data/invoices/invoice_1004.json           # pays first
.venv/bin/python main.py --invoice_path=data/invoices/invoice_1004_revised.json   # same invoice_id, rejected
```

**What it demos:** `invoice_1004_revised.json` carries the *same* `invoice_number` (`INV-1004`) as the original, just with an extra line item and a `"revision": "R1"` tag — a real-world pattern for a resubmitted/amended invoice. Because the first run already wrote a `paid_invoices` row for `INV-1004`, the second run's validation queries that table and finds it, flagging `DUPLICATE_INVOICE` and rejecting outright — regardless of the amount or how clean the revised line items are.

**Reasoning:** This is explicitly **stateful** — it can only be demonstrated with the two commands run in sequence against the same DB, not with either invoice in isolation (a detail worth calling out, since it's easy to write a test that accidentally checks each file independently and never actually exercises this path). Preventing double payment on a resubmitted invoice is one of the concrete business failure modes the $2M/year manual-process cost described in the assignment is actually about.

**Code:** `agents/validation/db.py::check_duplicate()` — a parameterized `SELECT 1 FROM paid_invoices WHERE invoice_id = ?` — called from `flags.py::compute_flags()` before any other check. `agents/payment/agent.py::_pay_node()` writes the `paid_invoices` row via `record_payment()` only on a successful payment, which is what makes the second call's lookup succeed.

**Expected result:** first call → `PAID`; second call → `REJECTED` with `DUPLICATE_INVOICE`.

---

## Full regression check

```bash
.venv/bin/python -m pytest tests/ -v
```

90 tests: unit (parsers, DB, flags, rules), integration (each sub-graph), and end-to-end (all 20 official invoices + the stateful duplicate test).
