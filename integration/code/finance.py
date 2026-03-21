"""Finance module (extra).

Responsibilities:
- Track income and expenses via a ledger
- Update inventory cash as a side effect (integration point)

This module intentionally calls inventory._adjust_cash() so that:
results.py -> finance.py -> inventory.py forms a clear integration chain.
"""

from __future__ import annotations

from models import LedgerEntry, SystemState, ValidationError

import inventory


def record_income(state: SystemState, amount: int, reason: str) -> LedgerEntry:
    if amount <= 0:
        raise ValidationError("Income amount must be > 0")
    reason = reason.strip() or "income"

    inventory._adjust_cash(state, amount)

    entry = LedgerEntry(entry_id=state.new_id("fin"), kind="income", amount=amount, reason=reason)
    state.ledger.append(entry)
    return entry


def record_expense(state: SystemState, amount: int, reason: str) -> LedgerEntry:
    if amount <= 0:
        raise ValidationError("Expense amount must be > 0")
    reason = reason.strip() or "expense"

    inventory._adjust_cash(state, -amount)

    entry = LedgerEntry(entry_id=state.new_id("fin"), kind="expense", amount=amount, reason=reason)
    state.ledger.append(entry)
    return entry
