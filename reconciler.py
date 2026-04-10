from __future__ import annotations
from dataclasses import dataclass, field
from collections import Counter
from typing import Optional
import os
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
