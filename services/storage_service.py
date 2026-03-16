"""
storage_service.py - COMPLETE ENHANCED VERSION

Includes enhanced failure details in summary and database.
"""

from core.excel_formatter import ExcelFormatter
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment

class StorageService:

    def save_full_report(self, output_path, summary_data, all_pivots):
        """
        Save formatted summary with ENHANCED failure details.
        """

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:

            formatter = ExcelFormatter()

            # SUMMARY SHEET - ENHANCED
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
                    
                    # Build failure text from details
                    failure_text = self._build_failure_text(media.get("failure_details", {}))

                    summary_rows.append([
                        cat["category"],
                        media["media_type"],
                        media["overall_result"],
                        failure_text
                    ])

            summary_df = pd.DataFrame(summary_rows)
            summary_df.to_excel(writer, sheet_name="Summary", index=False, header=False)

            # Format Summary sheet
            summary_ws = writer.sheets["Summary"]
            blue_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")

            for row_idx, row in enumerate(summary_ws.iter_rows(), start=1):
                for cell in row:
                    if cell.value == "SUMMARY":
                        cell.font = Font(bold=True, size=14)
                    
                    if row_idx == 3:
                        cell.font = Font(bold=True, size=11, color="FFFFFF")
                        cell.fill = blue_fill
                    
                    if cell.value == "Fail":
                        cell.font = Font(bold=True, color="FF0000")
                    elif cell.value == "Pass":
                        cell.font = Font(bold=True, color="00B050")
                    
                    cell.alignment = Alignment(wrap_text=True, vertical="top")

            for column_cells in summary_ws.columns:
                length = max(len(str(cell.value)) if cell.value else 0 for cell in column_cells)
                summary_ws.column_dimensions[column_cells[0].column_letter].width = min(length + 2, 50)

            # PIVOT TABLES
            for category_name, pivot_data in all_pivots.items():

                config = pivot_data["config"]

                media_sheet = f"{category_name} By Media"[:31]
                unit_sheet = f"{category_name} By Unit"[:31]

                pivot_data["media"].to_excel(writer, sheet_name=media_sheet, index=False)
                pivot_data["unit"].to_excel(writer, sheet_name=unit_sheet, index=False)

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

    def _build_failure_text(self, failure_details):
        """Build formatted failure text from failure details."""
        if not failure_details:
            return ""
        
        lines = []
        
        # Check if this is enhanced format (has failure_details dict)
        if isinstance(failure_details, dict):
            # Enhanced format
            if failure_details.get("failed_media_names"):
                media_list = ", ".join(failure_details["failed_media_names"])
                lines.append(f"Media: {media_list}")
            
            if failure_details.get("failed_units"):
                unit_list = ", ".join(failure_details["failed_units"])
                lines.append(f"Units: {unit_list}")
            
            if failure_details.get("failed_error_types"):
                error_list = ", ".join(failure_details["failed_error_types"])
                lines.append(f"Errors: {error_list}")
            
            if failure_details.get("failed_conditions"):
                if len(failure_details["failed_conditions"]) <= 2:
                    cond_list = ", ".join(failure_details["failed_conditions"])
                    lines.append(f"Conditions: {cond_list}")
            
            if not lines and failure_details.get("failed_combinations"):
                for combo in failure_details["failed_combinations"][:2]:
                    lines.append(combo)
        
        return "\n".join(lines) if lines else "Multiple factors"

    def save_results_to_database(self, db, all_pivots, year, quarter, summary_data):
        """
        Save ENHANCED results to database.
        
        Args:
            db: DatabaseManager instance
            all_pivots: Dictionary of pivot data
            year: Year (int)
            quarter: Quarter (1-4)
            summary_data: Summary data with failure_details
        """
        
        for cat in summary_data["categories"]:
            category_name = cat["category"]
            
            for media in cat["media_summary"]:
                media_type = media["media_type"]
                overall_result = media["overall_result"]
                
                # Get failure details (enhanced format)
                details = media.get("failure_details", {})
                
                # Build strings for database
                failed_units_str = ",".join(details.get("failed_units", []))
                failed_media_names = ",".join(details.get("failed_media_names", []))
                failed_error_types = ",".join(details.get("failed_error_types", []))
                failed_conditions = ",".join(details.get("failed_conditions", []))
                
                # Build display text
                common_failure_factor = self._build_failure_text(details)
                
                # Insert into database
                db.insert_summary_result(
                    category=category_name,
                    media_type=media_type,
                    overall_result=overall_result,
                    failed_units=failed_units_str,
                    failed_media_names=failed_media_names,
                    failed_error_types=failed_error_types,
                    failed_conditions=failed_conditions,
                    common_failure_factor=common_failure_factor,
                    year=year,
                    quarter=quarter
                )
                        
    def detect_common_factors_vertical(self, failed_list, media_type):
        """Legacy method - kept for backward compatibility."""
        if not failed_list:
            return []

        factor_counts = {}
        for item in failed_list:
            parts = [p.strip() for p in item.split("|")]
            for part in parts:
                if part:
                    factor_counts[part] = factor_counts.get(part, 0) + 1

        if not factor_counts:
            return []

        sorted_factors = sorted(
            factor_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )

        threshold = max(1, int(len(failed_list) * 0.6))
        
        dominant = [
            factor for factor, count in sorted_factors
            if count >= threshold
        ]

        if not dominant:
            dominant = [sorted_factors[0][0]]

        return dominant