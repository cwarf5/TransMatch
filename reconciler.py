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
