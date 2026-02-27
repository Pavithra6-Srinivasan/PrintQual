from core.excel_formatter import ExcelFormatter
import pandas as pd
from pathlib import Path

class StorageService:

    def save_full_report(self, output_path, summary_data, all_pivots):
        """
        Save formatted summary first,
        followed by fully formatted pivot tables.
        """

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:

            formatter = ExcelFormatter()

            # ===================================================
            # SUMMARY SHEET
            # ===================================================

            summary_rows = []

            # ----- CATEGORY OVERVIEW -----
            summary_rows.append(["CATEGORY OVERVIEW"])
            summary_rows.append([])
            summary_rows.append(["Category", "Total Pass", "Total Fail", "Fail Rate (%)"])

            for cat in summary_data["categories"]:
                summary_rows.append([
                    cat["category"],
                    cat["total_pass"],
                    cat["total_fail"],
                    cat["fail_rate"]
                ])

            summary_rows.append([])
            summary_rows.append([])

            # ----- MEDIA DETAILS -----
            summary_rows.append(["MEDIA DETAILS"])
            summary_rows.append([])
            summary_rows.append(["Category", "Media Type", "Overall Result", "Failed Combinations"])

            for cat in summary_data["categories"]:
                for media in cat["media_summary"]:
                    summary_rows.append([
                        cat["category"],
                        media["media_type"],
                        media["overall_result"],
                        ", ".join(media["failed_combinations"])
                    ])

            summary_rows.append([])
            summary_rows.append([])

            # ----- UNIT DETAILS -----
            summary_rows.append(["UNIT DETAILS"])
            summary_rows.append([])
            summary_rows.append(["Category", "Unit", "Overall Result", "Failed Conditions"])

            for cat in summary_data["categories"]:
                for unit in cat["unit_summary"]:
                    summary_rows.append([
                        cat["category"],
                        unit["unit"],
                        unit["overall_result"],
                        ", ".join(unit["failed_combinations"])
                    ])

            summary_df = pd.DataFrame(summary_rows)

            summary_df.to_excel(
                writer,
                sheet_name="Summary",
                index=False,
                header=False
            )

            # Apply formatting to Summary sheet
            summary_ws = writer.sheets["Summary"]

            from openpyxl.styles import Font

            for row in summary_ws.iter_rows():
                for cell in row:
                    # Bold section titles
                    if cell.value in ["CATEGORY OVERVIEW", "MEDIA DETAILS", "UNIT DETAILS"]:
                        cell.font = Font(bold=True)

                    # Highlight FAIL results
                    if cell.value == "Fail":
                        cell.font = Font(bold=True, color="FF0000")

            # Auto column width
            for column_cells in summary_ws.columns:
                length = max(len(str(cell.value)) if cell.value else 0 for cell in column_cells)
                summary_ws.column_dimensions[column_cells[0].column_letter].width = length + 2

            # ===================================================
            # WRITE & FORMAT ALL PIVOT TABLES
            # ===================================================

            for category_name, pivot_data in all_pivots.items():

                config = pivot_data["config"]

                media_sheet = f"{category_name} By Media"[:31]
                unit_sheet = f"{category_name} By Unit"[:31]

                # Write pivot tables
                pivot_data["media"].to_excel(writer, sheet_name=media_sheet, index=False)
                pivot_data["unit"].to_excel(writer, sheet_name=unit_sheet, index=False)

                # Apply your existing professional formatter
                formatter.apply_standard_formatting(
                    worksheet=writer.sheets[media_sheet],
                    dataframe=pivot_data["media"],
                    grand_total_identifier="Grand Total",
                    bold_columns=[config.total_column_name],
                    highlight_threshold=0.5,
                    total_column_name=config.total_column_name
                )

                formatter.apply_standard_formatting(
                    worksheet=writer.sheets[unit_sheet],
                    dataframe=pivot_data["unit"],
                    grand_total_identifier="Grand Total",
                    bold_columns=[config.total_column_name],
                    highlight_threshold=0.5,
                    total_column_name=config.total_column_name
                )