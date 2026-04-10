# TransMatch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python desktop tool that reconciles PDI deposit records against bank transactions from a CSV, flagging discrepancies and noting DIT entries.

**Architecture:** Two files: `reconciler.py` contains all pure logic (column detection, matching, formatting) with no UI dependency so it can be fully unit-tested; `transmatch.py` contains the tkinter App class that calls into reconciler. This split keeps business logic testable without needing a display.

**Tech Stack:** Python 3.10+, pandas, tkinter (stdlib), collections.Counter, pytest

---

## File Structure

- Create: `reconciler.py` — column detection, matching algorithm, output formatting
- Create: `transmatch.py` — tkinter App class, entry point (`python transmatch.py`)
- Create: `tests/__init__.py` — empty, marks tests as a package
- Create: `tests/test_reconciler.py` — unit tests for all reconciler functions
- Create: `requirements.txt` — pandas + pytest

---

### Task 1: Project Setup

**Files:**
- Create: `requirements.txt`

- [ ] **Step 1: Create requirements.txt**

```
pandas>=2.0.0
pytest>=7.0.0
```

- [ ] **Step 2: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: Successfully installed pandas (and numpy as a transitive dependency)

- [ ] **Step 3: Verify pandas import works**

Run: `python -c "import pandas; print(pandas.__version__)"`
Expected: A version string like `2.x.x`

- [ ] **Step 4: Commit**

```bash
git init
git add requirements.txt
git commit -m "chore: initial project setup with pandas dependency"
```

---

### Task 2: Data Structures

**Files:**
- Create: `reconciler.py` (initial, dataclasses only)
- Create: `tests/__init__.py`
- Create: `tests/test_reconciler.py` (initial import test only)

- [ ] **Step 1: Write the failing import test**

Create `tests/__init__.py` as an empty file.

Create `tests/test_reconciler.py`:
```python
from reconciler import ColumnMap, DepositEntry, BankEntry, ReconciliationResult
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_reconciler.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'reconciler'`

- [ ] **Step 3: Create reconciler.py with data structures**

Create `reconciler.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_reconciler.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add reconciler.py tests/__init__.py tests/test_reconciler.py
git commit -m "feat: add reconciler data structures"
```

---

### Task 3: Column Detection

**Files:**
- Modify: `reconciler.py` — add `detect_columns(df) -> ColumnMap`
- Modify: `tests/test_reconciler.py` — add column detection tests

- [ ] **Step 1: Write failing tests for detect_columns**

Replace the contents of `tests/test_reconciler.py` with:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_reconciler.py -v`
Expected: FAIL with `ImportError: cannot import name 'detect_columns'`

- [ ] **Step 3: Implement detect_columns**

Add to `reconciler.py` after the dataclass definitions:
```python
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
    dit_col = next((c for c in cols if "dit" in str(c).lower()), None)
    if dit_col is None:
        for c in cols:
            if df[c].astype(str).str.contains(r"\bDIT\b", case=False, na=False).any():
                dit_col = c
                break

    return ColumnMap(dep_cols=dep_cols, bank_col=bank_col, dit_col=dit_col, date_col=date_col)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_reconciler.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add reconciler.py tests/test_reconciler.py
git commit -m "feat: implement column detection with header name and cell-value fallback"
```

---

### Task 4: Reconciliation Logic

**Files:**
- Modify: `reconciler.py` — add `run_reconciliation(df, col_map) -> ReconciliationResult`
- Modify: `tests/test_reconciler.py` — add reconciliation tests

- [ ] **Step 1: Write failing tests for run_reconciliation**

Append to `tests/test_reconciler.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_reconciler.py -v`
Expected: FAIL with `ImportError: cannot import name 'run_reconciliation'`

- [ ] **Step 3: Implement run_reconciliation**

Add to `reconciler.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_reconciler.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add reconciler.py tests/test_reconciler.py
git commit -m "feat: implement reconciliation matching with multiset Counter logic"
```

---

### Task 5: Output Formatting

**Files:**
- Modify: `reconciler.py` — add `format_output(result) -> str`
- Modify: `tests/test_reconciler.py` — add formatting tests

- [ ] **Step 1: Write failing tests for format_output**

Append to `tests/test_reconciler.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_reconciler.py -v`
Expected: FAIL with `ImportError: cannot import name 'format_output'`

- [ ] **Step 3: Implement format_output**

Add to `reconciler.py`:
```python
def format_output(result: ReconciliationResult) -> str:
    lines = []
    lines.append("--- Summary ---")
    lines.append(f"  {'✓  Matched:':<22} {result.matched_count}")
    lines.append(f"  {'✗  Unmatched Deps:':<22} {len(result.unmatched_deps)}")
    lines.append(f"  {'~  DIT (noted):':<22} {len(result.dit_entries)}")
    lines.append(f"  {'✗  Unmatched Bank:':<22} {len(result.unmatched_bank)}")
    lines.append("")

    has_detail = result.unmatched_deps or result.unmatched_bank or result.dit_entries
    if not has_detail:
        lines.append("  No discrepancies found.")
    else:
        lines.append("--- Details ---")
        for dep in result.unmatched_deps:
            lines.append(
                f"  ✗  DEP   {dep.date:<14}  ${dep.amount:>12,.2f}   No matching bank entry"
            )
        for bank in result.unmatched_bank:
            lines.append(
                f"  ✗  BANK  {bank.date:<14}  ${bank.amount:>12,.2f}   No matching deposit"
            )
        for dit in result.dit_entries:
            lines.append(
                f"  ~  DIT   {dit.date:<14}  ${dit.amount:>12,.2f}   Deposit in transit (noted)"
            )

    if result.errors:
        lines.append("")
        lines.append("--- WARNINGS ---")
        for err in result.errors:
            lines.append(f"  !  {err}")

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_reconciler.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add reconciler.py tests/test_reconciler.py
git commit -m "feat: implement output formatting with summary and detail sections"
```

---

### Task 6: CSV Loading

**Files:**
- Modify: `reconciler.py` — add `load_csv(path) -> pd.DataFrame`
- Modify: `tests/test_reconciler.py` — add CSV loading tests

- [ ] **Step 1: Write failing tests for load_csv**

Append to `tests/test_reconciler.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_reconciler.py -v`
Expected: FAIL with `ImportError: cannot import name 'load_csv'`

- [ ] **Step 3: Implement load_csv**

Add to `reconciler.py` (after the imports, before the dataclasses):
```python
def load_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    df = pd.read_csv(path, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    return df
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_reconciler.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add reconciler.py tests/test_reconciler.py
git commit -m "feat: implement CSV loading with header normalization"
```

---

### Task 7: tkinter UI

**Files:**
- Create: `transmatch.py`

*tkinter widgets cannot be unit tested without a display. This task uses manual verification.*

- [ ] **Step 1: Create transmatch.py**

Create `transmatch.py`:
```python
import os
import tkinter as tk
from tkinter import filedialog, scrolledtext

from reconciler import load_csv, detect_columns, run_reconciliation, format_output


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TransMatch — Deposit Reconciliation")
        self.minsize(700, 500)
        self.resizable(True, True)
        self._csv_path: str | None = None
        self._build_ui()

    def _build_ui(self):
        top = tk.Frame(self, padx=10, pady=8)
        top.pack(fill=tk.X)

        tk.Button(top, text="Select CSV File", command=self._select_file).pack(side=tk.LEFT)
        self._path_var = tk.StringVar(value="No file selected")
        tk.Label(top, textvariable=self._path_var, anchor="w").pack(
            side=tk.LEFT, padx=10, fill=tk.X, expand=True
        )

        self._run_btn = tk.Button(
            self, text="Run Check", command=self._run, state=tk.DISABLED, padx=12
        )
        self._run_btn.pack(pady=(0, 8))

        self._output = scrolledtext.ScrolledText(
            self, state=tk.DISABLED, font=("Courier", 10), wrap=tk.NONE
        )
        self._output.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    def _select_file(self):
        path = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if path:
            self._csv_path = path
            self._path_var.set(os.path.basename(path))
            self._run_btn.config(state=tk.NORMAL)

    def _run(self):
        self._run_btn.config(state=tk.DISABLED)
        self._set_output("Running...")
        self.update_idletasks()
        try:
            df = load_csv(self._csv_path)
            col_map = detect_columns(df)
            result = run_reconciliation(df, col_map)
            output = format_output(result)
        except Exception as exc:
            output = f"Error: {exc}"
        finally:
            self._run_btn.config(state=tk.NORMAL)
        self._set_output(output)

    def _set_output(self, text: str):
        self._output.config(state=tk.NORMAL)
        self._output.delete("1.0", tk.END)
        self._output.insert(tk.END, text)
        self._output.config(state=tk.DISABLED)


if __name__ == "__main__":
    App().mainloop()
```

- [ ] **Step 2: Manual verification — launch the app**

Run: `python transmatch.py`
Expected: Window opens with "Select CSV File" button visible and "Run Check" button disabled.

- [ ] **Step 3: Create test CSV and run manually**

Create `test_data.csv` in the project root:
```
Site ID,Date,Dep1,Dep2,Dep3,Total,Flag,Bank
001,2025-01-01,100.00,,,100.00,,100.00
001,2025-01-02,500.00,,,500.00,DIT,
001,2025-01-03,200.00,300.00,,500.00,,200.00
```

Select `test_data.csv` in the app and click Run Check.

Expected output:
```
--- Summary ---
  ✓  Matched:               2
  ✗  Unmatched Deps:        1
  ~  DIT (noted):           1
  ✗  Unmatched Bank:        0

--- Details ---
  ✗  DEP   2025-01-03       $      300.00   No matching bank entry
  ~  DIT   2025-01-02       $      500.00   Deposit in transit (noted)
```

- [ ] **Step 4: Commit**

```bash
git add transmatch.py test_data.csv
git commit -m "feat: implement tkinter UI with file picker and scrollable output pane"
```

---

### Task 8: Full Test Suite

**Files:** none new

- [ ] **Step 1: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS, zero failures

- [ ] **Step 2: Commit if any fixes needed**

If any failures were found and fixed:
```bash
git add reconciler.py tests/test_reconciler.py
git commit -m "fix: address issues found during full test run"
```
