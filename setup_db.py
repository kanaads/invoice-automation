"""Creates and seeds inventory.db. Run with: python setup_db.py"""
import sqlite3

DB_PATH = "data/inventory.db"


def setup_db(db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory (
            item       TEXT PRIMARY KEY,
            stock      INTEGER NOT NULL DEFAULT 0,
            unit_price REAL,
            category   TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS paid_invoices (
            invoice_id TEXT PRIMARY KEY,
            vendor     TEXT NOT NULL,
            amount     REAL NOT NULL,
            paid_at    TEXT NOT NULL
        )
        """
    )

    # Option B: WidgetC / SuperGizmo / MegaSprocket are deliberately NOT seeded,
    # so get_stock() returns None for them -> UNKNOWN_ITEM (matches the README's
    # stated scenario table for INV-1008 / INV-1016).
    cur.executemany(
        "INSERT OR IGNORE INTO inventory VALUES (?, ?, ?, ?)",
        [
            ("WidgetA", 15, 250.0, "widget"),
            ("WidgetB", 10, 500.0, "widget"),
            ("GadgetX", 5, 750.0, "gadget"),
            ("FakeItem", 0, None, "SENTINEL"),
        ],
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    setup_db()
    print(f"Inventory database ready at {DB_PATH}")
