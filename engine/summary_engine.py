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

                        overall_result, accumulated_rate, spec_val =                             self._calc_media_type_result(gt_media, config)

                        errors = []
                        if overall_result == "FAIL":
                            errors = self._build_error_list(
                                gt_media, unit_media, per_k_cols, config
                            )
                        elif overall_result == "PASS":
                            errors = self._build_pass_error_list(
                                gt_media, unit_media, per_k_cols, config
                            )
                        elif overall_result == "NO SPEC":
                            errors = self._build_no_spec_error_list(
                                gt_media, per_k_cols
                            )

                        media_summaries.append({
                            "media_type":     media_type,
                            "overall_result": overall_result,
                            "tray":           tray,
                            "mode":           mode,
                            "spec":           spec_val,
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

    def _calc_media_type_result(self, gt_media, config):
        """
        Compute Tpages-weighted average of total intervention rate across
        all media names for this (media_type, print_mode) combination,
        then compare against spec.

        Returns (overall_result, accumulated_rate, spec_val).
        """
        if gt_media.empty:
            return "NO DATA", None, None

        results = gt_media["Result"].astype(str).str.upper().unique()

        # No spec case — fall back to worst result
        if all(r in ("NO SPEC PROVIDED", "SPEC NOT FOUND", "NO DATA")
               for r in results):
            return "NO SPEC", None, None

        total_col = config.total_column_name

        # Get spec limit (same for all rows in this slice)
        spec_val = None
        if "Spec Limit" in gt_media.columns:
            spec_series = pd.to_numeric(
                gt_media["Spec Limit"], errors="coerce"
            ).dropna()
            if not spec_series.empty:
                spec_val = round(float(spec_series.iloc[0]), 2)

        if total_col not in gt_media.columns or spec_val is None:
            # No total column or no spec — fall back to worst result
            if "FAIL" in results:
                return "FAIL", None, spec_val
            return "PASS", None, spec_val

        # Tpages-weighted average of total rate across all media names
        tpages = pd.to_numeric(gt_media["Tpages"], errors="coerce").fillna(0)
        rates  = pd.to_numeric(gt_media[total_col], errors="coerce").fillna(0)

        total_tpages = tpages.sum()
        if total_tpages <= 0:
            return "NO DATA", None, spec_val

        accumulated_rate = round(
            float((rates * tpages).sum() / total_tpages), 2
        )

        overall_result = "PASS" if accumulated_rate <= spec_val else "FAIL"
        return overall_result, accumulated_rate, spec_val

    # ------------------------------------------------------------------
    # ERROR LIST BUILDER
    # ------------------------------------------------------------------

    def _build_error_list(self, gt_media, unit_media, per_k_cols, config):
        """
        For each error column:
          1. Compute Tpages-weighted average of that error rate across ALL
             media names in this (media_type, print_mode) combination.
          2. Include the error only if that accumulated rate exceeds spec.
          3. Display the accumulated rate (not per-media-name max).
          4. Under each media name, list units where Result = FAIL and
             rate > 0 for that specific error column.
        """
        error_candidates = []

        # Get spec limit (same for all rows in this slice)
        spec_val = None
        if "Spec Limit" in gt_media.columns:
            spec_series = pd.to_numeric(
                gt_media["Spec Limit"], errors="coerce"
            ).dropna()
            if not spec_series.empty:
                spec_val = float(spec_series.iloc[0])

        tpages_all = pd.to_numeric(
            gt_media["Tpages"], errors="coerce"
        ).fillna(0) if "Tpages" in gt_media.columns else pd.Series(
            [0.0] * len(gt_media), index=gt_media.index
        )
        total_tpages = tpages_all.sum()

        for col in per_k_cols:
            if col not in gt_media.columns:
                continue

            rates = pd.to_numeric(gt_media[col], errors="coerce").fillna(0)

            # Tpages-weighted average across all media names
            if total_tpages > 0:
                accumulated_rate = float((rates * tpages_all).sum() / total_tpages)
            else:
                accumulated_rate = 0.0

            if accumulated_rate <= 0:
                continue

            # Only include if accumulated rate exceeds spec
            if spec_val is not None and accumulated_rate <= spec_val:
                continue

            accumulated_rate = round(accumulated_rate, 2)

            # Build failed media list — media names with non-zero rate
            failed_media_list = []

            if "Media Name" in gt_media.columns:
                nonzero_gt = gt_media[rates > 0]

                for media_name in nonzero_gt["Media Name"].dropna().unique():
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

                    # Per-media-name rate for display
                    media_gt_rows = nonzero_gt[
                        nonzero_gt["Media Name"].astype(str).str.strip()
                        == media_name_str
                    ]
                    media_tpages = pd.to_numeric(
                        media_gt_rows["Tpages"], errors="coerce"
                    ).fillna(0) if "Tpages" in media_gt_rows.columns else pd.Series([0.0])
                    media_rates  = pd.to_numeric(
                        media_gt_rows[col], errors="coerce"
                    ).fillna(0)
                    media_total_tp = media_tpages.sum()

                    if media_total_tp > 0:
                        media_rate = round(
                            float((media_rates * media_tpages).sum() / media_total_tp), 2
                        )
                    else:
                        media_rate = round(float(media_rates.max()), 2)

                    failed_media_list.append({
                        "media_name": media_name_str,
                        "units":      failed_units,
                        "rate":       media_rate
                    })

            if failed_media_list:
                error_name = col.replace("/K", "").strip()
                error_candidates.append({
                    "error":        error_name,
                    "rate":         accumulated_rate,
                    "failed_media": failed_media_list
                })

        # Sort by accumulated rate descending
        error_candidates.sort(key=lambda x: x["rate"], reverse=True)
        return error_candidates

    # ------------------------------------------------------------------
    # PASS ERROR LIST BUILDER
    # ------------------------------------------------------------------

    def _build_pass_error_list(self, gt_media, unit_media, per_k_cols, config):
        """
        For PASS combinations: find up to 5 error types where individual
        media names breach the spec, even though the accumulated rate passed.

        Logic per error column:
          - Find media names whose individual Grand Total rate > spec
          - If any found, include this error (accumulated rate shown)
          - Cap at 5 error types, ranked by accumulated rate descending
          - No units listed (overall passed)
        """
        PASS_TOP_N = 5
        error_candidates = []

        # Get spec limit
        spec_val = None
        if "Spec Limit" in gt_media.columns:
            spec_series = pd.to_numeric(
                gt_media["Spec Limit"], errors="coerce"
            ).dropna()
            if not spec_series.empty:
                spec_val = float(spec_series.iloc[0])

        if spec_val is None:
            return []

        tpages_all = pd.to_numeric(
            gt_media["Tpages"], errors="coerce"
        ).fillna(0) if "Tpages" in gt_media.columns else pd.Series(
            [0.0] * len(gt_media), index=gt_media.index
        )
        total_tpages = tpages_all.sum()

        for col in per_k_cols:
            if col not in gt_media.columns:
                continue

            rates = pd.to_numeric(gt_media[col], errors="coerce").fillna(0)

            # Find media names that individually breach spec for this error
            if "Media Name" not in gt_media.columns:
                continue

            breaching_media = []
            for _, row in gt_media.iterrows():
                media_name_str = str(row.get("Media Name", "")).strip()
                if not media_name_str:
                    continue
                media_rate = pd.to_numeric(row.get(col, 0), errors="coerce")
                if pd.isna(media_rate) or media_rate <= spec_val:
                    continue
                # This media name individually breaches spec
                breaching_media.append({
                    "media_name": media_name_str,
                    "units":      [],   # no units for PASS overall
                    "rate":       round(float(media_rate), 2)
                })

            if not breaching_media:
                continue

            # Accumulated rate for this error (for sorting)
            if total_tpages > 0:
                accumulated_rate = round(
                    float((rates * tpages_all).sum() / total_tpages), 2
                )
            else:
                accumulated_rate = round(float(rates.max()), 2)

            error_name = col.replace("/K", "").strip()
            error_candidates.append({
                "error":        error_name,
                "rate":         accumulated_rate,
                "failed_media": breaching_media
            })

        error_candidates.sort(key=lambda x: x["rate"], reverse=True)
        return error_candidates[:PASS_TOP_N]

    # ------------------------------------------------------------------
    # NO SPEC ERROR LIST BUILDER
    # ------------------------------------------------------------------

    def _build_no_spec_error_list(self, gt_media, per_k_cols):
        """
        For categories with no spec (e.g. Other Defects, PQ):
        - Find error columns with non-zero rates on any Grand Total row
        - Rank by max rate descending, take top 5
        - For each error, list media names with non-zero rate
        - No units listed (not applicable without spec)
        """
        NO_SPEC_TOP_N = 5
        error_candidates = []

        for col in per_k_cols:
            if col not in gt_media.columns:
                continue

            rates = pd.to_numeric(gt_media[col], errors="coerce").fillna(0)
            max_rate = rates.max()

            if max_rate <= 0:
                continue

            # Media names with non-zero rate for this error
            failed_media_list = []
            if "Media Name" in gt_media.columns:
                nonzero_rows = gt_media[rates > 0]
                for media_name in nonzero_rows["Media Name"].dropna().unique():
                    failed_media_list.append({
                        "media_name": str(media_name).strip(),
                        "units": []   # no units for NO SPEC categories
                    })

            if failed_media_list:
                error_name = col.replace("/K", "").strip()
                error_candidates.append({
                    "error":        error_name,
                    "rate":         round(float(max_rate), 3),
                    "failed_media": failed_media_list
                })

        error_candidates.sort(key=lambda x: x["rate"], reverse=True)
        return error_candidates[:NO_SPEC_TOP_N]

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