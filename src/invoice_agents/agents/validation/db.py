import json
import sqlite3
from typing import Optional

DEFAULT_DB_PATH = "data/inventory.db"


def get_stock(item: str, db_path: str = DEFAULT_DB_PATH) -> Optional[int]:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute("SELECT stock FROM inventory WHERE item = ?", (item,))
        row = cur.fetchone()
        return row[0] if row is not None else None
    finally:
        conn.close()


def deduct_stock(item: str, qty: int, db_path: str = DEFAULT_DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("UPDATE inventory SET stock = stock - ? WHERE item = ?", (qty, item))
        conn.commit()
    finally:
        conn.close()


def check_duplicate(invoice_id: str, db_path: str = DEFAULT_DB_PATH) -> bool:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "SELECT 1 FROM paid_invoices WHERE invoice_id = ?", (invoice_id,)
        )
        return cur.fetchone() is not None
    finally:
        conn.close()


def record_payment(
    invoice_id: str,
    vendor: str,
    amount: float,
    paid_at: str,
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO paid_invoices (invoice_id, vendor, amount, paid_at) VALUES (?, ?, ?, ?)",
            (invoice_id, vendor, amount, paid_at),
        )
        conn.commit()
    finally:
        conn.close()


def record_rejection(
    invoice_id: Optional[str],
    vendor: Optional[str],
    reason: str,
    flags: list[dict],
    rejected_at: str,
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO rejections (invoice_id, vendor, reason, flags, rejected_at) VALUES (?, ?, ?, ?, ?)",
            (invoice_id, vendor, reason, json.dumps(flags), rejected_at),
        )
        conn.commit()
    finally:
        conn.close()
