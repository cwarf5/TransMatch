from __future__ import annotations
from dataclasses import dataclass, field
from collections import Counter
from typing import Optional
import os
import re
import pandas as pd


@dataclass
class ColumnMap:
    dep_cols: list[str]
    bank_col: str
    dit_col: Optional[str]
    date_col: Optional[str]


@dataclass
class DepositEntry:
    amount: float
    date: str
    is_dit: bool = False


@dataclass
class BankEntry:
    amount: float
    date: str


@dataclass
class ReconciliationResult:
    matched_count: int = 0
    unmatched_deps: list[DepositEntry] = field(default_factory=list)
    dit_entries: list[DepositEntry] = field(default_factory=list)
    unmatched_bank: list[BankEntry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def detect_columns(df: pd.DataFrame) -> ColumnMap:
    cols = list(df.columns)

    dep_cols = [c for c in cols if "dep" in str(c).lower()]
    if not dep_cols:
        raise ValueError(
            "Could not detect Dep columns — verify CSV has headers like 'Dep1', 'Dep2', etc."
        )

    bank_col = next((c for c in cols if "bank" in str(c).lower()), None)
    if bank_col is None:
        raise ValueError(
            "Could not detect Bank column — verify CSV has a header containing 'Bank'."
        )

    date_col = next((c for c in cols if "date" in str(c).lower()), None)

    # Try to find DIT column by header name first, then fall back to cell value scan
    dit_col = next((c for c in cols if re.search(r'\bdit\b', str(c).lower())), None)
    if dit_col is None:
        for c in cols:
            if df[c].astype(str).str.contains(r"\bDIT\b", case=False, na=False).any():
                dit_col = c
                break

    return ColumnMap(dep_cols=dep_cols, bank_col=bank_col, dit_col=dit_col, date_col=date_col)


def run_reconciliation(df: pd.DataFrame, col_map: ColumnMap) -> ReconciliationResult:
    result = ReconciliationResult()

    def _get_date(row) -> str:
        if col_map.date_col and col_map.date_col in row.index:
            val = str(row[col_map.date_col]).strip()
            return val if val not in ("", "nan") else "Unknown"
        return "Unknown"

    def _is_dit(row) -> bool:
        if col_map.dit_col and col_map.dit_col in row.index:
            return str(row[col_map.dit_col]).strip().upper() == "DIT"
        return False

    def _parse_amount(val, context: str, result: ReconciliationResult) -> Optional[float]:
        s = str(val).strip()
        if s in ("", "nan", "None"):
            return None
        try:
            return round(float(s.replace(",", "")), 2)
        except (ValueError, TypeError):
            result.errors.append(f"Non-numeric value in {context}: {val!r}")
            return None

    # Collect deposit entries
    all_deps: list[DepositEntry] = []
    for _, row in df.iterrows():
        date = _get_date(row)
        is_dit = _is_dit(row)
        for dep_col in col_map.dep_cols:
            amount = _parse_amount(row[dep_col], f"{dep_col} on {date}", result)
            if amount is not None:
                all_deps.append(DepositEntry(amount=amount, date=date, is_dit=is_dit))

    # Collect bank entries
    all_bank: list[BankEntry] = []
    for _, row in df.iterrows():
        date = _get_date(row)
        amount = _parse_amount(row[col_map.bank_col], f"Bank on {date}", result)
        if amount is not None:
            all_bank.append(BankEntry(amount=amount, date=date))

    # Separate DIT from non-DIT deposits
    result.dit_entries = [d for d in all_deps if d.is_dit]
    non_dit_deps = [d for d in all_deps if not d.is_dit]

    # Multiset matching via Counter
    dep_counter = Counter(d.amount for d in non_dit_deps)
    bank_counter = Counter(b.amount for b in all_bank)
    matched_counter = dep_counter & bank_counter
    result.matched_count = sum(matched_counter.values())
    unmatched_dep_counter = dep_counter - bank_counter
    unmatched_bank_counter = bank_counter - dep_counter

    # Preserve per-row dates by walking source lists
    consumed_dep: Counter = Counter()
    for dep in non_dit_deps:
        if consumed_dep[dep.amount] < unmatched_dep_counter[dep.amount]:
            result.unmatched_deps.append(dep)
            consumed_dep[dep.amount] += 1

    consumed_bank: Counter = Counter()
    for bank in all_bank:
        if consumed_bank[bank.amount] < unmatched_bank_counter[bank.amount]:
            result.unmatched_bank.append(bank)
            consumed_bank[bank.amount] += 1

    return result
