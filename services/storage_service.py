from core.excel_formatter import ExcelFormatter
import pandas as pd
from pathlib import Path

class StorageService:

    def save_excel(self, output_path, all_pivots):
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            formatter = ExcelFormatter()

            for category_name, pivot_data in all_pivots.items():
                config = pivot_data['config']

                sheet_media = f'{category_name} By Media'
                sheet_unit = f'{category_name} By Unit'

                pivot_data['media'].to_excel(writer, sheet_name=sheet_media, index=False)
                pivot_data['unit'].to_excel(writer, sheet_name=sheet_unit, index=False)

                formatter.apply_standard_formatting(
                    worksheet=writer.sheets[sheet_media],
                    dataframe=pivot_data['media'],
                    grand_total_identifier='Grand Total',
                    bold_columns=[config.total_column_name],
                    highlight_threshold=0.5,
                    total_column_name=config.total_column_name
                )

                formatter.apply_standard_formatting(
                    worksheet=writer.sheets[sheet_unit],
                    dataframe=pivot_data['unit'],
                    grand_total_identifier='Grand Total',
                    bold_columns=[config.total_column_name],
                    highlight_threshold=0.5,
                    total_column_name=config.total_column_name
                )

    def save_summary_report(self, summary_dict, base_output_folder):
        """
        Save structured pivot summary as Excel report.
        """

        report_folder = Path(base_output_folder) / "reports"
        report_folder.mkdir(exist_ok=True)

        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        report_path = report_folder / f"Pivot_Summary_Report_{timestamp}.xlsx"

        with pd.ExcelWriter(report_path, engine="openpyxl") as writer:

            # Category Overview Sheet
            overview_rows = []
            for cat in summary_dict["categories"]:
                overview_rows.append({
                    "Category": cat["category"],
                    "Total Pass": cat["total_pass"],
                    "Total Fail": cat["total_fail"],
                    "Fail Rate (%)": cat["fail_rate"]
                })

            overview_df = pd.DataFrame(overview_rows)
            overview_df.to_excel(writer, sheet_name="Category Overview", index=False)

            # Media Level Sheet
            media_rows = []
            for cat in summary_dict["categories"]:
                for media in cat["media_summary"]:
                    media_rows.append({
                        "Category": cat["category"],
                        "Media Type": media["media_type"],
                        "Overall Result": media["overall_result"],
                        "Failed Combinations": ", ".join(media["failed_combinations"])
                    })

            media_df = pd.DataFrame(media_rows)
            media_df.to_excel(writer, sheet_name="Media", index=False)

            # Unit Level Sheet
            unit_rows = []
            for cat in summary_dict["categories"]:
                for unit in cat["unit_summary"]:
                    unit_rows.append({
                        "Category": cat["category"],
                        "Unit": unit["unit"],
                        "Overall Result": unit["overall_result"],
                        "Failed Conditions": ", ".join(unit["failed_combinations"])
                    })

            unit_df = pd.DataFrame(unit_rows)
            unit_df.to_excel(writer, sheet_name="Unit", index=False)

        return report_path