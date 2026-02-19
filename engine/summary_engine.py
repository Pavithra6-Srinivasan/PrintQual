"""
summary_engine.py

Analyzes generated pivot tables and produces summary insights.
"""

import pandas as pd


class PivotSummaryEngine:
    def __init__(self, all_pivots: dict):
        """
        all_pivots structure:
        {
            category_name: {
                'media': DataFrame,
                'unit': DataFrame,
                'config': config_object
            }
        }
        """
        self.all_pivots = all_pivots

    def generate_summary(self):
        """
        Returns structured summary dictionary.
        """
        category_summaries = []
        overall_results = []

        for category_name, data in self.all_pivots.items():
            df = data["media"]

            summary = self.analyze_category(category_name, df)
            category_summaries.append(summary)
            overall_results.append(summary)

        # Determine worst category overall
        worst_category = max(
            overall_results,
            key=lambda x: x["fail_rate"]
        )

        return {
            "categories": category_summaries,
            "worst_category": worst_category
        }

    def analyze_category(self, category_name, df):
        """
        Analyze a single pivot table.
        """
        result = {
            "category": category_name,
            "total_pass": 0,
            "total_fail": 0,
            "fail_rate": 0,
            "worst_columns": []
        }

        if "Result" in df.columns:
            pass_count = (df["Result"] == "Pass").sum()
            fail_count = (df["Result"] == "Fail").sum()

            result["total_pass"] = int(pass_count)
            result["total_fail"] = int(fail_count)

            total = pass_count + fail_count
            result["fail_rate"] = round((fail_count / total) * 100, 2) if total > 0 else 0

        # Identify fail-related columns
        fail_columns = [
            col for col in df.columns
            if "/K" in str(col) and "Total" not in str(col)
        ]

        column_fail_values = {}

        for col in fail_columns:
            try:
                column_fail_values[col] = df[col].sum()
            except Exception:
                column_fail_values[col] = 0

        # Sort highest fail contributors
        sorted_cols = sorted(
            column_fail_values.items(),
            key=lambda x: x[1],
            reverse=True
        )

        result["worst_columns"] = sorted_cols[:3]

        return result

    def format_summary_text(self, summary_dict):
        """
        Convert summary dict into readable text for GUI.
        """
        lines = []
        lines.append("=" * 60)
        lines.append("PIVOT TABLE SUMMARY")
        lines.append("=" * 60)
        lines.append("")

        for cat in summary_dict["categories"]:
            lines.append(f"Category: {cat['category']}")
            lines.append(f"  Pass: {cat['total_pass']}")
            lines.append(f"  Fail: {cat['total_fail']}")
            lines.append(f"  Fail Rate: {cat['fail_rate']}%")

            if cat["worst_columns"]:
                lines.append("  Top Fail Contributors:")
                for col, val in cat["worst_columns"]:
                    lines.append(f"     - {col}: {val}")

            lines.append("")

        worst = summary_dict["worst_category"]
        lines.append("=" * 60)
        lines.append(f"WORST PERFORMING CATEGORY: {worst['category']}")
        lines.append(f"Fail Rate: {worst['fail_rate']}%")
        lines.append("=" * 60)

        return "\n".join(lines)
