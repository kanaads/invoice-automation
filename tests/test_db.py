from src.invoice_agents.agents.validation.db import (
    check_duplicate,
    deduct_stock,
    get_stock,
    record_payment,
)


def test_get_stock_found(fresh_db):
    assert get_stock("WidgetA", db_path=fresh_db) == 15


def test_get_stock_zero(fresh_db):
    assert get_stock("FakeItem", db_path=fresh_db) == 0


def test_get_stock_unknown(fresh_db):
    assert get_stock("Nonexistent", db_path=fresh_db) is None


def test_get_stock_unseeded_items_are_unknown(fresh_db):
    # WidgetC / SuperGizmo / MegaSprocket are deliberately not seeded (Option B).
    for item in ("WidgetC", "SuperGizmo", "MegaSprocket"):
        assert get_stock(item, db_path=fresh_db) is None


def test_parameterised_no_injection(fresh_db):
    result = get_stock("'; DROP TABLE inventory; --", db_path=fresh_db)
    assert result is None
    assert get_stock("WidgetA", db_path=fresh_db) == 15


def test_deduct_stock(fresh_db):
    deduct_stock("WidgetA", 10, db_path=fresh_db)
    assert get_stock("WidgetA", db_path=fresh_db) == 5


def test_check_duplicate_false(fresh_db):
    assert check_duplicate("INV-9999", db_path=fresh_db) is False


def test_check_duplicate_true(fresh_db):
    record_payment("INV-1004", "Acme Vendor", 1890.0, "2026-01-01T00:00:00", db_path=fresh_db)
    assert check_duplicate("INV-1004", db_path=fresh_db) is True
