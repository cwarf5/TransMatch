import os
import tkinter as tk
from tkinter import filedialog

from reconciler import load_csv, detect_columns, run_reconciliation, ReconciliationResult

# ── Palette ──────────────────────────────────────────────────────────────────
BG          = "#0D1117"
BG2         = "#161B22"
BG3         = "#21262D"
BORDER      = "#30363D"
TEXT        = "#E6EDF3"
MUTED       = "#8B949E"
GREEN       = "#3FB950"
RED         = "#F85149"
AMBER       = "#D29922"
BLUE        = "#58A6FF"
ACCENT      = "#1F6FEB"

FONT_MONO   = ("Courier New", 10)
FONT_MONO_B = ("Courier New", 10, "bold")
FONT_UI     = ("Segoe UI", 9)
FONT_UI_B   = ("Segoe UI", 9, "bold")
FONT_HDR    = ("Courier New", 18, "bold")
FONT_SUB    = ("Segoe UI", 8)
FONT_CARD_N = ("Courier New", 22, "bold")
FONT_CARD_L = ("Segoe UI", 8)


class StatCard(tk.Frame):
    def __init__(self, parent, label: str, color: str, **kw):
        super().__init__(parent, bg=BG3, highlightbackground=BORDER,
                         highlightthickness=1, **kw)
        self._color = color
        self._num_var = tk.StringVar(value="—")
        tk.Label(self, textvariable=self._num_var, font=FONT_CARD_N,
                 fg=color, bg=BG3).pack(padx=18, pady=(14, 2))
        tk.Label(self, text=label, font=FONT_CARD_L,
                 fg=MUTED, bg=BG3).pack(padx=18, pady=(0, 12))

    def set(self, value: int):
        self._num_var.set(str(value))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TransMatch")
        self.configure(bg=BG)
        self.minsize(760, 560)
        self.resizable(True, True)
        self._csv_path: str | None = None
        self._build_ui()

    # ── Layout ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_toolbar()
        self._build_cards()
        self._build_divider()
        self._build_output()
        self._build_statusbar()

    def _build_header(self):
        hdr = tk.Frame(self, bg=BG2, pady=0)
        hdr.pack(fill=tk.X)
        # accent stripe
        tk.Frame(hdr, bg=ACCENT, height=3).pack(fill=tk.X)
        inner = tk.Frame(hdr, bg=BG2, padx=20, pady=14)
        inner.pack(fill=tk.X)
        tk.Label(inner, text="TRANSMATCH", font=FONT_HDR,
                 fg=TEXT, bg=BG2).pack(side=tk.LEFT)
        tk.Label(inner, text="  Deposit Reconciliation System",
                 font=("Segoe UI", 10), fg=MUTED, bg=BG2).pack(
                     side=tk.LEFT, pady=(6, 0))

    def _build_toolbar(self):
        bar = tk.Frame(self, bg=BG, padx=20, pady=12)
        bar.pack(fill=tk.X)

        # file selector row
        file_row = tk.Frame(bar, bg=BG2, highlightbackground=BORDER,
                            highlightthickness=1)
        file_row.pack(fill=tk.X, side=tk.LEFT, expand=True)

        self._browse_btn = tk.Button(
            file_row, text=" Browse…", font=FONT_UI_B,
            bg=BG3, fg=TEXT, activebackground=BORDER,
            activeforeground=TEXT, relief=tk.FLAT,
            cursor="hand2", padx=12, pady=6,
            command=self._select_file)
        self._browse_btn.pack(side=tk.LEFT)

        # separator line
        tk.Frame(file_row, bg=BORDER, width=1).pack(
            side=tk.LEFT, fill=tk.Y, pady=4)

        self._path_var = tk.StringVar(value="  No file selected")
        tk.Label(file_row, textvariable=self._path_var,
                 font=FONT_MONO, fg=MUTED, bg=BG2,
                 anchor="w").pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)

        # run button
        self._run_btn = tk.Button(
            bar, text="▶  Run Check", font=FONT_UI_B,
            bg=ACCENT, fg="#FFFFFF", activebackground="#1158C7",
            activeforeground="#FFFFFF", relief=tk.FLAT,
            cursor="hand2", padx=20, pady=6,
            state=tk.DISABLED, command=self._run)
        self._run_btn.pack(side=tk.LEFT, padx=(12, 0))

        self._bind_hover(self._browse_btn, BG3, BORDER)

    def _build_cards(self):
        row = tk.Frame(self, bg=BG)
        row.pack(fill=tk.X, padx=20, pady=(0, 12))

        self._card_matched  = StatCard(row, "MATCHED",        GREEN)
        self._card_udep     = StatCard(row, "UNMATCHED DEP",  RED)
        self._card_dit      = StatCard(row, "DIT  (noted)",   AMBER)
        self._card_ubank    = StatCard(row, "UNMATCHED BANK", RED)

        for card in (self._card_matched, self._card_udep,
                     self._card_dit, self._card_ubank):
            card.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 8))

    def _build_divider(self):
        tk.Frame(self, bg=BORDER, height=1).pack(fill=tk.X, padx=20)

    def _build_output(self):
        container = tk.Frame(self, bg=BG, padx=20, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(container, text="DETAILS", font=("Segoe UI", 7, "bold"),
                 fg=MUTED, bg=BG, anchor="w").pack(fill=tk.X, pady=(0, 6))

        txt_frame = tk.Frame(container, bg=BG2,
                             highlightbackground=BORDER, highlightthickness=1)
        txt_frame.pack(fill=tk.BOTH, expand=True)

        self._output = tk.Text(
            txt_frame, state=tk.DISABLED,
            font=FONT_MONO, bg=BG2, fg=TEXT,
            insertbackground=TEXT, selectbackground=ACCENT,
            relief=tk.FLAT, padx=14, pady=10,
            wrap=tk.NONE, cursor="arrow")
        self._output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = tk.Scrollbar(txt_frame, orient=tk.VERTICAL,
                          command=self._output.yview, bg=BG3,
                          troughcolor=BG2, activebackground=BORDER)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._output.config(yscrollcommand=sb.set)

        xsb = tk.Scrollbar(container, orient=tk.HORIZONTAL,
                            command=self._output.xview, bg=BG3,
                            troughcolor=BG2, activebackground=BORDER)
        xsb.pack(fill=tk.X)
        self._output.config(xscrollcommand=xsb.set)

        # text tags for color-coded output
        self._output.tag_config("match",   foreground=GREEN)
        self._output.tag_config("err",     foreground=RED)
        self._output.tag_config("dit",     foreground=AMBER)
        self._output.tag_config("bank",    foreground=BLUE)
        self._output.tag_config("hdr",     foreground=MUTED,
                                font=("Segoe UI", 8, "bold"))
        self._output.tag_config("warn",    foreground=AMBER,
                                font=FONT_MONO_B)
        self._output.tag_config("muted",   foreground=MUTED)
        self._output.tag_config("bold",    font=FONT_MONO_B)

    def _build_statusbar(self):
        self._status_var = tk.StringVar(value="Ready")
        bar = tk.Frame(self, bg=BG2, padx=20, pady=4,
                       highlightbackground=BORDER, highlightthickness=0)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Frame(bar, bg=BORDER, height=1).pack(fill=tk.X, side=tk.TOP)
        tk.Label(bar, textvariable=self._status_var,
                 font=FONT_SUB, fg=MUTED, bg=BG2, anchor="w").pack(
                     side=tk.LEFT, pady=4)

    # ── Interactions ─────────────────────────────────────────────────────────

    def _bind_hover(self, widget, normal_bg: str, hover_bg: str):
        widget.bind("<Enter>", lambda _: widget.config(bg=hover_bg))
        widget.bind("<Leave>", lambda _: widget.config(bg=normal_bg))

    def _select_file(self):
        path = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if path:
            self._csv_path = path
            self._path_var.set(f"  {os.path.basename(path)}")
            self._run_btn.config(state=tk.NORMAL)
            self._status_var.set(f"File loaded: {path}")

    def _run(self):
        self._run_btn.config(state=tk.DISABLED)
        self._status_var.set("Running reconciliation…")
        self._clear_output()
        self.update_idletasks()
        try:
            df = load_csv(self._csv_path)
            col_map = detect_columns(df)
            result = run_reconciliation(df, col_map)
            self._display_result(result)
            total_issues = len(result.unmatched_deps) + len(result.unmatched_bank)
            self._status_var.set(
                f"Complete — {result.matched_count} matched, "
                f"{total_issues} discrepancies, {len(result.dit_entries)} DIT"
            )
        except Exception as exc:
            self._write(f"Error: {exc}\n", "err")
            self._status_var.set(f"Error: {exc}")
        finally:
            self._run_btn.config(state=tk.NORMAL)

    # ── Output rendering ─────────────────────────────────────────────────────

    def _display_result(self, r: ReconciliationResult):
        # update stat cards
        self._card_matched.set(r.matched_count)
        self._card_udep.set(len(r.unmatched_deps))
        self._card_dit.set(len(r.dit_entries))
        self._card_ubank.set(len(r.unmatched_bank))

        has_detail = r.unmatched_deps or r.unmatched_bank or r.dit_entries

        if not has_detail and not r.errors:
            self._write("  ✓  All deposits matched — no discrepancies found.\n", "match")
            return

        col_w = 14  # date column width

        if r.unmatched_deps:
            self._write("  UNMATCHED DEPOSITS\n", "hdr")
            for d in r.unmatched_deps:
                self._write(
                    f"  ✗  DEP   {d.date:<{col_w}}  ${d.amount:>12,.2f}"
                    f"   No matching bank entry\n", "err")

        if r.unmatched_bank:
            if r.unmatched_deps:
                self._write("\n")
            self._write("  UNMATCHED BANK ENTRIES\n", "hdr")
            for b in r.unmatched_bank:
                self._write(
                    f"  ✗  BANK  {b.date:<{col_w}}  ${b.amount:>12,.2f}"
                    f"   No matching deposit\n", "bank")

        if r.dit_entries:
            if r.unmatched_deps or r.unmatched_bank:
                self._write("\n")
            self._write("  DEPOSITS IN TRANSIT  (DIT — noted, not an error)\n", "hdr")
            for d in r.dit_entries:
                self._write(
                    f"  ~  DIT   {d.date:<{col_w}}  ${d.amount:>12,.2f}"
                    f"   Deposit in transit\n", "dit")

        if r.errors:
            self._write("\n")
            self._write("  PARSE WARNINGS\n", "warn")
            for e in r.errors:
                self._write(f"  !  {e}\n", "warn")

    def _write(self, text: str, tag: str = ""):
        self._output.config(state=tk.NORMAL)
        if tag:
            self._output.insert(tk.END, text, tag)
        else:
            self._output.insert(tk.END, text)
        self._output.config(state=tk.DISABLED)

    def _clear_output(self):
        self._output.config(state=tk.NORMAL)
        self._output.delete("1.0", tk.END)
        self._output.config(state=tk.DISABLED)
        for card in (self._card_matched, self._card_udep,
                     self._card_dit, self._card_ubank):
            card._num_var.set("—")


if __name__ == "__main__":
    App().mainloop()
