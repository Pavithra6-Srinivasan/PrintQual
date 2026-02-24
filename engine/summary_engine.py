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
            media_df = data["media"]
            unit_df = data["unit"]

            summary = self.analyze_category(category_name, media_df, unit_df)
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

    def analyze_category(self, category_name, media_df, unit_df):

        result = {
            "category": category_name,
            "media_summary": [],
            "unit_summary": [],
            "total_pass": 0,
            "total_fail": 0,
            "fail_rate": 0
        }

        # -----------------------------
        # CATEGORY LEVEL
        # -----------------------------
        if "Result" in media_df.columns:
            # Normalize result column
            media_df["Result"] = (
                media_df["Result"]
                .astype(str)
                .str.strip()
                .str.lower()
            )

            pass_count = (media_df["Result"] == "pass").sum()
            fail_count = (media_df["Result"] == "fail").sum()

            total = pass_count + fail_count
            result["total_pass"] = int(pass_count)
            result["total_fail"] = int(fail_count)
            result["fail_rate"] = round((fail_count / total) * 100, 2) if total > 0 else 0

        # -----------------------------
        # MEDIA TYPE LEVEL
        # -----------------------------
        if "Media Type" in media_df.columns:

            grouped = media_df.groupby("Media Type")

            for media_type, group in grouped:

                # Determine overall status
                overall_status = "Fail" if (group["Result"] == "fail").any() else "Pass"

                # Capture failing combinations
                failed_rows = group[group["Result"] == "fail"]

                failed_combos = []
                for _, row in failed_rows.iterrows():

                    combo = []
                    if "Media Cat" in group.columns:
                        combo.append(f"Media Cat: {row.get('Media Cat')}")
                    if "Print Mode" in group.columns:
                        combo.append(f"Print Mode: {row.get('Print Mode')}")
                    if "Test mode" in group.columns:
                        combo.append(f"Test Mode: {row.get('Test mode')}")

                    failed_combos.append(", ".join(combo))

                result["media_summary"].append({
                    "media_type": media_type,
                    "overall_result": overall_status,
                    "failed_combinations": failed_combos
                })

        # -----------------------------
        # UNIT LEVEL
        # -----------------------------
        if "Unit" in unit_df.columns:
            unit_df["Result"] = (
                unit_df["Result"]
                .astype(str)
                .str.strip()
                .str.lower()
            )
            grouped = unit_df.groupby("Unit")

            for unit, group in grouped:

                overall_status = "Fail" if (group["Result"] == "fail").any() else "Pass"

                failed_rows = group[group["Result"] == "fail"]

                failed_conditions = []
                for _, row in failed_rows.iterrows():
                    failed_conditions.append(
                        f"{row.get('Media Type')} / {row.get('Print Mode')}"
                    )

                result["unit_summary"].append({
                    "unit": unit,
                    "overall_result": overall_status,
                    "failed_combinations": failed_conditions
                })

        return result

    def format_summary_text(self, summary_dict):
        """
        Convert summary dict into readable text for GUI.
        """
        lines = []
        lines.append("PIVOT TABLE SUMMARY")
        lines.append("")

        for cat in summary_dict["categories"]:
            lines.append(f"Category: {cat['category']}")
            lines.append("")

            lines.append("MEDIA RESULTS:")
            for media in cat["media_summary"]:
                lines.append(f"  - {media['media_type']}: {media['overall_result']}")
                if media["failed_combinations"]:
                    for combo in media["failed_combinations"]:
                        lines.append(f"      ↳ Failed: {combo}")

            lines.append("")
            lines.append("UNIT RESULTS:")
            for unit in cat["unit_summary"]:
                lines.append(f"  - Unit {unit['unit']}: {unit['overall_result']}")
                if unit["failed_combinations"]:
                    for combo in unit["failed_combinations"]:
                        lines.append(f"      ↳ Failed: {combo}")

            lines.append("")

        worst = summary_dict["worst_category"]
        lines.append(f"WORST PERFORMING CATEGORY: {worst['category']}")
        lines.append(f"Fail Rate: {worst['fail_rate']}%")

        return "\n".join(lines)
