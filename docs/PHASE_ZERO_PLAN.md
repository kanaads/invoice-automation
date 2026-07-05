# Phase 0 — Claude Code Development Plan

## Token Optimization · Essential Skills · Docs · Development Phases

> **Purpose:** This document is your pre-flight checklist before writing a single line of code. It sets up the Claude Code environment for maximum cost efficiency, lists every skill/doc/reference needed, and provides a phased build plan designed for Claude Code's agentic workflow.

---

## Table of Contents

1. [Token Optimization Stack](#1-token-optimization-stack)
2. [CLAUDE.md Rules File](#2-claudemd-rules-file)
3. [Essential Skills & Docs Reference Library](#3-essential-skills--docs-reference-library)
4. [Model Strategy](#4-model-strategy)
5. [Pre-Processing Hooks & Enforcement](#5-pre-processing-hooks--enforcement)
6. [Phased Development Plan](#6-phased-development-plan)
7. [Session Management Protocol](#7-session-management-protocol)
8. [Cost Budget Estimation](#8-cost-budget-estimation)

---

## 1. Token Optimization Stack

Install these **before** starting development. Order matters — each layer reduces what the next layer sees.

### Layer 1: Graphify — Codebase Knowledge Graph (navigation: up to 70× savings)

**What:** Builds a tree-sitter AST-based knowledge graph of your codebase. Claude navigates the graph instead of re-reading files.

**Why for this project:** The invoice-agents project will grow to ~20 files across 4 agent packages. Without Graphify, Claude re-reads the full directory tree on every prompt. With it, a single graph lookup replaces 6–8 Glob/Grep calls.

```bash
pip install graphify-ai
graphify install --platform claude
# Creates ~/.claude/skills/graphify/SKILL.md
# Run after each significant structural change:
graphify build --project ./invoice-agents
```

**Key setting:** Use `--deep` mode for semantic edges (uses LLM, costs tokens) only on initial build. Incremental rebuilds use SHA256 cache and cost zero tokens.

**Reference:** [https://github.com/lucasrosati/claude-code-memory-setup](https://github.com/lucasrosati/claude-code-memory-setup)

---

### Layer 2: Codebase Memory MCP (CBM) — Code Discovery Gate (discovery: 99% savings)

**What:** An MCP server that maintains a persistent knowledge graph of your codebase. Claude queries the graph before touching any file.

**Why for this project:** Prevents Claude from using `cat`, `grep`, `Read` on source files to find where `compute_flags()` or `InvoiceState` is defined. One CBM query returns the location, its dependencies, and its callers.

```bash
# CBM installs via the claude-code-tips stack (see Layer 5)
# Or standalone:
npm install -g @deusdata/codebase-memory-mcp
```

**Enforcement:** The `cbm-code-discovery-gate` hook blocks `Grep`, `Glob`, and `Read` on source directories until CBM has been called at least once in the session.

---

### Layer 3: context-mode — Output Virtualisation (large outputs: 98% savings)

**What:** A Claude Code plugin that sandboxes large tool outputs. Instead of injecting a 10,000-line test output into context, it writes to a virtual file and hands Claude a 200-token summary.

**Why for this project:** Running `pytest` or `python main.py --invoice_path=...` produces multi-line structured JSON logs. Without context-mode, every test run bloats context. With it, Claude gets a summary and can request specific sections on demand.

```bash
claude plugin install mksglu/context-mode
```

**How it works:** Hooks into `PreToolUse`, `PostToolUse`, `PreCompact`, and `SessionStart`. Large outputs are written to `.context-mode/` and a compressed reference is injected instead.

**Reference:** [https://github.com/mksglu/context-mode](https://github.com/mksglu/context-mode)

---

### Layer 4: RTK — Shell Output Compression (CLI output: 60–90% savings)

**What:** A Rust binary that intercepts shell commands and compresses their output before it enters context. `git status` → `rtk git status`. Same semantics, 60–90% fewer tokens.

**Why for this project:** We'll run `pip install`, `python setup_db.py`, `pytest`, `python main.py` frequently. Each run produces verbose output. RTK filters it to the signal.

```bash
# RTK is bundled with Headroom (see Layer 5)
# Standalone: cargo install rtk-ai
```

**Savings by command type:**

- `pip install` output: ~90% reduction
- `pytest` output: ~85% (keeps only PASS/FAIL + error traces)
- `git diff`: ~70% (removes decorative headers, alignment spaces)
- `python main.py`: ~60% (keeps structured JSON output, drops print noise)

---

### Layer 5: Headroom — API-Layer Proxy (all traffic: 47–92% savings)

**What:** A local proxy (localhost:8787) between Claude Code and the Anthropic API. Compresses tool results, leverages prefix caching, reduces every API request.

**Why for this project:** This is the final compression layer. Everything that survives Layers 1–4 still gets compressed before hitting the API. JSON arrays (our structured logs): 83–90% compression. Build logs: 94%.

```bash
pip install "headroom-ai[all]"
headroom wrap claude
# Now every `claude` invocation routes through the proxy
# Undo: headroom unwrap claude
```

**Desktop app (macOS):** Headroom Desktop provides a menu bar UI showing daily/monthly savings charts and per-client token stats.

**Reference:** [https://github.com/chopratejas/headroom](https://github.com/chopratejas/headroom)

---

### Layer 6: Ponytail — Output Token Reduction (code generation: 54% less code)

**What:** A skill/plugin that makes Claude write minimal, boring, correct code. Installs a "lazy senior developer" decision ladder: does this need to exist? Is it in the standard library? Can it be one line?

**Why for this project:** Our invoice-agents project has clear boundaries — each agent does one thing. Ponytail prevents Claude from over-engineering (no speculative abstractions, no scaffolding "for later"). Measured: 54% less code, 20% cheaper, 27% faster, 100% safe.

```bash
# Claude Code:
/plugin marketplace add DietrichGebert/ponytail
/plugin install ponytail@ponytail

# Or via Headroom Add-ons (toggle on from the UI)
```

**Modes:**

- `lite` — gentle nudge, skip on trivial tasks
- `full` — default, always-on YAGNI ladder (recommended for this project)
- `ultra` — aggressive, for when the codebase has wronged you personally

**Reference:** [https://github.com/DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail)

---

### Layer 7: Caveman — Claude Output Compression (Claude's prose: 50–75% savings)

**What:** A plugin that makes Claude respond concisely. Strips ceremony, restated code, and verbose explanations. "why use many token when few token do trick."

**Why for this project:** During development, we want Claude to write code, not explain what it's about to do. Caveman cuts prose output by 50–75%.

```bash
claude plugin install JuliusBrussee/caveman
# Activate in session: /caveman
```

**Caveat:** Caveman + Ponytail together can make responses TOO terse. Use Caveman for coding sessions and disable it for architecture/planning sessions.

**Reference:** [https://github.com/JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman)

---

### One-Click Install (All Layers)

The `sgaabdu4/claude-code-tips` repo bundles all 7 layers with a single installer:

```bash
git clone https://github.com/sgaabdu4/claude-code-tips.git
cd claude-code-tips
chmod +x install.sh && ./install.sh
```

**Result:** Sessions stretch from ~30 minutes to 3+ hours on the same 200K context window. Combined savings: 90%+ token reduction.

---

## 2. CLAUDE.md Rules File

Create this file at the project root. Claude Code reads it at session start.

```markdown
# CLAUDE.md — Invoice Processing Agent Project Rules

## Project Context
Building a LangGraph multi-agent invoice processing system.
4 sub-graphs: Ingestion → Validation → Approval → Payment.
Refer to IMPLEMENTATION_SPEC.md for ALL architecture decisions.
Refer to COMPARATIVE_STUDY.md for test data mapping.

## Code Standards
- Python 3.10+. Type hints on ALL function signatures.
- Pydantic v2 for models. TypedDict for LangGraph state.
- NEVER use f-strings in SQL. Always parameterised queries with ?.
- NEVER mutate LangGraph state in-place. Return new dicts from nodes.
- All node functions must include `"steps_taken": ["node_name"]` in return dict.
- Use `with_structured_output()` — never `JsonOutputParser`.
- Max function length: 30 lines. Extract helpers if longer.
- Every file has a module docstring explaining what it does.

## File Reading Protocol
- ALWAYS use Graphify/CBM before reading source files.
- When looking for a function: query the graph first, then read only the relevant file.
- When running tests: use `pytest -x --tb=short` to minimize output.
- NEVER `cat` an entire file to find one function.

## LangGraph Rules
- State type: TypedDict (NOT Pydantic BaseModel for graph state).
- Reducers: operator.add for list fields (validation_flags, steps_taken).
- Sub-graphs: each agent is a compiled StateGraph added as a node.
- Conditional edges: use the routing table in IMPLEMENTATION_SPEC.md Section 11.
- Reflection loop: MUST have bounded counter (max 3 iterations).

## Testing Rules
- One test per README scenario (see test matrix in spec).
- Test command: `pytest tests/ -x --tb=short -q`
- Expected outcomes are in IMPLEMENTATION_SPEC.md Section 14.

## Session Management
- Start EVERY session by running: `graphify query --summary`
- Before switching files: check what's already in context with /context.
- Compact context before it reaches 80%: /compact.
- One agent per session. Don't build all 4 in one context window.
```

---

## 3. Essential Skills & Docs Reference Library

### 3.1 LangGraph (Primary Framework)


| Resource                   | URL                                                                                                                                                                                    | When to use                                      |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| **LangGraph Concepts**     | [https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph](https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph)                                         | Before starting — understand nodes, edges, state |
| **StateGraph API**         | [https://docs.langchain.com/oss/python/langgraph/reference/graphs](https://docs.langchain.com/oss/python/langgraph/reference/graphs)                                                   | When building graph.py — exact API signatures    |
| **Sub-graphs**             | [https://docs.langchain.com/oss/python/langgraph/use-subgraphs](https://docs.langchain.com/oss/python/langgraph/use-subgraphs)                                                         | When wiring sub-graphs as nodes                  |
| **Conditional Edges**      | [https://docs.langchain.com/oss/python/langgraph/concepts/conditional-edges](https://docs.langchain.com/oss/python/langgraph/concepts/conditional-edges)                               | When implementing routing logic                  |
| **Checkpointer (SQLite)**  | [https://docs.langchain.com/oss/python/langgraph/persistence](https://docs.langchain.com/oss/python/langgraph/persistence)                                                             | When adding SqliteSaver                          |
| **RetryPolicy**            | [https://www.langchain.com/blog/fault-tolerance-in-langgraph](https://www.langchain.com/blog/fault-tolerance-in-langgraph)                                                             | When adding error handling to payment node       |
| **Human-in-the-Loop**      | [https://docs.langchain.com/oss/python/langgraph/concepts/human-in-the-loop](https://docs.langchain.com/oss/python/langgraph/concepts/human-in-the-loop)                               | For interrupt() on high-value approvals          |
| **Multi-Agent Supervisor** | [https://reference.langchain.com/python/langgraph-supervisor](https://reference.langchain.com/python/langgraph-supervisor)                                                             | Architecture pattern reference                   |
| **Command primitive**      | [https://blog.langchain.com/command-a-new-tool-for-multi-agent-architectures-in-langgraph/](https://blog.langchain.com/command-a-new-tool-for-multi-agent-architectures-in-langgraph/) | For state updates + routing in one step          |


### 3.2 LangChain (LLM Integration)


| Resource                  | URL                                                                                                                                              | When to use                                                 |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------- |
| **Structured Output**     | [https://docs.langchain.com/oss/python/langchain-core/structured-output](https://docs.langchain.com/oss/python/langchain-core/structured-output) | For `with_structured_output()` on Invoice, ApprovalDecision |
| **ChatXAI (Grok)**        | [https://pypi.org/project/langchain-xai/](https://pypi.org/project/langchain-xai/)                                                               | For LLM factory setup                                       |
| **ChatOpenAI (fallback)** | [https://docs.langchain.com/oss/python/langchain-openai/](https://docs.langchain.com/oss/python/langchain-openai/)                               | When Grok key unavailable                                   |
| **Prompt Templates**      | [https://docs.langchain.com/oss/python/langchain-core/prompts](https://docs.langchain.com/oss/python/langchain-core/prompts)                     | For extraction + approval prompts                           |
| **Tool Calling**          | [https://docs.langchain.com/oss/python/langchain-core/tools](https://docs.langchain.com/oss/python/langchain-core/tools)                         | For function/tool use                                       |


### 3.3 SQLite (Inventory Database)


| Resource                     | URL                                                                                                                                                                                  | When to use                                    |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------- |
| **Python sqlite3 docs**      | [https://docs.python.org/3/library/sqlite3.html](https://docs.python.org/3/library/sqlite3.html)                                                                                     | For parameterised queries                      |
| **SQL Injection Prevention** | [https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html) | Security reference — always use ? placeholders |


### 3.4 PDF/Document Parsing


| Resource                  | URL                                                                                                                          | When to use                        |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| **pdfplumber**            | [https://github.com/jsvine/pdfplumber](https://github.com/jsvine/pdfplumber)                                                 | For PDF text + table extraction    |
| **PyMuPDF (fitz)**        | [https://pymupdf.readthedocs.io/](https://pymupdf.readthedocs.io/)                                                           | For PDF fallback + scanned pages   |
| **xml.etree.ElementTree** | [https://docs.python.org/3/library/xml.etree.elementtree.html](https://docs.python.org/3/library/xml.etree.elementtree.html) | For XML invoice parsing (INV-1014) |


### 3.5 Pydantic v2 (Data Models)


| Resource               | URL                                                                                                    | When to use                                           |
| ---------------------- | ------------------------------------------------------------------------------------------------------ | ----------------------------------------------------- |
| **Pydantic v2 docs**   | [https://docs.pydantic.dev/latest/](https://docs.pydantic.dev/latest/)                                 | For Invoice, ApprovalDecision, CritiqueResult models  |
| **Field descriptions** | [https://docs.pydantic.dev/latest/concepts/fields/](https://docs.pydantic.dev/latest/concepts/fields/) | Critical — descriptions are injected into LLM prompts |


### 3.6 Streamlit (UI)


| Resource             | URL                                                                                                                                                  | When to use               |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------- |
| **Streamlit API**    | [https://docs.streamlit.io/](https://docs.streamlit.io/)                                                                                             | Phase 4 — building the UI |
| **st.tabs**          | [https://docs.streamlit.io/develop/api-reference/layout/st.tabs](https://docs.streamlit.io/develop/api-reference/layout/st.tabs)                     | For the 3-tab layout      |
| **st.file_uploader** | [https://docs.streamlit.io/develop/api-reference/widgets/st.file_uploader](https://docs.streamlit.io/develop/api-reference/widgets/st.file_uploader) | For invoice upload        |


### 3.7 Testing


| Resource            | URL                                                                                                              | When to use               |
| ------------------- | ---------------------------------------------------------------------------------------------------------------- | ------------------------- |
| **pytest**          | [https://docs.pytest.org/](https://docs.pytest.org/)                                                             | For all tests             |
| **pytest fixtures** | [https://docs.pytest.org/en/stable/how-to/fixtures.html](https://docs.pytest.org/en/stable/how-to/fixtures.html) | For shared graph/DB setup |


---

## 4. Model Strategy

Use different models for different tasks to minimize cost.


| Task                                       | Model      | Why                                                      | Est. cost/task |
| ------------------------------------------ | ---------- | -------------------------------------------------------- | -------------- |
| Architecture planning, complex debugging   | Opus 4.6   | Best reasoning, worth the cost for architecture          | $0.50–1.00     |
| Writing agent code, sub-graphs             | Sonnet 4.6 | Best balance of quality/cost for coding                  | $0.10–0.30     |
| Boilerplate, setup scripts, parsers, tests | Haiku 4.5  | 15× cheaper than Opus, more than capable for simple code | $0.01–0.05     |
| Code review, refactoring                   | Sonnet 4.6 | Needs to understand context across files                 | $0.10–0.20     |


**Claude Code model switching:**

```bash
# In session:
/model sonnet    # Switch to Sonnet for coding
/model haiku     # Switch to Haiku for boilerplate
/model opus      # Switch to Opus for complex reasoning

# Or set default in ~/.claude/settings.json:
{ "model": "sonnet", "effortLevel": "high" }
```

**Effort levels:**

- `low` — for simple edits, file creation (saves ~30% tokens)
- `medium` — default for coding tasks
- `high` — for complex reasoning, debugging, architecture

---

## 5. Pre-Processing Hooks & Enforcement

### 5.1 bash-ban-raw-tools Hook

Blocks Claude from using raw `cat`, `head`, `tail`, `find`, `grep`, `wc` in bash. Forces use of CBM/Graphify for code discovery and Read tool for targeted file access.

```json
// In ~/.claude/settings.json hooks section
{
  "type": "PreToolUse",
  "tool_name": "Bash",
  "script": "~/.claude/hooks/bash-ban-raw-tools"
}
```

### 5.2 Test Output Filtering Hook

A custom PostToolUse hook that compresses test output before it enters context:

```bash
#!/bin/bash
# ~/.claude/hooks/filter-test-output
# PostToolUse hook for Bash — compress pytest/python output

if echo "$TOOL_INPUT" | grep -qE "pytest|python main.py"; then
  echo "$TOOL_OUTPUT" | grep -A5 -E "FAIL|ERROR|PASS|REJECT|PAID|assert" | head -100
fi
```

### 5.3 SQL Safety Hook

A PreToolUse hook that blocks any bash command containing f-string SQL patterns:

```bash
#!/bin/bash
# ~/.claude/hooks/sql-safety-gate
# Blocks f-string SQL patterns

if echo "$TOOL_INPUT" | grep -qE 'f".*SELECT|f".*INSERT|f".*UPDATE|\.format\(.*SELECT'; then
  echo "BLOCKED: SQL query uses f-string interpolation. Use parameterised queries with ? placeholders."
  exit 1
fi
```

---

## 6. Phased Development Plan

### Phase 1 — Scaffold + DB + Parsers (Session 1, ~45 min)

**Model:** Haiku 4.5 (boilerplate)
**Effort:** low


| Step | Task                                             | Files created                        |
| ---- | ------------------------------------------------ | ------------------------------------ |
| 1.1  | Create full directory structure                  | All `__init__.py`, empty agent files |
| 1.2  | Write `requirements.txt`                         | requirements.txt                     |
| 1.3  | Write `setup_db.py` with official seed data      | setup_db.py                          |
| 1.4  | Write all 5 parsers (TXT, JSON, CSV×2, XML)      | parsers.py                           |
| 1.5  | Write PDF parser (pdfplumber + PyMuPDF fallback) | parsers.py                           |
| 1.6  | Test parsers against all 20 official invoices    | Manual verification                  |


**Session end:** `/compact`, commit to git, run `graphify build`.

### Phase 2 — State + Models + LLM Factory (Session 2, ~30 min)

**Model:** Sonnet 4.6 (needs to understand Pydantic + TypedDict correctly)
**Effort:** medium


| Step | Task                                                                        | Files created    |
| ---- | --------------------------------------------------------------------------- | ---------------- |
| 2.1  | Write `InvoiceState` TypedDict with all fields + reducers                   | state.py         |
| 2.2  | Write Pydantic models (Invoice, LineItem, ApprovalDecision, CritiqueResult) | state.py         |
| 2.3  | Write `llm.py` factory (ChatXAI + OpenAI fallback)                          | llm.py           |
| 2.4  | Write flag types + ValidationFlag dataclass                                 | flags.py         |
| 2.5  | Test: import all models, verify types                                       | Quick smoke test |


**Session end:** `/compact`, commit, `graphify build`.

### Phase 3 — Ingestion Agent (Session 3, ~45 min)

**Model:** Sonnet 4.6
**Effort:** high


| Step | Task                                                               | Files created             |
| ---- | ------------------------------------------------------------------ | ------------------------- |
| 3.1  | Write extraction prompt template                                   | extractor.py              |
| 3.2  | Write `extract_invoice()` with `with_structured_output` + 3× retry | extractor.py              |
| 3.3  | Write `build_ingestion_graph()` sub-graph                          | agents/ingestion/agent.py |
| 3.4  | Test: run ingestion on INV-1001.txt, INV-1002.txt, INV-1012.pdf    | test_ingestion.py         |


### Phase 4 — Validation Agent (Session 4, ~45 min)

**Model:** Sonnet 4.6
**Effort:** high


| Step | Task                                                             | Files created              |
| ---- | ---------------------------------------------------------------- | -------------------------- |
| 4.1  | Write `get_stock()`, `check_duplicate()`, `deduct_stock()`       | db.py                      |
| 4.2  | Write `compute_flags()` with all 10 flag types + qty aggregation | flags.py                   |
| 4.3  | Write `build_validation_graph()` sub-graph                       | agents/validation/agent.py |
| 4.4  | Test: run validation on all 5 README scenarios                   | test_validation.py         |


### Phase 5 — Approval Agent with Reflection Loop (Session 5, ~60 min)

**Model:** Opus 4.6 (this is the most complex agent — worth the cost)
**Effort:** high


| Step | Task                                                                     | Files created            |
| ---- | ------------------------------------------------------------------------ | ------------------------ |
| 5.1  | Write `rule_based_approve()` + routing thresholds                        | rules.py                 |
| 5.2  | Write Generator prompt + `generate_decision()`                           | generator.py             |
| 5.3  | Write Critic prompt + `critique_decision()`                              | critic.py                |
| 5.4  | Write `build_approval_graph()` with 3-way entry router + reflection loop | agents/approval/agent.py |
| 5.5  | Test: Branch A (blocking flags), Branch B (reflection), Branch C (rule)  | test_approval.py         |


### Phase 6 — Payment Agent + Orchestrator (Session 6, ~45 min)

**Model:** Sonnet 4.6
**Effort:** medium


| Step | Task                                                      | Files created           |
| ---- | --------------------------------------------------------- | ----------------------- |
| 6.1  | Write `mock_payment()` with transaction ID                | mock_api.py             |
| 6.2  | Write `build_payment_graph()` with pay/reject routing     | agents/payment/agent.py |
| 6.3  | Wire all 4 sub-graphs in `build_graph()`                  | graph.py                |
| 6.4  | Write CLI entry point with `--setup` and `--invoice_path` | main.py                 |
| 6.5  | End-to-end test: all 20 invoices                          | test_end_to_end.py      |


### Phase 7 — Streamlit UI (Session 7, ~60 min)

**Model:** Sonnet 4.6
**Effort:** medium


| Step | Task                                          | Files created    |
| ---- | --------------------------------------------- | ---------------- |
| 7.1  | Copy DevDizzle's 3-tab layout structure       | streamlit_app.py |
| 7.2  | Add file upload + processing + result display | streamlit_app.py |
| 7.3  | Add sidebar inventory display                 | streamlit_app.py |
| 7.4  | Add session history                           | streamlit_app.py |


### Phase 8 — Polish + Docs (Session 8, ~30 min)

**Model:** Haiku 4.5
**Effort:** low


| Step | Task                                               | Files created   |
| ---- | -------------------------------------------------- | --------------- |
| 8.1  | Write `docs/presentation.md` with 3 demo scenarios | presentation.md |
| 8.2  | Write `docs/demo_script.md`                        | demo_script.md  |
| 8.3  | Add Dockerfile                                     | Dockerfile      |
| 8.4  | Final README.md                                    | README.md       |
| 8.5  | Run all tests one final time                       | —               |


---

## 7. Session Management Protocol

### Before Every Session

```bash
# 1. Start Headroom proxy (if not auto-wrapped)
headroom wrap claude

# 2. Rebuild graph if files changed since last session
graphify build --project ./invoice-agents

# 3. Start Claude Code with the right model
claude --model sonnet  # or haiku/opus per the phase plan
```

### During Session

```bash
# Check context usage
/context

# When context reaches 75%
/compact

# Switch model mid-session
/model haiku   # for boilerplate generation
/model opus    # for complex debugging

# Run tests with minimal output
pytest tests/ -x --tb=short -q 2>&1 | head -50

# Activate caveman for pure coding
/caveman

# Deactivate for architecture discussion
/caveman off
```

### After Every Session

```bash
# 1. Commit changes
git add -A && git commit -m "Phase X.Y complete"

# 2. Rebuild graph
graphify build --project ./invoice-agents

# 3. Check token usage
headroom stats
```

### One Agent Per Session Rule

**Do NOT build multiple agents in the same session.** Each agent has its own file set, prompts, and test cases. Building ingestion + validation in one session means:

- Context fills with ingestion code while writing validation
- Compaction may drop ingestion context you need to reference
- Errors compound — a bug in ingestion pollutes validation testing

**Instead:** One session = one agent = one commit. Clean context for each.

---

## 8. Cost Budget Estimation

Based on Sonnet 4.6 pricing ($3/1M input, $15/1M output) WITH the optimization stack:


| Phase                    | Sessions       | Est. tokens (with stack) | Est. cost  |
| ------------------------ | -------------- | ------------------------ | ---------- |
| Phase 1 — Scaffold       | 1 (Haiku)      | ~50K                     | $0.05      |
| Phase 2 — State/Models   | 1 (Sonnet)     | ~80K                     | $0.30      |
| Phase 3 — Ingestion      | 1 (Sonnet)     | ~120K                    | $0.50      |
| Phase 4 — Validation     | 1 (Sonnet)     | ~120K                    | $0.50      |
| Phase 5 — Approval       | 1 (Opus)       | ~150K                    | $2.00      |
| Phase 6 — Payment + Wire | 1 (Sonnet)     | ~100K                    | $0.40      |
| Phase 7 — Streamlit      | 1 (Sonnet)     | ~120K                    | $0.50      |
| Phase 8 — Polish         | 1 (Haiku)      | ~50K                     | $0.05      |
| **Total**                | **8 sessions** | **~790K tokens**         | **~$4.30** |


**Without the optimization stack:** Same work would cost ~$30–50 based on industry benchmarks (10× context re-reading overhead).

**Break-even:** The stack setup takes ~30 minutes. It pays for itself within the first session.

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│  TOKEN OPTIMIZATION STACK — INSTALL ORDER                   │
├─────────────────────────────────────────────────────────────┤
│  1. Graphify     → codebase knowledge graph (navigation)    │
│  2. CBM          → code discovery gate (file reads)         │
│  3. context-mode → sandbox large outputs (test results)     │
│  4. RTK          → shell output compression (CLI)           │
│  5. Headroom     → API proxy compression (everything)       │
│  6. Ponytail     → write less code (output reduction)       │
│  7. Caveman      → Claude talks less (prose reduction)      │
├─────────────────────────────────────────────────────────────┤
│  Combined: 90%+ token reduction · 30min → 3h+ sessions     │
├─────────────────────────────────────────────────────────────┤
│  ONE-CLICK: git clone sgaabdu4/claude-code-tips && install  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  MODEL STRATEGY                                             │
├─────────────────────────────────────────────────────────────┤
│  Haiku 4.5  → boilerplate, setup, simple edits ($1/M in)   │
│  Sonnet 4.6 → coding, agents, testing ($3/M in)            │
│  Opus 4.6   → architecture, complex agents ($15/M in)      │
├─────────────────────────────────────────────────────────────┤
│  /model haiku | sonnet | opus  (switch mid-session)         │
│  /effort low | medium | high   (adjust reasoning depth)    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  SESSION RULES                                              │
├─────────────────────────────────────────────────────────────┤
│  1 agent = 1 session = 1 commit                            │
│  /context at 75% → /compact                                │
│  graphify build after every commit                          │
│  pytest -x --tb=short -q | head -50                        │
│  /caveman for coding · /caveman off for planning            │
└─────────────────────────────────────────────────────────────┘
```

