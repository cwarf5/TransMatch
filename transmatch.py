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
