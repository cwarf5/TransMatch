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


from reconciler import run_reconciliation


def _make_df(rows):
    """rows: list of (date, dep1, dep2, dep3, dit_flag, bank)"""
    return pd.DataFrame(rows, columns=["Date", "Dep1", "Dep2", "Dep3", "DIT", "Bank"])


def test_all_matched():
    df = _make_df([
        ("2025-01-01", "100.00", None, None, None, "100.00"),
        ("2025-01-02", "200.00", None, None, None, "200.00"),
    ])
    result = run_reconciliation(df, detect_columns(df))
    assert result.matched_count == 2
    assert result.unmatched_deps == []
    assert result.unmatched_bank == []
    assert result.dit_entries == []


def test_unmatched_dep():
    df = _make_df([("2025-01-01", "500.00", None, None, None, None)])
    result = run_reconciliation(df, detect_columns(df))
    assert result.matched_count == 0
    assert len(result.unmatched_deps) == 1
    assert result.unmatched_deps[0].amount == 500.0
    assert result.unmatched_deps[0].date == "2025-01-01"


def test_unmatched_bank():
    df = _make_df([("2025-01-01", None, None, None, None, "300.00")])
    result = run_reconciliation(df, detect_columns(df))
    assert result.matched_count == 0
    assert len(result.unmatched_bank) == 1
    assert result.unmatched_bank[0].amount == 300.0


def test_dit_not_flagged_as_discrepancy():
    df = _make_df([("2025-01-01", "750.00", None, None, "DIT", None)])
    result = run_reconciliation(df, detect_columns(df))
    assert result.matched_count == 0
    assert result.unmatched_deps == []
    assert len(result.dit_entries) == 1
    assert result.dit_entries[0].amount == 750.0


def test_duplicate_amounts_both_matched():
    df = _make_df([
        ("2025-01-01", "500.00", None, None, None, "500.00"),
        ("2025-01-02", "500.00", None, None, None, "500.00"),
    ])
    result = run_reconciliation(df, detect_columns(df))
    assert result.matched_count == 2
    assert result.unmatched_deps == []
    assert result.unmatched_bank == []


def test_duplicate_amounts_one_unmatched():
    df = _make_df([
        ("2025-01-01", "500.00", None, None, None, "500.00"),
        ("2025-01-02", "500.00", None, None, None, None),
    ])
    result = run_reconciliation(df, detect_columns(df))
    assert result.matched_count == 1
    assert len(result.unmatched_deps) == 1


def test_multiple_dep_columns():
    df = pd.DataFrame({
        "Date": ["2025-01-01"],
        "Dep1": ["100.00"],
        "Dep2": ["200.00"],
        "Dep3": ["300.00"],
        "DIT": [None],
        "Bank": ["100.00"],
    })
    result = run_reconciliation(df, detect_columns(df))
    assert result.matched_count == 1
    assert len(result.unmatched_deps) == 2


from reconciler import format_output


def test_format_output_all_matched():
    result = ReconciliationResult(matched_count=3)
    output = format_output(result)
    assert "Matched:" in output
    assert "3" in output
    assert "No discrepancies found" in output


def test_format_output_with_discrepancies():
    result = ReconciliationResult(
        matched_count=1,
        unmatched_deps=[DepositEntry(amount=1250.0, date="2025-03-01")],
        unmatched_bank=[BankEntry(amount=875.0, date="2025-03-05")],
        dit_entries=[DepositEntry(amount=500.0, date="2025-03-08", is_dit=True)],
    )
    output = format_output(result)
    assert "Matched:" in output
    assert "1,250.00" in output
    assert "2025-03-01" in output
    assert "DEP" in output
    assert "875.00" in output
    assert "2025-03-05" in output
    assert "BANK" in output
    assert "500.00" in output
    assert "DIT" in output


def test_format_output_with_errors():
    result = ReconciliationResult(errors=["Non-numeric value in Dep1 on 2025-01-01: 'abc'"])
    output = format_output(result)
    assert "WARNINGS" in output
    assert "Non-numeric" in output


from reconciler import load_csv


def test_load_csv_returns_dataframe():
    csv_content = "Site ID,Date,Dep1,DIT,Bank\n001,2025-01-01,100.0,,100.0\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
        f.write(csv_content)
        path = f.name
    try:
        df = load_csv(path)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert "Dep1" in df.columns
        assert "Bank" in df.columns
    finally:
        os.unlink(path)


def test_load_csv_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_csv("/nonexistent/path/does_not_exist.csv")
