"""Rule-based routing thresholds for the approval sub-graph. No LLM involved."""

APPROVAL_THRESHOLD = 10000
MAX_REFLECTION_ITERATIONS = 3


def has_blocking_flags(flags: list[dict]) -> bool:
    """Flags default to blocking unless explicitly marked otherwise (e.g. FOREIGN_CURRENCY)."""
    return any(f.get("blocking", True) for f in flags)


def requires_reflection(amount: float, flags: list[dict]) -> bool:
    """Branch B: high-value AND clean. Blocking flags always win over the amount threshold."""
    return amount > APPROVAL_THRESHOLD and not has_blocking_flags(flags)


def rule_based_approve(amount: float, flags: list[dict]) -> bool:
    """Branch C: low-value AND clean -- auto-approve with zero LLM calls."""
    return amount <= APPROVAL_THRESHOLD and not has_blocking_flags(flags)
