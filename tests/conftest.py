import shutil
import sqlite3

import pytest


@pytest.fixture(scope="session")
def test_db(tmp_path_factory):
    """Create a fresh inventory.db with the project's seed data for tests."""
    db_path = tmp_path_factory.mktemp("data") / "inventory.db"
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE inventory (item TEXT PRIMARY KEY, stock INTEGER NOT NULL DEFAULT 0, "
        "unit_price REAL, category TEXT)"
    )
    cur.executemany(
        "INSERT INTO inventory VALUES (?,?,?,?)",
        [
            ("WidgetA", 15, 250.0, "widget"),
            ("WidgetB", 10, 500.0, "widget"),
            ("GadgetX", 5, 750.0, "gadget"),
            ("FakeItem", 0, None, "SENTINEL"),
        ],
    )
    cur.execute(
        "CREATE TABLE paid_invoices (invoice_id TEXT PRIMARY KEY, vendor TEXT NOT NULL, "
        "amount REAL NOT NULL, paid_at TEXT NOT NULL)"
    )
    conn.commit()
    conn.close()
    return str(db_path)


@pytest.fixture
def fresh_db(test_db, tmp_path):
    """A per-test copy so stock deductions don't leak between tests."""
    copy = tmp_path / "inventory.db"
    shutil.copy(test_db, copy)
    return str(copy)


@pytest.fixture
def invoice_dir():
    return "data/invoices"
