"""
summary_engine.py - ENHANCED

Provides detailed failure analysis:
- Specific media names causing failures
- Specific units with problems
- Specific error columns with high defect rates
- Test conditions that failed
"""

import pandas as pd

class PivotSummaryEngine:
    def __init__(self, all_pivots: dict):
        self.all_pivots = all_pivots

    def generate_summary(self):
        """Returns structured summary dictionary with detailed failure info."""
        category_summaries = []
        overall_results = []

        for category_name, data in self.all_pivots.items():
            media_df = data["media"]
            unit_df = data["unit"]

            summary = self.analyze_category(category_name, media_df, unit_df)
            category_summaries.append(summary)
            overall_results.append(summary)

        worst_category = max(overall_results, key=lambda x: x["fail_rate"])

        return {
            "categories": category_summaries,
            "worst_category": worst_category
        }

    def analyze_category(self, category_name, media_df, unit_df):
        result = {
            "category": category_name,
            "media_summary": [],
            "unit_summary": [],
            "total_pass": 0,
            "total_fail": 0,
            "fail_rate": 0
        }

        # CATEGORY LEVEL
        if "Result" in media_df.columns:
            media_df["Result"] = media_df["Result"].astype(str).str.strip().str.lower()
            pass_count = (media_df["Result"] == "pass").sum()
            fail_count = (media_df["Result"] == "fail").sum()
            total = pass_count + fail_count
            result["total_pass"] = int(pass_count)
            result["total_fail"] = int(fail_count)
            result["fail_rate"] = round((fail_count / total) * 100, 2) if total > 0 else 0

        # MEDIA TYPE LEVEL - Enhanced analysis
        if "Media Type" in media_df.columns:
            media_grouped = media_df.groupby("Media Type")
            
            for media_type, media_group in media_grouped:
                # Result based ONLY on media-level tests
                overall_status = "Fail" if (media_group["Result"] == "fail").any() else "Pass"
                
                # ENHANCED: Collect detailed failure information
                failure_details = self._analyze_failures(
                    media_type=media_type,
                    media_group=media_group,
                    unit_df=unit_df,
                    category_name=category_name
                )
                
                result["media_summary"].append({
                    "media_type": media_type,
                    "overall_result": overall_status,
                    "failure_details": failure_details  # Enhanced structured data
                })

        return result

    def _analyze_failures(self, media_type, media_group, unit_df, category_name):
        """
        Analyze failures and return detailed, specific information.
        Returns dict with specific failure factors.
        """
        details = {
            "failed_media_names": [],      # Specific media names that failed
            "failed_units": [],             # Specific units with problems
            "failed_conditions": [],        # Test conditions that failed
            "failed_error_types": [],       # Specific error columns causing issues
            "failed_combinations": []       # Detailed combo info
        }
        
        # 1. Get failed media-level rows
        failed_media_rows = media_group[media_group["Result"] == "fail"]
        
        if len(failed_media_rows) > 0:
            # Extract specific media names that failed
            if "Media Name" in media_group.columns:
                media_names = failed_media_rows["Media Name"].dropna().unique().tolist()
                details["failed_media_names"] = [str(m) for m in media_names]
            
            # Extract test conditions that failed
            if "Test Condition" in media_group.columns:
                conditions = failed_media_rows["Test Condition"].dropna().unique().tolist()
                details["failed_conditions"] = [str(c) for c in conditions]
            
            # Analyze which error columns have high defect rates
            details["failed_error_types"] = self._identify_problem_error_columns(
                failed_media_rows, 
                category_name
            )
            
            # Build detailed combination strings
            for _, row in failed_media_rows.iterrows():
                combo_parts = []
                
                if "Media Name" in media_group.columns and pd.notna(row.get('Media Name')):
                    combo_parts.append(f"Media: {row.get('Media Name')}")
                    
                if "Test Condition" in media_group.columns and pd.notna(row.get('Test Condition')):
                    combo_parts.append(f"Condition: {row.get('Test Condition')}")
                    
                if "Media Cat" in media_group.columns and pd.notna(row.get('Media Cat')):
                    combo_parts.append(f"Category: {row.get('Media Cat')}")
                    
                if "Print Mode" in media_group.columns and pd.notna(row.get('Print Mode')):
                    combo_parts.append(f"Print: {row.get('Print Mode')}")
                
                if combo_parts:
                    details["failed_combinations"].append(" | ".join(combo_parts))
        
        # 2. Check units with failures for this media type
        failed_units = self._get_failed_units_for_media(unit_df, media_type)
        if failed_units:
            details["failed_units"] = failed_units
        
        return details

    def _identify_problem_error_columns(self, failed_rows, category_name):
        """
        Identify which specific error types (columns) are causing problems.
        Returns list of error column names with high defect rates.
        """
        problem_columns = []
        
        # Find columns ending with /K (per-K rate columns)
        per_k_cols = [col for col in failed_rows.columns if str(col).endswith('/K')]
        
        for col in per_k_cols:
            # Skip the total column
            if 'Total' in col or 'total' in col:
                continue
            
            # Check if this column has significant defect rates
            try:
                max_rate = failed_rows[col].max()
                if pd.notna(max_rate) and max_rate > 0.5:  # Threshold: > 0.5 defects per 1000
                    # Extract clean error name (remove /K suffix)
                    error_name = col.replace('/K', '').strip()
                    problem_columns.append(f"{error_name} ({max_rate:.2f}/K)")
            except:
                continue
        
        return problem_columns

    def _get_failed_units_for_media(self, unit_df, media_type):
        """
        Find which units have defects for a specific media type.
        """
        failed_units = []
        
        if media_type not in unit_df.columns or "Unit" not in unit_df.columns:
            return failed_units
        
        for _, row in unit_df.iterrows():
            unit = row["Unit"]
            defect_count = row.get(media_type, 0)
            
            if pd.notna(defect_count) and defect_count > 0:
                failed_units.append(str(unit))
        
        return sorted(failed_units)

    def format_summary_text(self, summary_dict):
        """Convert summary dict into readable text."""
        lines = []
        lines.append("PIVOT TABLE SUMMARY")
        lines.append("")

        for cat in summary_dict["categories"]:
            lines.append(f"Category: {cat['category']}")
            lines.append("")

            lines.append("MEDIA RESULTS:")
            for media in cat["media_summary"]:
                lines.append(f"  - {media['media_type']}: {media['overall_result']}")
                
                details = media["failure_details"]
                
                # Show specific failures
                if details.get("failed_media_names"):
                    lines.append(f"      Failed Media: {', '.join(details['failed_media_names'])}")
                
                if details.get("failed_units"):
                    lines.append(f"      Failed Units: {', '.join(details['failed_units'])}")
                
                if details.get("failed_error_types"):
                    lines.append(f"      Problem Types: {', '.join(details['failed_error_types'])}")
                
                if details.get("failed_conditions"):
                    lines.append(f"      Conditions: {', '.join(details['failed_conditions'])}")

            lines.append("")

        worst = summary_dict["worst_category"]
        lines.append(f"WORST PERFORMING CATEGORY: {worst['category']}")
        lines.append(f"Fail Rate: {worst['fail_rate']}%")

        return "\n".join(lines)