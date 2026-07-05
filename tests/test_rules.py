from src.invoice_agents.agents.approval.rules import (
    APPROVAL_THRESHOLD,
    has_blocking_flags,
    requires_reflection,
    rule_based_approve,
)


def test_rule_approve_clean_low():
    assert rule_based_approve(amount=3000, flags=[]) is True


def test_rule_approve_high_amount():
    assert rule_based_approve(amount=15000, flags=[]) is False


def test_rule_approve_with_flags():
    assert rule_based_approve(amount=3000, flags=[{"type": "STOCK_MISMATCH"}]) is False


def test_requires_reflection():
    assert requires_reflection(amount=15000, flags=[]) is True


def test_requires_reflection_false_when_flagged():
    # Blocking flags always win over the amount threshold -- Branch A, not Branch B.
    assert requires_reflection(amount=15000, flags=[{"type": "STOCK_MISMATCH"}]) is False


def test_requires_reflection_false_when_low():
    assert requires_reflection(amount=3000, flags=[]) is False


def test_has_blocking_flags():
    assert has_blocking_flags([{"type": "STOCK_MISMATCH"}]) is True


def test_has_blocking_flags_false():
    assert has_blocking_flags([]) is False


def test_has_blocking_flags_ignores_non_blocking():
    # A FOREIGN_CURRENCY-only invoice should still route to Branch B/C, not Branch A.
    assert has_blocking_flags([{"type": "FOREIGN_CURRENCY", "blocking": False}]) is False


def test_rule_approve_with_only_non_blocking_flag():
    assert rule_based_approve(amount=3000, flags=[{"type": "FOREIGN_CURRENCY", "blocking": False}]) is True


def test_threshold_is_10k():
    assert APPROVAL_THRESHOLD == 10000
