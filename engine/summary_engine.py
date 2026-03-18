"""
summary_engine.py - REBUILT FROM SCRATCH

Logic:
- Grand Total rows determine media name inclusion (FAIL = include, PASS = exclude from errors)
- Media Type Overall Result = weighted re-aggregation of all Grand Total rows for that media type
- Failed units = only units where individual Result = FAIL for that specific error column
- Top N error columns shown, ranked by max rate (non-zero only)
"""

import pandas as pd

TOP_N_ERRORS = 2


class PivotSummaryEngine:

    def __init__(self, all_pivots: dict):
        self.all_pivots = all_pivots

    # ------------------------------------------------------------------
    # PUBLIC
    # ------------------------------------------------------------------

    def generate_summary(self):
        """
        Returns:
            {
                "categories": [
                    {
                        "category": str,
                        "media_summaries": [
                            {
                                "media_type": str,
                                "overall_result": "PASS" | "FAIL" | "NO SPEC PROVIDED",
                                "tray": str,
                                "mode": str,
                                "errors": [          # only populated if overall_result == FAIL
                                    {
                                        "error": str,        # e.g. "MP"
                                        "rate": float,       # max rate across failed media names
                                        "failed_media": [
                                            {
                                                "media_name": str,
                                                "units": [str, ...]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        """
        categories = []

        for category_name, data in self.all_pivots.items():
            combined_df = data["combined"].copy()
            config = data["config"]

            combined_df = self._normalise_result_col(combined_df)

            grand_total_df = self._get_grand_total_rows(combined_df)
            unit_df = self._get_unit_rows(combined_df)

            per_k_cols = self._get_error_per_k_cols(combined_df, config)

            tray_mode_combos = self._get_tray_mode_combos(combined_df)

            media_summaries = []

            for (tray, mode) in tray_mode_combos:
                gt_slice = self._filter_by_tray_mode(grand_total_df, tray, mode)
                unit_slice = self._filter_by_tray_mode(unit_df, tray, mode)

                media_types = gt_slice["Media Type"].dropna().unique() if "Media Type" in gt_slice.columns else []

                for media_type in sorted(media_types):
                    gt_media = gt_slice[gt_slice["Media Type"] == media_type]
                    unit_media = unit_slice[unit_slice["Media Type"] == media_type] if "Media Type" in unit_slice.columns else pd.DataFrame()

                    overall_result = self._calc_media_type_result(
                        gt_media, config
                    )

                    errors = []
                    if overall_result == "FAIL":
                        errors = self._build_error_list(
                            gt_media, unit_media, per_k_cols
                        )

                    media_summaries.append({
                        "media_type": media_type,
                        "overall_result": overall_result,
                        "tray": tray,
                        "mode": mode,
                        "errors": errors
                    })

            categories.append({
                "category": category_name,
                "media_summaries": media_summaries
            })

        return {"categories": categories}

    # ------------------------------------------------------------------
    # SPLIT GRAND TOTAL vs UNIT ROWS
    # ------------------------------------------------------------------

    def _get_grand_total_rows(self, df):
        if "Unit" not in df.columns:
            return pd.DataFrame()
        mask = df["Unit"].astype(str).str.strip().str.lower() == "grand total"
        return df[mask].copy().reset_index(drop=True)

    def _get_unit_rows(self, df):
        if "Unit" not in df.columns:
            return df.copy()
        mask = df["Unit"].astype(str).str.strip().str.lower() != "grand total"
        return df[mask].copy().reset_index(drop=True)

    # ------------------------------------------------------------------
    # TRAY / MODE COMBINATIONS
    # ------------------------------------------------------------------

    def _get_tray_mode_combos(self, df):
        """Return sorted list of (tray, mode) tuples present in df."""
        tray_col = self._find_tray_col(df)
        combos = set()

        trays = df[tray_col].dropna().unique() if tray_col else [None]
        modes = df["Print Mode"].dropna().unique() if "Print Mode" in df.columns else [None]

        for t in trays:
            for m in modes:
                combos.add((t, m))

        return sorted(combos, key=lambda x: (str(x[0]), str(x[1])))

    def _filter_by_tray_mode(self, df, tray, mode):
        result = df.copy()
        tray_col = self._find_tray_col(result)

        if tray_col and tray is not None:
            result = result[result[tray_col] == tray]
        if "Print Mode" in result.columns and mode is not None:
            result = result[result["Print Mode"] == mode]

        return result.reset_index(drop=True)

    def _find_tray_col(self, df):
        for col in ["Input Tray", "Input_Tray", "Tray"]:
            if col in df.columns:
                return col
        return None

    # ------------------------------------------------------------------
    # MEDIA TYPE OVERALL RESULT
    # ------------------------------------------------------------------

    def _calc_media_type_result(self, gt_media, config):
        """
        Weighted re-aggregation of all Grand Total rows for this media type.
        Mirrors the same weighted average logic used in add_grand_totals().
        Result is determined by comparing re-aggregated rate against spec.
        Falls back to worst individual result if no spec available.
        """
        if gt_media.empty:
            return "NO DATA"

        results = gt_media["Result"].astype(str).str.upper().unique()

        # No spec case
        if all(r in ("NO SPEC PROVIDED", "SPEC NOT FOUND", "NO DATA") for r in results):
            return results[0]

        # If any grand total row failed, overall is FAIL
        if "FAIL" in results:
            return "FAIL"

        if "PASS" in results:
            return "PASS"

        return results[0]

    # ------------------------------------------------------------------
    # ERROR LIST BUILDER
    # ------------------------------------------------------------------

    def _build_error_list(self, gt_media, unit_media, per_k_cols):
        """
        For each error column:
        1. Find media names whose Grand Total row has a non-zero rate for that error
           AND whose Grand Total Result = FAIL
        2. Under each such media name, list units where individual Result = FAIL
        Return top N errors sorted by max rate descending.
        """
        error_candidates = []

        for col in per_k_cols:
            if col not in gt_media.columns:
                continue

            # Grand Total rows that have a non-zero rate for this error AND failed overall
            failed_gt = gt_media[
                (gt_media["Result"].astype(str).str.upper() == "FAIL") &
                (pd.to_numeric(gt_media[col], errors="coerce").fillna(0) > 0)
            ]

            if failed_gt.empty:
                continue

            max_rate = pd.to_numeric(gt_media[col], errors="coerce").max()

            failed_media_list = []

            if "Media Name" in failed_gt.columns:
                for media_name in failed_gt["Media Name"].dropna().unique():
                    media_name_str = str(media_name).strip()

                    # Units where individual Result = FAIL for this error
                    failed_units = []

                    if not unit_media.empty and "Media Name" in unit_media.columns:
                        unit_rows = unit_media[
                            (unit_media["Media Name"].astype(str).str.strip() == media_name_str) &
                            (unit_media["Result"].astype(str).str.upper() == "FAIL")
                        ]

                        if "Unit" in unit_rows.columns:
                            failed_units = sorted(
                                unit_rows["Unit"].astype(str).str.strip().unique().tolist()
                            )

                    failed_media_list.append({
                        "media_name": media_name_str,
                        "units": failed_units
                    })

            if failed_media_list:
                error_name = col.replace("/K", "").strip()
                error_candidates.append({
                    "error": error_name,
                    "rate": round(float(max_rate), 3),
                    "failed_media": failed_media_list
                })

        # Sort by rate descending, return top N
        error_candidates.sort(key=lambda x: x["rate"], reverse=True)
        return error_candidates[:TOP_N_ERRORS]

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _get_error_per_k_cols(self, df, config):
        """Return per-K columns excluding the total column."""
        total_col = config.total_column_name
        return [
            col for col in df.columns
            if str(col).endswith("/K") and col != total_col
            and "total" not in str(col).lower()
            and "intervention" not in str(col).lower()
        ]

    def _normalise_result_col(self, df):
        if "Result" in df.columns:
            df["Result"] = df["Result"].astype(str).str.strip().str.upper()
        return df