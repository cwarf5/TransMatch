# TransMatch Design Spec
**Date:** 2026-04-10

## Overview

TransMatch is a single-file Python desktop tool that reconciles PDI deposit records against bank transactions from a CSV export. It identifies deposits that have no matching bank entry (excluding DIT), bank entries with no matching deposit, and notes deposits flagged as Deposits in Transit (DIT).

One site per file. The tool reads a CSV, detects relevant columns by header name, performs multiset matching on deposit and bank amounts, and displays a summary plus detailed discrepancy list in a tkinter UI.

---

## CSV Structure

The CSV has a variable number of Dep columns (1–3). All subsequent columns shift left when fewer Dep columns are present. Column detection is header-based, not position-based.

| Column | Header Contains | Notes |
|--------|----------------|-------|
| A | SITE ID | For display only |
| B | Date | Associated with each deposit/bank entry |
| C | Dep1 | Always present |
| D | Dep2 | Optional |
| E | Dep3 | Optional |
| next | Total | Not used in matching |
| H (shifts) | DIT flag | Cell value "DIT" marks a row as Deposit in Transit |
| I (shifts) | Bank | Bank transaction amounts |

---

## Architecture

Single file: `transmatch.py`

**Dependencies:**
- `pandas` — CSV loading, column detection, data wrangling
- `tkinter` — UI (stdlib)
- `collections.Counter` — multiset matching

**Structure:**
- `load_csv(path) -> pd.DataFrame` — reads CSV, normalizes headers
- `detect_columns(df) -> dict` — returns column name mapping for dep, bank, dit, date
- `run_reconciliation(df, col_map) -> ReconciliationResult` — performs matching, returns result object
- `App(tk.Tk)` — tkinter UI class

---

## Column Detection

Headers are matched case-insensitively:
- **Dep columns:** any header containing `"dep"` (catches Dep1, Dep2, Dep3)
- **Bank column:** header containing `"bank"`
- **DIT column:** header containing `"dit"`, or fallback: scan all columns for rows where cell value equals `"DIT"` and use that column
- **Date column:** header containing `"date"`
- **Site ID:** header containing `"site"`

If a required column (Bank, at least one Dep) cannot be detected, display a clear error in the output pane: *"Could not detect [column] — verify CSV headers."*

---

## Matching Algorithm

All amounts are rounded to 2 decimal places before comparison to avoid floating-point mismatches.

**Step 1 — Collect deposit values:**
For each row, extract all non-null Dep column values. Tag each with its Date and whether the row has "DIT" in the DIT column.

**Step 2 — Collect bank values:**
Extract all non-null Bank column values, each tagged with its Date.

**Step 3 — Separate DIT deposits:**
Split deposits into two groups: DIT-flagged and non-DIT. DIT deposits are noted but excluded from matching.

**Step 4 — Multiset matching:**
Use `Counter` on non-DIT deposit amounts and Bank amounts.

- **Matched:** amounts present in both Counters (up to the minimum count of each)
- **Unmatched Dep:** amounts in Dep Counter not fully covered by Bank Counter
- **Unmatched Bank:** amounts in Bank Counter not fully covered by Dep Counter

---

## Output Format

### Summary (top of output pane)
```
--- Summary ---
✓  Matched:          12
✗  Unmatched Deps:    2
~  DIT (noted):       3
✗  Unmatched Bank:    1
```

### Detail List (scrollable, below summary)
```
--- Details ---
✗  DEP   2025-03-01   $1,250.00   No matching bank entry
✗  BANK  2025-03-05   $875.00     No matching deposit
~  DIT   2025-03-08   $500.00     Deposit in transit (noted)
```

---

## UI Layout

```
┌─────────────────────────────────────────┐
│  [Select CSV File]  path/to/file.csv    │
│  [Run Check]                            │
├─────────────────────────────────────────┤
│  Output                    (scrollable) │
│  --- Summary ---                        │
│  ✓ Matched: 12   ✗ Discrepancies: 2    │
│  ~ DIT: 3        ✗ Unmatched Bank: 1   │
│  --- Details ---                        │
│  ✗ DEP  2025-03-01  $1,250.00  ...     │
│  ...                                    │
└─────────────────────────────────────────┘
```

- **Select CSV File:** opens `tkinter.filedialog.askopenfilename` filtered to `.csv`
- **Run Check:** disabled until a file is selected; re-enabled after each run
- Output pane: `tk.Text` widget, read-only (`state=DISABLED`), with vertical scrollbar
- Results are cleared and rewritten on each run

---

## Error Handling

- Column detection failure: show descriptive message in output pane, abort run
- Empty CSV or no data rows: show "No data found in file"
- Malformed amounts (non-numeric): skip the cell, note the row/column in output
- File unreadable: catch `Exception` on load, show error message

---

## Testing

Manual test cases using a small hand-crafted CSV:
1. All deposits match bank entries — expect zero discrepancies
2. One Dep with no Bank match — expect one unmatched Dep
3. One Bank with no Dep match — expect one unmatched Bank
4. One DIT row — expect it noted, not flagged
5. CSV with only 1 Dep column — verify column detection still works
6. Duplicate amounts (two $500 deposits, two $500 bank entries) — expect both matched
7. Duplicate amounts (two $500 deposits, one $500 bank entry) — expect one unmatched Dep
