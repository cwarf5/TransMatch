import os
import tempfile
import pytest
import pandas as pd
from reconciler import (
    ColumnMap, DepositEntry, BankEntry, ReconciliationResult,
    detect_columns,
)


def make_df(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def test_detect_columns_three_deps():
    df = make_df(["Site ID", "Date", "Dep1", "Dep2", "Dep3", "Total", "Flag", "DIT", "Bank"])
    col_map = detect_columns(df)
    assert col_map.dep_cols == ["Dep1", "Dep2", "Dep3"]
    assert col_map.bank_col == "Bank"
    assert col_map.dit_col == "DIT"
    assert col_map.date_col == "Date"


def test_detect_columns_one_dep():
    df = make_df(["Site ID", "Date", "Dep1", "Total", "Flag", "DIT", "Bank"])
    col_map = detect_columns(df)
    assert col_map.dep_cols == ["Dep1"]
    assert col_map.bank_col == "Bank"


def test_detect_columns_missing_bank_raises():
    df = make_df(["Site ID", "Date", "Dep1", "Total"])
    with pytest.raises(ValueError, match="Bank"):
        detect_columns(df)


def test_detect_columns_missing_dep_raises():
    df = make_df(["Site ID", "Date", "Total", "Bank"])
    with pytest.raises(ValueError, match="Dep"):
        detect_columns(df)


def test_detect_dit_column_by_cell_value():
    # DIT column header is "Flag" — does not contain "dit", so falls back to cell scan
    df = pd.DataFrame({
        "Site ID": ["001"],
        "Date": ["2025-01-01"],
        "Dep1": ["500.00"],
        "Flag": ["DIT"],
        "Bank": [None],
    })
    col_map = detect_columns(df)
    assert col_map.dit_col == "Flag"


def test_detect_dit_no_false_positive_audit():
    # "AUDIT" contains "dit" as substring but should NOT match as DIT column
    df = make_df(["Site ID", "Date", "Dep1", "AUDIT", "Bank"])
    col_map = detect_columns(df)
    assert col_map.dit_col is None


def test_detect_dit_no_false_positive_credit():
    # "CREDIT" contains "dit" as substring but should NOT match as DIT column
    df = make_df(["Site ID", "Date", "Dep1", "CREDIT", "Bank"])
    col_map = detect_columns(df)
    assert col_map.dit_col is None
