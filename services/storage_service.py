from core.excel_formatter import ExcelFormatter
import pandas as pd
from pathlib import Path
from openpyxl.styles import Font, PatternFill, Alignment

class StorageService:

    def save_full_report(self, output_path, summary_data, all_pivots):
        """
        Save formatted summary first,
        followed by fully formatted pivot tables.
        """

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:

            formatter = ExcelFormatter()

            # SUMMARY SHEET

            summary_rows = []

            summary_rows.append(["SUMMARY"])
            summary_rows.append([])
            summary_rows.append([
                "Category",
                "Media Type",
                "Overall Result",
                "Common Failure Factor"
            ])

            for cat in summary_data["categories"]:
                for media in cat["media_summary"]:

                    # ALWAYS initialize first
                    failure_text = ""

                    if media["overall_result"].upper() == "FAIL":

                        failed_items = media.get("failed_combinations", [])

                        factors = self.detect_common_factors_vertical(
                            failed_items,
                            media["media_type"]
                        )

                        failure_text = "\n".join(factors)

                    summary_rows.append([
                        cat["category"],
                        media["media_type"],
                        media["overall_result"],
                        failure_text
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

            blue_fill = PatternFill(start_color="BDD7EE", end_color="BDD7EE", fill_type="solid")

            for row_idx, row in enumerate(summary_ws.iter_rows(), start=1):
                for cell in row:

                    # Bold main title
                    if cell.value == "SUMMARY":
                        cell.font = Font(bold=True, size=14)

                    # Header row formatting (row 3)
                    if row_idx == 3:
                        cell.font = Font(bold=True)
                        cell.fill = blue_fill

                    # PASS / FAIL coloring
                    if cell.value == "Fail":
                        cell.font = Font(bold=True, color="FF0000")

                    elif cell.value == "Pass":
                        cell.font = Font(bold=True, color="00B050")

                    # Wrap text for vertical listing
                    cell.alignment = Alignment(wrap_text=True, vertical="top")

            # Auto column width
            for column_cells in summary_ws.columns:
                length = max(len(str(cell.value)) if cell.value else 0 for cell in column_cells)
                summary_ws.column_dimensions[column_cells[0].column_letter].width = length + 2

            # WRITE & FORMAT ALL PIVOT TABLES

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

    def detect_common_factors_vertical(self, failed_list, media_type):
        """
        Returns dominant failure factors vertically.
        """

        if not failed_list:
            return []

        factor_counts = {}

        for item in failed_list:
            parts = [p.strip() for p in item.split("|")]

            for part in parts:
                if part:  # avoid empty strings
                    factor_counts[part] = factor_counts.get(part, 0) + 1

        if not factor_counts:
            return []

        # Sort by frequency
        sorted_factors = sorted(
            factor_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Get highest frequency
        top_count = sorted_factors[0][1]

        # Only keep strong drivers (at least 60% dominance)
        threshold = max(1, int(len(failed_list) * 0.6))

        dominant = [
            factor for factor, count in sorted_factors
            if count >= threshold
        ]

        # If nothing passes threshold → just return top 1
        if not dominant:
            dominant = [sorted_factors[0][0]]

        # Add media driver ONLY if all fails are same media
        if len(failed_list) > 0:
            dominant.insert(0, f"Media: {media_type}")

        return dominant