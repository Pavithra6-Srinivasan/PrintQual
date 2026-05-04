"""
ui_spec_warning_dialog.py - Warning dialog for spec coverage issues.

Shows the columns where raw data values are not covered by the spec file.
The user can choose to proceed with generation or cancel to fix the data.
"""

import tkinter as tk
from tkinter import ttk


class SpecWarningDialog:
    """
    result = True  — user clicked "Proceed Anyway"
    result = False — user clicked "Cancel" or closed the window
    """

    def __init__(self, parent, issues):
        self.result = False
        self._build(parent, issues)

    def _build(self, parent, issues):
        dlg = tk.Toplevel(parent)
        dlg.title("Spec Coverage Warning")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.protocol("WM_DELETE_WINDOW", lambda: self._close(dlg, False))

        outer = ttk.Frame(dlg, padding=16)
        outer.pack(fill="both", expand=True)

        # ── Header ───────────────────────────────────────────────────────────
        ttk.Label(
            outer,
            text="⚠  Spec coverage warning",
            font=("Segoe UI", 11, "bold"),
            foreground="#ea580c",
        ).pack(anchor="w", pady=(0, 4))

        ttk.Label(
            outer,
            text=(
                "The following columns contain values in the raw data that were not found\n"
                "in the spec file. Affected rows may show 'SPEC NOT FOUND' in the results."
            ),
            font=("Segoe UI", 9),
            justify="left",
        ).pack(anchor="w", pady=(0, 10))

        # ── Issue table ───────────────────────────────────────────────────────
        tbl_frame = ttk.Frame(outer, relief="groove", borderwidth=1)
        tbl_frame.pack(fill="x", pady=(0, 12))
        tbl_frame.columnconfigure(0, weight=0)
        tbl_frame.columnconfigure(1, weight=1)
        tbl_frame.columnconfigure(2, weight=2)

        # Header row
        HDR_BG = "#dbeafe"
        for ci, txt in enumerate(["Column", "Not in spec", "Expected (from spec)"]):
            lbl = tk.Label(
                tbl_frame, text=txt,
                font=("Segoe UI", 8, "bold"),
                bg=HDR_BG, anchor="w", padx=6, pady=4,
            )
            lbl.grid(row=0, column=ci, sticky="ew", padx=(0, 1))

        for ri, issue in enumerate(issues, start=1):
            bg = "#ffffff" if ri % 2 == 0 else "#f9fafb"

            missing_str = ", ".join(f'"{v}"' for v in issue["missing"])

            spec_list = issue["spec_values"]
            spec_str  = ", ".join(f'"{v}"' for v in spec_list[:6])
            if len(spec_list) > 6:
                spec_str += f"  … (+{len(spec_list) - 6} more)"

            col_data = [
                (issue["column"], "#374151", 100),
                (missing_str,     "#dc2626", 220),
                (spec_str,        "#6b7280", 260),
            ]
            for ci, (txt, fg, wrap) in enumerate(col_data):
                lbl = tk.Label(
                    tbl_frame, text=txt,
                    font=("Segoe UI", 8),
                    fg=fg, bg=bg,
                    anchor="w", padx=6, pady=4,
                    wraplength=wrap, justify="left",
                )
                lbl.grid(row=ri, column=ci, sticky="ew", padx=(0, 1), pady=(0, 1))

        # ── Footer ────────────────────────────────────────────────────────────
        ttk.Label(
            outer,
            text=(
                "You can proceed and generate the report with the current data, or\n"
                "cancel to update the raw data file and re-run the check."
            ),
            font=("Segoe UI", 9),
            foreground="#6b7280",
            justify="left",
        ).pack(anchor="w", pady=(0, 14))

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_frame = ttk.Frame(outer)
        btn_frame.pack(anchor="e")

        ttk.Button(
            btn_frame, text="Proceed Anyway",
            command=lambda: self._close(dlg, True),
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            btn_frame, text="Cancel",
            command=lambda: self._close(dlg, False),
        ).pack(side="left")

        # ── Centre on parent ──────────────────────────────────────────────────
        dlg.update_idletasks()
        dw = dlg.winfo_reqwidth()
        dh = dlg.winfo_reqheight()
        px = parent.winfo_x() + (parent.winfo_width()  - dw) // 2
        py = parent.winfo_y() + (parent.winfo_height() - dh) // 2
        dlg.geometry(f"{dw}x{dh}+{px}+{py}")

        parent.wait_window(dlg)

    def _close(self, dlg, result):
        self.result = result
        dlg.destroy()
