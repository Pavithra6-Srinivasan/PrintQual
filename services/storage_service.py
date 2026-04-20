"""
storage_service.py - REBUILT SUMMARY SHEET

Summary sheet layout:
  Row 1: section header — Input Tray | Print Mode
  Row 2: column headers — Category | Media Type | Overall Result | Error Type & Rate | Failed Media Name | Failed Units
  Data rows: one row per unit under each failed media name, with cell-merge blanking pattern

Rules:
- All media types listed (PASS and FAIL)
- PASS rows: no error/media/unit detail
- FAIL rows: top N errors, only media names whose Grand Total = FAIL, only units with individual Result = FAIL
- Grand Total rows never appear in summary sheet
- Tables split by (Input Tray + Print Mode) combination
"""

from core.excel_formatter import ExcelFormatter
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side


class StorageService:

    def save_full_report(self, output_path, summary_data, all_pivots):
        """Save formatted Excel report with summary sheet + pivot sheets."""

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            formatter = ExcelFormatter()

            # One sheet per category
            for category_name, pivot_data in all_pivots.items():
                config         = pivot_data["config"]
                combined_df    = pivot_data["combined"].copy()
                spec_has_tray  = pivot_data.get("spec_has_tray", True)

                if not spec_has_tray:
                    tray_col = next(
                        (c for c in ("Input Tray", "Input_Tray", "Tray")
                         if c in combined_df.columns),
                        None
                    )
                    if tray_col:
                        combined_df[tray_col] = ""

                sheet_name = category_name[:31]
                combined_df.to_excel(writer, sheet_name=sheet_name, index=False)

                ws = writer.sheets[sheet_name]
                formatter.apply_standard_formatting(
                    worksheet=ws,
                    dataframe=combined_df,
                    grand_total_identifier="Grand Total",
                    bold_columns=[config.total_column_name],
                    highlight_threshold=0.5,
                    total_column_name=config.total_column_name
                )

    # ------------------------------------------------------------------
    # SUMMARY SHEET
    # ------------------------------------------------------------------

    def _write_summary_sheet(self, writer, summary_data):
        """Build and write the summary sheet."""

        # Collect all (tray, mode) combinations across all categories
        tray_mode_combos = self._collect_tray_mode_combos(summary_data)

        rows = []  # list of row dicts: {cols: [...], row_type: str}

        for (tray, mode) in tray_mode_combos:

            # Section header
            rows.append({
                "cols": [f"Input Tray: {tray}", f"Print Mode: {mode}", "", "", "", ""],
                "row_type": "section_header"
            })

            # Column headers
            rows.append({
                "cols": ["Category", "Media Type", "Overall Result",
                         "Error Type & Rate", "Failed Media Name", "Failed Units"],
                "row_type": "col_header"
            })

            # Data rows for this tray/mode combination
            for cat in summary_data["categories"]:
                category_name = cat["category"]

                # Filter media summaries for this tray/mode
                media_list = [
                    m for m in cat["media_summaries"]
                    if m["tray"] == tray and m["mode"] == mode
                ]

                if not media_list:
                    continue

                first_cat_row = True

                for media in media_list:
                    media_type = media["media_type"]
                    overall_result = media["overall_result"]
                    errors = media.get("errors", [])

                    if overall_result != "FAIL" or not errors:
                        # Single row — PASS or no error detail
                        rows.append({
                            "cols": [
                                category_name if first_cat_row else "",
                                media_type,
                                overall_result,
                                "", "", ""
                            ],
                            "row_type": "pass_row" if overall_result == "PASS" else "data_row",
                            "result": overall_result
                        })
                        first_cat_row = False
                        continue

                    # FAIL — expand into error / media / unit rows
                    first_media_row = True

                    for err in errors:
                        error_label = f"{err['error']}: {err['rate']:.3f}/K"
                        first_error_row = True

                        for media_entry in err["failed_media"]:
                            media_name = media_entry["media_name"]
                            units = media_entry["units"]

                            if not units:
                                # Media name with no individually-failed units
                                rows.append({
                                    "cols": [
                                        category_name if first_cat_row else "",
                                        media_type if first_media_row else "",
                                        overall_result if first_media_row else "",
                                        error_label if first_error_row else "",
                                        media_name,
                                        ""
                                    ],
                                    "row_type": "data_row",
                                    "result": overall_result
                                })
                                first_cat_row = False
                                first_media_row = False
                                first_error_row = False
                            else:
                                first_unit_row = True
                                for unit in units:
                                    rows.append({
                                        "cols": [
                                            category_name if first_cat_row else "",
                                            media_type if first_media_row else "",
                                            overall_result if first_media_row else "",
                                            error_label if first_error_row else "",
                                            media_name if first_unit_row else "",
                                            unit
                                        ],
                                        "row_type": "data_row",
                                        "result": overall_result
                                    })
                                    first_cat_row = False
                                    first_media_row = False
                                    first_error_row = False
                                    first_unit_row = False

            # Blank spacer between sections
            rows.append({"cols": ["", "", "", "", "", ""], "row_type": "spacer"})

        # Write to Excel
        df = pd.DataFrame([r["cols"] for r in rows],
                          columns=["Category", "Media Type", "Overall Result",
                                   "Error Type & Rate", "Failed Media Name", "Failed Units"])

        df.to_excel(writer, sheet_name="Summary", index=False, header=False)

        ws = writer.sheets["Summary"]
        self._format_summary_sheet(ws, rows)

    # ------------------------------------------------------------------
    # FORMATTING
    # ------------------------------------------------------------------

    def _format_summary_sheet(self, ws, rows):
        """Apply formatting row by row based on row_type metadata."""

        # Colour definitions
        blue_fill       = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        grey_fill       = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
        pass_fill       = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
        fail_fill       = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

        white_bold      = Font(bold=True, color="FFFFFF")
        bold_black      = Font(bold=True)
        pass_font       = Font(bold=True, color="006100")
        fail_font       = Font(bold=True, color="C00000")

        thin = Side(style="thin")
        thin_border = Border(left=thin, right=thin, top=thin, bottom=thin)
        thick_top_border = Border(left=thin, right=thin,
                                  top=Side(style="medium"), bottom=thin)

        wrap_top = Alignment(wrap_text=True, vertical="top")

        num_cols = 6

        for row_idx, row_meta in enumerate(rows, start=1):
            row_type = row_meta.get("row_type", "data_row")
            result   = row_meta.get("result", "")

            for col_idx in range(1, num_cols + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.alignment = wrap_top

                if row_type == "section_header":
                    cell.font = Font(bold=True, size=11)
                    cell.fill = grey_fill
                    # No border on section header — visual breathing room

                elif row_type == "col_header":
                    cell.font = white_bold
                    cell.fill = blue_fill
                    cell.border = thin_border

                elif row_type == "pass_row":
                    cell.border = thin_border
                    if col_idx == 3:  # Overall Result column
                        cell.font = pass_font
                        cell.fill = pass_fill

                elif row_type == "data_row":
                    cell.border = thin_border
                    if col_idx == 3 and cell.value in ("FAIL", "PASS"):
                        if cell.value == "FAIL":
                            cell.font = fail_font
                            cell.fill = fail_fill
                        else:
                            cell.font = pass_font
                            cell.fill = pass_fill

                # Thick top border on first row of each category group
                # (col A has a value and it's a data row)
                if col_idx == 1 and row_type == "data_row" and cell.value:
                    for c in range(1, num_cols + 1):
                        ws.cell(row=row_idx, column=c).border = thick_top_border

        # Column widths
        ws.column_dimensions["A"].width = 22   # Category
        ws.column_dimensions["B"].width = 16   # Media Type
        ws.column_dimensions["C"].width = 16   # Overall Result
        ws.column_dimensions["D"].width = 26   # Error Type & Rate
        ws.column_dimensions["E"].width = 45   # Failed Media Name
        ws.column_dimensions["F"].width = 16   # Failed Units

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _collect_tray_mode_combos(self, summary_data):
        """Collect all unique (tray, mode) pairs across all categories, sorted."""
        combos = set()
        for cat in summary_data["categories"]:
            for m in cat["media_summaries"]:
                combos.add((m["tray"], m["mode"]))
        return sorted(combos, key=lambda x: (str(x[0]), str(x[1])))

    # ------------------------------------------------------------------
    # DATABASE SAVE (unchanged interface)
    # ------------------------------------------------------------------

    def save_results_to_database(self, db, all_pivots, year, quarter, summary_data):
        """Save results to database."""
        for cat in summary_data["categories"]:
            category_name = cat["category"]

            for media in cat["media_summaries"]:
                media_type     = media["media_type"]
                overall_result = media["overall_result"]
                errors         = media.get("errors", [])

                all_media_names   = set()
                all_error_types   = set()
                failed_units_set  = set()

                for err in errors:
                    all_error_types.add(f"{err['error']} ({err['rate']:.3f}/K)")
                    for me in err.get("failed_media", []):
                        all_media_names.add(me["media_name"])
                        failed_units_set.update(me["units"])

                db.insert_summary_result(
                    category=category_name,
                    media_type=media_type,
                    overall_result=overall_result,
                    failed_units=",".join(sorted(failed_units_set)),
                    failed_media_names=",".join(sorted(all_media_names)),
                    failed_error_types=",".join(sorted(all_error_types)),
                    failed_conditions="",
                    remarks=self._build_remarks(errors, overall_result),
                    year=year,
                    quarter=quarter
                )

    def _build_remarks(self, errors, overall_result):
        if not errors or overall_result.upper() != "FAIL":
            return ""
        parts = []
        for err in errors:
            media_parts = [
                f"{me['media_name']} ({', '.join(me['units'])})"
                for me in err["failed_media"]
            ]
            parts.append(f"{err['error']} {err['rate']:.3f}/K: {' | '.join(media_parts)}")
        return " // ".join(parts)