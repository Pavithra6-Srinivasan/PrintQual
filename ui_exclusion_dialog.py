"""
ui_exclusion_dialog.py - Modal dialog for selecting units/media names to exclude.

All items start checked (included). Engineer unchecks items to exclude them.
After the dialog closes, self.result holds (excluded_units, excluded_media_names)
or None if the engineer cancelled.
"""

import tkinter as tk
from tkinter import ttk


class ExclusionDialog:
    def __init__(self, parent, units, media_names):
        self.result = None

        dlg = tk.Toplevel(parent)
        dlg.title("Filter Data Before Generating")
        dlg.transient(parent)
        dlg.grab_set()
        dlg.resizable(True, True)

        # Size: taller if many items, capped at 620
        h = min(620, max(380, 80 + max(len(units), len(media_names)) * 22))
        dlg.geometry(f"700x{h}")

        # ── Header ────────────────────────────────────────────────────────────
        header = ttk.Frame(dlg, padding="12 10 12 4")
        header.pack(fill="x")
        ttk.Label(
            header,
            text="Filter Data Before Generating",
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            header,
            text="Unchecked items will be excluded from the report. All items are included by default.",
            font=("Segoe UI", 9),
            foreground="#555555",
        ).pack(anchor="w", pady=(2, 0))
        ttk.Separator(dlg, orient="horizontal").pack(fill="x", padx=12, pady=6)

        # ── Two panes ─────────────────────────────────────────────────────────
        panes = ttk.Frame(dlg, padding="12 0 12 0")
        panes.pack(fill="both", expand=True)
        panes.columnconfigure(0, weight=1)
        panes.columnconfigure(1, weight=1)

        self._unit_vars  = {}
        self._media_vars = {}

        self._unit_vars  = _build_pane(panes, col=0, title="Units",       items=units)
        self._media_vars = _build_pane(panes, col=1, title="Media Names", items=media_names)

        # ── Footer ────────────────────────────────────────────────────────────
        ttk.Separator(dlg, orient="horizontal").pack(fill="x", padx=12, pady=8)
        footer = ttk.Frame(dlg, padding="12 0 12 10")
        footer.pack(fill="x")

        ttk.Button(
            footer, text="Cancel",
            command=lambda: dlg.destroy()
        ).pack(side="right", padx=(6, 0))

        ttk.Button(
            footer, text="Generate Report",
            command=lambda: self._confirm(dlg),
            style="Accent.TButton",
        ).pack(side="right")

        dlg.wait_window()

    def _confirm(self, dlg):
        excluded_units  = [u for u, v in self._unit_vars.items()  if not v.get()]
        excluded_media  = [m for m, v in self._media_vars.items() if not v.get()]
        self.result = (excluded_units, excluded_media)
        dlg.destroy()


# ── Helper ────────────────────────────────────────────────────────────────────

def _build_pane(parent, col, title, items):
    """Build one labelled pane with a scrollable checklist. Returns vars dict."""
    frame = ttk.LabelFrame(parent, text=f"  {title}  ", padding="6")
    frame.grid(row=0, column=col, sticky="nsew", padx=(0 if col else 0, 6 if col == 0 else 0), pady=4)
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(1, weight=1)

    # Select All / Deselect All
    btn_row = ttk.Frame(frame)
    btn_row.grid(row=0, column=0, sticky="ew", pady=(0, 4))

    vars_dict = {}

    def select_all():
        for v in vars_dict.values():
            v.set(True)

    def deselect_all():
        for v in vars_dict.values():
            v.set(False)

    ttk.Button(btn_row, text="Select All",   command=select_all,   width=10).pack(side="left", padx=(0, 4))
    ttk.Button(btn_row, text="Deselect All", command=deselect_all, width=12).pack(side="left")

    if not items:
        ttk.Label(frame, text="(no items found)", foreground="#888888").grid(row=1, column=0)
        return vars_dict

    # Scrollable canvas
    canvas = tk.Canvas(frame, borderwidth=0, highlightthickness=0)
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
    inner = ttk.Frame(canvas)

    inner.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.grid(row=1, column=0, sticky="nsew")
    scrollbar.grid(row=1, column=1, sticky="ns")
    frame.columnconfigure(0, weight=1)

    # Mouse-wheel scrolling
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    canvas.bind("<MouseWheel>", _on_mousewheel)
    inner.bind("<MouseWheel>",  _on_mousewheel)

    for item in items:
        var = tk.BooleanVar(value=True)
        cb = ttk.Checkbutton(inner, text=item, variable=var)
        cb.pack(anchor="w", padx=4, pady=1)
        cb.bind("<MouseWheel>", _on_mousewheel)
        vars_dict[item] = var

    return vars_dict
