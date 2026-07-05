# DATA_MODEL.md — Invoice Processing Automation (Galatiq Case)

> **Verification status:** This version has been checked against the actual contents of all 20 invoice files in `galatiq-ai/galatiq-case-invoices`. Corrections from the previous draft are marked **[CORRECTED]** and explained in Section 8. The most important fix: the INV-1013 total discrepancy is in the **tax→total** step (a $50 gap), not the line-item→subtotal step, which changes how `TOTAL_MISMATCH` must be implemented.

## Purpose

This document specifies the SQLite data model used by the Validation and Payment agents. It starts from the minimal schema given in the official `README.md` and extends it to the level required by `PLAN.md` / `TESTPLAN.md` — the extensions are explicitly invited by the README ("*You may extend the seed data with additional items or columns... consider adding tables for those as well*") and are needed to support duplicate-invoice detection, pricing validation, and stock-deduction tracking.

Two tables, one database file: `inventory.db`.

---

## 1. Table: `inventory`

Represents Acme Corp's own records of what items exist and how many units are on hand. This is what incoming vendor invoices are validated against — not the vendor's stock, Acme's.

### 1.1 Baseline (as given in README.md — verified exact)

```sql
CREATE TABLE IF NOT EXISTS inventory (
    item  TEXT PRIMARY KEY,
    stock INTEGER
);
```

| Column | Type | Constraint | Meaning |
|---|---|---|---|
| `item` | TEXT | PRIMARY KEY | Item name, exact match key |
| `stock` | INTEGER | — | Units currently on hand |

Minimum seed data (README — verified exact, only 4 rows):

| item | stock |
|---|---|
| WidgetA | 15 |
| WidgetB | 10 |
| GadgetX | 5 |
| FakeItem | 0 |

### 1.2 Extended schema (per PLAN.md / TESTPLAN.md)

```sql
CREATE TABLE IF NOT EXISTS inventory (
    item       TEXT PRIMARY KEY,
    stock      INTEGER NOT NULL DEFAULT 0,
    unit_price REAL,
    category   TEXT
);
```

| Column | Type | Constraint | Why it was added |
|---|---|---|---|
| `item` | TEXT | PRIMARY KEY | Same as baseline — canonical, normalised item name (no spaces, e.g. `WidgetA` not `Widget A`) |
| `stock` | INTEGER | NOT NULL, default 0 | Same as baseline |
| `unit_price` | REAL | nullable | Enables optional price-mismatch validation (invoice charges more/less per unit than Acme's expected price) |
| `category` | TEXT | nullable | Groups items (`widget`, `gadget`, `unknown`, `SENTINEL`); useful for reporting and for tagging known-fraud sentinel rows |

### 1.3 Full seed data (extended) — **[CORRECTED]** unit prices now match the invoices

The invoices consistently price items at **WidgetA $250, WidgetB $500, GadgetX $750**. The previous draft used $200 / $150 / $800, which did not match any invoice and would have produced false `PRICE_MISMATCH` flags if price validation were enabled. Corrected below.

| item | stock | unit_price | category | Why it's seeded |
|---|---|---|---|---|
| WidgetA | 15 | 250.00 | widget | Core item across most invoices (priced $250 everywhere) |
| WidgetB | 10 | 500.00 | widget | Core item across most invoices (priced $500 everywhere) |
| GadgetX | 5 | 750.00 | gadget | Low-stock item — priced $750; triggers `STOCK_MISMATCH` on over-ordering |
| WidgetC | 0 | 350.00 | widget | Referenced only by INV-1016 (priced $350 there) — zero stock to trigger a flag |
| FakeItem | 0 | NULL | SENTINEL | Referenced only by INV-1003 — zero-stock fraud marker |
| SuperGizmo | 0 | NULL | unknown | Referenced only by INV-1008 — not in Acme's real catalogue |
| MegaSprocket | 0 | NULL | unknown | Referenced only by INV-1008 — not in Acme's real catalogue |

> **Design decision — how to treat WidgetC, SuperGizmo, MegaSprocket.** There are two valid modelling choices and you must pick one consciously, because it changes which flag fires:
>
> - **Option A — seed them with `stock = 0` (rows present).** Then INV-1008 and INV-1016 fail with `ZERO_STOCK_SUSPICIOUS` (item found, zero stock). This is what the table above does.
> - **Option B — do NOT seed them (rows absent).** Then `get_stock()` returns `None` and they fail with `UNKNOWN_ITEM`.
>
> The README's own scenario table says INV-1008 (SuperGizmo, MegaSprocket) and INV-1016 (WidgetC) should be **"Flagged as unknown item"**, which points to **Option B**. If you want the README's stated behaviour, do **not** seed these three rows. The choice is legitimate either way, but be consistent with your TESTPLAN assertions — see Section 8, correction #4.

---

## 2. Table: `paid_invoices`

**Not present in the README at all.** Added specifically to solve the duplicate/revised-invoice trap (INV-1004 vs INV-1004_revised) and to give the Payment agent something to record against for auditability.

```sql
CREATE TABLE IF NOT EXISTS paid_invoices (
    invoice_id TEXT PRIMARY KEY,
    vendor     TEXT NOT NULL,
    amount     REAL NOT NULL,
    paid_at    TEXT NOT NULL
);
```

| Column | Type | Constraint | Meaning |
|---|---|---|---|
| `invoice_id` | TEXT | PRIMARY KEY | The invoice number as extracted (e.g. `INV-1004`). Primary key doubles as the duplicate-payment guard. |
| `vendor` | TEXT | NOT NULL | Vendor name, for audit/reporting |
| `amount` | REAL | NOT NULL | Amount actually paid |
| `paid_at` | TEXT | NOT NULL | ISO-8601 timestamp of payment, for the audit trail |

Written to by `record_payment()` immediately after a successful `mock_payment()` call. Read by `check_duplicate(invoice_id)` during Validation, before a decision is ever made — so a resubmitted or revised invoice for an already-paid `invoice_id` is flagged as `DUPLICATE_INVOICE` and routed straight to rejection (Branch A), regardless of amount.

> **[CORRECTED] — verified duplicate mechanics.** Both `invoice_1004.json` and `invoice_1004_revised.json` carry the identical `"invoice_number": "INV-1004"` (the revised one adds `"revision": "R1"` and a third line item, GadgetX×5). So the duplicate guard keys correctly on `invoice_id = "INV-1004"`. **Important caveat:** the duplicate is only detected if INV-1004 was *actually paid first* — `check_duplicate` reads the `paid_invoices` table, which is only written on APPROVE. If the two invoices are processed in isolation (as most unit tests do), neither is a duplicate. The DUPLICATE_INVOICE path is therefore an **ordering-dependent, stateful** test: pay INV-1004, then submit INV-1004_revised. See Section 8, correction #5.

> **PRIMARY KEY vs revisions.** Because `invoice_id` is the PK, a legitimate revision cannot be recorded under the same id after the original is paid. That is the intended behaviour here (revised invoice for an already-paid id = reject and investigate). If you ever needed to support legitimate revisions, you'd add a `revision` column and make the PK composite `(invoice_id, revision)` — out of scope for this assignment.

---

## 3. Entity relationship

```
 ┌────────────────────┐            ┌───────────────────────┐
 │      inventory       │            │     paid_invoices       │
 ├────────────────────┤            ├───────────────────────┤
 │ item (PK)            │            │ invoice_id (PK)          │
 │ stock                │            │ vendor                   │
 │ unit_price           │            │ amount                   │
 │ category             │            │ paid_at                  │
 └────────────────────┘            └───────────────────────┘
        ▲     ▲                                ▲
        │     │ read (validation)              │ read (validation:
        │     └──── compute_flags ─────────────┤        check_duplicate)
        │                                        │
        │ deduct_stock()  (write, APPROVE)       │ record_payment() (write, APPROVE)
        └──────────────────┬────────────────────┘
                            │
                     Payment sub-graph  ("pay" node, on APPROVE only)
```

There is no formal foreign key between the two tables. They are linked only through the `item` values inside an invoice's line items (which live in application state, not the DB) and through the invoice-level `vendor`/`amount` fields. This is deliberate: invoices are transient input, not a persisted table, so there is no `invoices` table in this model — the extracted invoice exists only as `state["extracted_invoice"]` for the duration of a single run.

---

## 4. Operations against the model

| Function | Table(s) touched | When | Effect |
|---|---|---|---|
| `get_stock(item)` | `inventory` (read) | Validation | Returns stock count, or `None` if item unknown |
| `compute_flags(invoice)` | `inventory` (read), `paid_invoices` (read) | Validation | Aggregates line items by name, compares **summed** totals to stock, checks `paid_invoices` for duplicates |
| `check_duplicate(invoice_id)` | `paid_invoices` (read) | Validation | `True` if `invoice_id` already exists |
| `deduct_stock(item, qty)` | `inventory` (write) | Payment, on APPROVE only | `stock = stock - qty` per **aggregated** line item |
| `record_payment(invoice_id, vendor, amount, paid_at)` | `paid_invoices` (write) | Payment, on APPROVE only | Inserts one row; the duplicate guard for future runs |

All queries use parameterised `?` placeholders — no f-string SQL — per the security note in PLAN.md (mitigating SQL injection via a maliciously-named item, covered by `test_parameterised_no_injection` / `test_sql_injection_item_name`).

> **[CORRECTED] — stock deduction must use aggregated quantities.** Because INV-1010 and INV-1013 repeat the same item across multiple lines, the *validation* comparison must aggregate quantities per item first. For `deduct_stock()`, either call it once with the summed quantity per item, or call it per raw line and let the subtractions accumulate — both give the same final stock. Keep it consistent with validation: aggregate once, use that same map for both the stock check and the deduction.

---

## 5. Setup script — **[CORRECTED]** prices fixed, WidgetC handling documented

```python
import sqlite3

def setup_db(db_path: str = "inventory.db") -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            item       TEXT PRIMARY KEY,
            stock      INTEGER NOT NULL DEFAULT 0,
            unit_price REAL,
            category   TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS paid_invoices (
            invoice_id TEXT PRIMARY KEY,
            vendor     TEXT NOT NULL,
            amount     REAL NOT NULL,
            paid_at    TEXT NOT NULL
        )
    """)

    # Prices corrected to match the invoices: WidgetA 250, WidgetB 500, GadgetX 750.
    # WidgetC / SuperGizmo / MegaSprocket included here (Option A: ZERO_STOCK_SUSPICIOUS).
    # For the README's stated "unknown item" behaviour (Option B), remove the last three rows.
    cur.executemany(
        "INSERT OR IGNORE INTO inventory VALUES (?, ?, ?, ?)",
        [
            ("WidgetA", 15, 250.0, "widget"),
            ("WidgetB", 10, 500.0, "widget"),
            ("GadgetX",  5, 750.0, "gadget"),
            ("WidgetC",  0, 350.0, "widget"),        # Option A only — omit for UNKNOWN_ITEM
            ("FakeItem", 0, None,  "SENTINEL"),
            ("SuperGizmo",   0, None, "unknown"),    # Option A only — omit for UNKNOWN_ITEM
            ("MegaSprocket", 0, None, "unknown"),    # Option A only — omit for UNKNOWN_ITEM
        ],
    )

    conn.commit()
    conn.close()
```

`INSERT OR IGNORE` keeps `python main.py --setup` idempotent (safe to run twice), per the Definition of Done in PLAN.md.

---

## 6. Traceability — which edge case needs which piece of the model **[CORRECTED]**

| Edge case (PLAN.md §4.3) | Invoice(s) | Verified data | Model element it depends on |
|---|---|---|---|
| Stock mismatch | INV-1002 (GadgetX×20), INV-1005 (GadgetX×8), INV-1007 (WidgetA×20, WidgetB×15) | ✓ confirmed | `inventory.stock` |
| Zero-stock / suspicious item | INV-1003 (FakeItem×100) | ✓ qty is **100** ($100,000) | `inventory` row `stock = 0`, `category = 'SENTINEL'` |
| Unknown item | INV-1008 (SuperGizmo×12, MegaSprocket×6), INV-1016 (WidgetC×3) | ✓ confirmed | Absent row → `UNKNOWN_ITEM`, OR seeded `stock=0` → `ZERO_STOCK_SUSPICIOUS` (pick one, §1.3) |
| Quantity aggregation | INV-1010 (WidgetA 8+4=12), INV-1013 (WidgetA 15+5+2=22, WidgetB 10+8=18, GadgetX 5+3+1=9) | ✓ confirmed | `inventory.stock` compared against a **summed** quantity |
| Duplicate invoice | INV-1004 then INV-1004_revised (both `INV-1004`) | ✓ stateful / ordering-dependent | `paid_invoices.invoice_id` |
| Total / tax mismatch | INV-1013 only | ✓ **$50 gap is tax→total, not line→subtotal** | App-level check: `subtotal + tax_amount` vs `total` (not a DB element) |
| Negative qty / amount / empty vendor | INV-1009 (WidgetA×-5, total -$250, vendor "") | ✓ subtotal also internally inconsistent | App-level integrity checks (not a DB element) |
| Foreign currency | INV-1014 (EUR) | ✓ confirmed | App-level check on `currency` field (not a DB element) |
| Stock depletion after payment | any approved invoice | — | `deduct_stock()` write to `inventory.stock` |
| SQL injection resistance | any item name | — | Parameterised queries against both tables |
| Price mismatch (optional, above & beyond) | any | prices now aligned ($250/$500/$750) | `inventory.unit_price` |

> **Scope note.** Total-mismatch, negative-value, empty-vendor, and foreign-currency checks are **not** properties of the SQLite model — they operate on `state["extracted_invoice"]` inside `compute_flags()`. They are listed here only for traceability. The DB model itself supports: stock validation, unknown-item detection, duplicate detection, price validation, and stock deduction.

---

## 7. Complete item catalogue observed across all 20 invoices

Verified by reading every file. This is the authoritative list of every item name that appears, so the seed data covers 100% of referenced items.

| Item name (as written) | Normalises to | Appears in | In README seed? |
|---|---|---|---|
| WidgetA | WidgetA | 1001, 1004, 1004r, 1005, 1006, 1007, 1009, 1010, 1011, 1013, 1015, 1016 | Yes |
| WidgetB | WidgetB | 1001, 1004, 1004r, 1005, 1006, 1007, 1009, 1010, 1011, 1013, 1014, 1015, 1016 | Yes |
| GadgetX | GadgetX | 1002, 1004r, 1005, 1007, 1010, 1013, 1015 | Yes |
| Widget A (space, OCR) | WidgetA | 1012 | via normalisation |
| WidgetB (OCR page) | WidgetB | 1012, 1014 | via normalisation |
| Gadget X (space, OCR) | GadgetX | 1012 | via normalisation |
| WidgetC | WidgetC | 1016 | No — extension needed |
| FakeItem | FakeItem | 1003 | Yes (stock 0) |
| SuperGizmo | SuperGizmo | 1008 | No — extension needed |
| MegaSprocket | MegaSprocket | 1008 | No — extension needed |

> Note: INV-1014 (XML, EUR) also prices WidgetA at €225 and WidgetB at €475 — different from the USD $250/$500. If price validation is enabled, currency must be normalised before comparing to `unit_price`, or price checks must be skipped for non-USD invoices. INV-1014 is flagged `FOREIGN_CURRENCY` regardless.

---

## 8. Corrections applied to the previous draft

| # | Previous draft said | Ground truth | Fix |
|---|---|---|---|
| 1 | `unit_price` seed: WidgetA 200, WidgetB 150, GadgetX 800 | Invoices price them $250 / $500 / $750 uniformly | Seed prices corrected to 250 / 500 / 750; WidgetC set to 350 (its INV-1016 price) |
| 2 | INV-1013 has a "$50 line-item overcharge" (line sum vs subtotal) | Line items sum to exactly $21,040 = stated subtotal (no line/subtotal gap). The $50 gap is `21040 + 7% tax = 22,512.80` vs stated total `22,562.80` | `TOTAL_MISMATCH` must compare `subtotal + tax_amount` against `total`, **not** line-sum against subtotal. INV-1013 still fails validation — but primarily on **STOCK_MISMATCH** (all three items over stock), with `TOTAL_MISMATCH` as a secondary flag |
| 3 | INV-1003 FakeItem quantity implied small | Actual qty is **100**, total **$100,000**, plus fraud markers ("URGENT", "Wire transfer preferred", due "yesterday") | Noted in seed rationale and traceability |
| 4 | Seeded WidgetC / SuperGizmo / MegaSprocket at stock 0 as the single approach | README scenario table says these should be flagged **"unknown item"** → rows should be **absent** (Option B) | Documented both options explicitly; flagged the TESTPLAN consistency requirement |
| 5 | Duplicate detection described as if always active | It is **stateful** — INV-1004 must be paid before INV-1004_revised is seen as a duplicate; in isolation neither is flagged | Documented the ordering dependency; the e2e test must pay 1004 first |
| 6 | (not mentioned) | INV-1009's stated `subtotal` (1000) is itself inconsistent with its line items (-250) | Added as an integrity observation; the negative total (-250) already triggers `DATA_INTEGRITY_ERROR` regardless |
| 7 | ER diagram had a formatting artifact ("(validation" leaking into a cell) | — | Redrawn cleanly with both read/write paths labelled |

---

## 9. What the README did *not* specify (and why it was added)

| Missing from README | Added in this model | Reason |
|---|---|---|
| Any payment-history table | `paid_invoices` | Needed for duplicate-invoice detection and audit trail — impossible without persisting prior payments |
| `unit_price` column | Added to `inventory` (corrected values) | Enables optional price-integrity checks (invoice price vs. Acme's expected price) |
| `category` column | Added to `inventory` | Distinguishes real-but-depleted items from genuinely unknown/fraudulent item names |
| Seed rows for `WidgetC`, `SuperGizmo`, `MegaSprocket` | Added (Option A) or deliberately omitted (Option B) | The README only seeds 4 items; INV-1008 and INV-1016 reference items the minimal seed doesn't cover. The choice governs UNKNOWN_ITEM vs ZERO_STOCK_SUSPICIOUS |
| `NOT NULL` / default constraints | Added | README's baseline schema has no constraints at all; basic integrity hygiene |

---

## 10. Alignment note for PLAN.md and TESTPLAN.md

Two changes propagate out of this verification and should be reflected in the other docs:

1. **INV-1013 `TOTAL_MISMATCH`** — update the check definition everywhere from "line items vs subtotal" to "subtotal + tax_amount vs total". The invoice's *primary* failure is `STOCK_MISMATCH` (all three items exceed stock after aggregation); `TOTAL_MISMATCH` is a secondary flag. Either flag alone routes it to Branch A / REJECTED, so the end-to-end outcome (REJECTED) is unchanged — but the asserted flag reason should mention STOCK_MISMATCH first.

2. **Duplicate detection is stateful** — the `test_duplicate_invoice` end-to-end test must run in two steps within one shared DB: process `invoice_1004.json` to PAID (which writes to `paid_invoices`), then process `invoice_1004_revised.json` and assert `DUPLICATE_INVOICE` → REJECTED. Using the per-test `fresh_db` fixture in isolation will not trigger it.
