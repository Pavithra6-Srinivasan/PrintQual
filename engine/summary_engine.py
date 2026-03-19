"""
summary_engine.py - REBUILT FROM SCRATCH

Logic:
- Grand Total rows determine media name inclusion (FAIL = include, PASS = exclude)
- Media Type Overall Result = worst result across all Grand Total rows for that media type
- Failed units = only units where individual Result = FAIL AND non-zero rate for that error
- Error columns shown only if Grand Total rate for that error exceeds Spec Limit
- No top-N cap — all spec-breaching errors shown
- Grouping is by (Input Tray + Test Category), Print Mode is a data column
"""

import pandas as pd


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
                                "overall_result": str,
                                "tray": str,
                                "mode": str,        # Print Mode — now a data field
                                "errors": [
                                    {
                                        "error": str,
                                        "rate": float,
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
            config      = data["config"]

            combined_df    = self._normalise_result_col(combined_df)
            grand_total_df = self._get_grand_total_rows(combined_df)
            unit_df        = self._get_unit_rows(combined_df)
            per_k_cols     = self._get_error_per_k_cols(combined_df, config)

            # Group by tray only — mode becomes a data column
            tray_col  = self._find_tray_col(combined_df)
            trays     = grand_total_df[tray_col].dropna().unique() \
                        if tray_col and not grand_total_df.empty else [None]

            media_summaries = []

            for tray in sorted(trays, key=str):
                gt_tray   = self._filter_by_tray(grand_total_df, tray)
                unit_tray = self._filter_by_tray(unit_df, tray)

                # Get all print modes present for this tray
                modes = gt_tray["Print Mode"].dropna().unique() \
                        if "Print Mode" in gt_tray.columns else [None]

                for mode in sorted(modes, key=str):
                    gt_slice   = self._filter_by_mode(gt_tray, mode)
                    unit_slice = self._filter_by_mode(unit_tray, mode)

                    media_types = gt_slice["Media Type"].dropna().unique() \
                                  if "Media Type" in gt_slice.columns else []

                    for media_type in sorted(media_types, key=str):
                        gt_media   = gt_slice[gt_slice["Media Type"] == media_type]
                        unit_media = unit_slice[unit_slice["Media Type"] == media_type] \
                                     if "Media Type" in unit_slice.columns \
                                     else pd.DataFrame()

                        overall_result = self._calc_media_type_result(gt_media)

                        errors = []
                        if overall_result == "FAIL":
                            errors = self._build_error_list(
                                gt_media, unit_media, per_k_cols
                            )

                        media_summaries.append({
                            "media_type":     media_type,
                            "overall_result": overall_result,
                            "tray":           tray,
                            "mode":           mode,   # Print Mode stored here
                            "errors":         errors
                        })

            categories.append({
                "category":        category_name,
                "media_summaries": media_summaries
            })

        return {"categories": categories}

    # ------------------------------------------------------------------
    # ROW SPLITTING
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
    # FILTERING
    # ------------------------------------------------------------------

    def _filter_by_tray(self, df, tray):
        if df.empty:
            return df
        tray_col = self._find_tray_col(df)
        if tray_col and tray is not None:
            return df[df[tray_col] == tray].reset_index(drop=True)
        return df.copy()

    def _filter_by_mode(self, df, mode):
        if df.empty:
            return df
        if "Print Mode" in df.columns and mode is not None:
            return df[df["Print Mode"] == mode].reset_index(drop=True)
        return df.copy()

    def _find_tray_col(self, df):
        for col in ["Input Tray", "Input_Tray", "Tray"]:
            if col in df.columns:
                return col
        return None

    # ------------------------------------------------------------------
    # MEDIA TYPE OVERALL RESULT
    # ------------------------------------------------------------------

    def _calc_media_type_result(self, gt_media):
        if gt_media.empty:
            return "NO DATA"

        results = gt_media["Result"].astype(str).str.upper().unique()

        if all(r in ("NO SPEC PROVIDED", "SPEC NOT FOUND", "NO DATA")
               for r in results):
            return results[0]

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
        For each error column, include it only if the Grand Total row's rate
        for that column exceeds the Spec Limit on that same Grand Total row.
        No top-N cap — all spec-breaching errors are shown.

        For each included error, list media names whose Grand Total = FAIL
        AND have a non-zero rate for that error. Under each media name, list
        units where Result = FAIL AND rate > 0 for that specific error column.
        """
        error_candidates = []

        for col in per_k_cols:
            if col not in gt_media.columns:
                continue

            # Check each Grand Total row: does this error column exceed spec?
            spec_breach_rows = []
            for _, row in gt_media.iterrows():
                result = str(row.get("Result", "")).strip().upper()
                if result != "FAIL":
                    continue

                rate = pd.to_numeric(row.get(col, 0), errors="coerce")
                if pd.isna(rate) or rate <= 0:
                    continue

                spec_limit = pd.to_numeric(row.get("Spec Limit", None),
                                           errors="coerce")
                if pd.isna(spec_limit):
                    continue   # No spec — skip this error

                if rate > spec_limit:
                    spec_breach_rows.append(row)

            if not spec_breach_rows:
                continue

            # Max rate across all breaching rows
            max_rate = max(pd.to_numeric(r[col], errors="coerce")
                          for r in spec_breach_rows)

            # Build failed media list
            failed_media_list = []

            if "Media Name" in gt_media.columns:
                # All Grand Total rows that are FAIL and have non-zero rate
                failed_gt = gt_media[
                    (gt_media["Result"].astype(str).str.upper() == "FAIL") &
                    (pd.to_numeric(gt_media[col], errors="coerce").fillna(0) > 0)
                ]

                for media_name in failed_gt["Media Name"].dropna().unique():
                    media_name_str = str(media_name).strip()
                    failed_units   = []

                    if not unit_media.empty and "Media Name" in unit_media.columns:
                        col_mask = (
                            pd.to_numeric(unit_media[col], errors="coerce").fillna(0) > 0
                            if col in unit_media.columns
                            else pd.Series([False] * len(unit_media),
                                           index=unit_media.index)
                        )
                        unit_rows = unit_media[
                            (unit_media["Media Name"].astype(str).str.strip()
                             == media_name_str) &
                            (unit_media["Result"].astype(str).str.upper() == "FAIL") &
                            col_mask
                        ]
                        if "Unit" in unit_rows.columns:
                            failed_units = sorted(
                                unit_rows["Unit"].astype(str).str.strip()
                                .unique().tolist()
                            )

                    failed_media_list.append({
                        "media_name": media_name_str,
                        "units":      failed_units
                    })

            if failed_media_list:
                error_name = col.replace("/K", "").strip()
                error_candidates.append({
                    "error":        error_name,
                    "rate":         round(float(max_rate), 3),
                    "failed_media": failed_media_list
                })

        # Sort by rate descending — no cap
        error_candidates.sort(key=lambda x: x["rate"], reverse=True)
        return error_candidates

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _get_error_per_k_cols(self, df, config):
        total_col = config.total_column_name
        return [
            col for col in df.columns
            if str(col).endswith("/K")
            and col != total_col
            and "total" not in str(col).lower()
            and "intervention" not in str(col).lower()
        ]

    def _normalise_result_col(self, df):
        if "Result" in df.columns:
            df["Result"] = df["Result"].astype(str).str.strip().str.upper()
        return df