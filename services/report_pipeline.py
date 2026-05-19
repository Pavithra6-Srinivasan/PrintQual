"""
report_pipeline.py - WITH POWERPOINT SUMMARY

Generates:
  1. Excel file  — pivot sheets for debugging
  2. PowerPoint  — summary slides (one slide per Input Tray / Print Mode combo)

For ADF sub-assemblies where the raw data contains both 'ADF' (Scan) and
'ADF COPY' entries in the 'Test mode' column, the pipeline automatically
generates two separate sets of reports — one per mode.
"""

import os
from pathlib import Path
from datetime import datetime
from services.pivot_service import PivotService
from services.summary_service import SummaryService
from services.storage_service import StorageService
from services.pptx_service import generate_summary_pptx
from core.Spec_Category_config import ADF_CATEGORIES, Paperpath_CATEGORIES
from core.spec_detector import extract_year_quarter


# Mapping from raw Test mode value (upper-cased) → human label used in filenames/titles
_ADF_MODE_MAP = {
    "ADF":      "ADF Scan",
    "ADF COPY": "ADF Copy",
}


class ReportPipeline:

    def run(self, raw_file, spec_file, output_folder,
            excluded_units=None, excluded_media_names=None):
        """
        Entry point.  Detects whether an ADF split is required and runs
        _run_single() once (normal) or twice (ADF Scan + ADF Copy).

        Returns a list of result dicts — one per report generated.
        """
        # Initial detection pass — also populates _RAW_DATA_CACHE
        _init_service = PivotService(raw_file, spec_file,
                                     excluded_units=excluded_units,
                                     excluded_media_names=excluded_media_names)
        sub_assembly, _, _, _, _ = _init_service.detect_test_type()

        run_modes = self._detect_run_modes(raw_file, sub_assembly)

        results = []
        for mode_filter, mode_label in run_modes:
            result = self._run_single(
                raw_file=raw_file,
                spec_file=spec_file,
                output_folder=output_folder,
                excluded_units=excluded_units,
                excluded_media_names=excluded_media_names,
                test_mode_filter=mode_filter,
                mode_label=mode_label,
            )
            results.append(result)

        return results

    # ── Split detection ───────────────────────────────────────────────────────

    def _detect_run_modes(self, raw_file, sub_assembly):
        """
        Returns a list of (filter_value, label) pairs.
        Single-element [(None, None)] when no split is needed.
        Two elements when ADF Scan + ADF Copy are both present.
        """
        if sub_assembly != "ADF":
            return [(None, None)]

        from core.pivot_generator import _RAW_DATA_CACHE
        raw_df = _RAW_DATA_CACHE.get(raw_file)
        if raw_df is None or "Test mode" not in raw_df.columns:
            return [(None, None)]

        modes_present = set(
            raw_df["Test mode"]
            .dropna()
            .astype(str)
            .str.strip()
            .str.upper()
            .unique()
        )

        split_modes = [k for k in _ADF_MODE_MAP if k in modes_present]
        if len(split_modes) == len(_ADF_MODE_MAP):
            print(f"✓ ADF split detected — generating {len(split_modes)} reports")
            return [(k, _ADF_MODE_MAP[k]) for k in _ADF_MODE_MAP]

        return [(None, None)]

    # ── Database save ─────────────────────────────────────────────────────────

    def _save_to_database(self, summary_data, year, quarter):
        try:
            from engine.database_manager import DatabaseManager
            db = DatabaseManager(
                host="15.46.29.115",
                user="pavithra_030226",
                password="pavithra@030226",
                database="quality_sandbox"
            )
            saved = 0
            for cat in summary_data.get("categories", []):
                category_name = cat["category"]
                for ms in cat["media_summaries"]:
                    media_type = ms["media_type"]
                    if ms.get("media_cat"):
                        media_type = f"{media_type} ({ms['media_cat']})"

                    errors = ms.get("errors", [])
                    all_units, all_media_names, all_error_types = set(), set(), set()
                    for err in errors:
                        for fm in err.get("failed_media", []):
                            all_media_names.add(fm["media_name"])
                            all_units.update(fm.get("units", []))
                            if fm.get("units"):
                                all_error_types.add(err["error"])

                    db.insert_summary_result(
                        category=category_name,
                        media_type=media_type,
                        overall_result=ms["overall_result"],
                        failed_units=", ".join(sorted(all_units)) or None,
                        failed_media_names=", ".join(sorted(all_media_names)) or None,
                        failed_error_types=", ".join(sorted(all_error_types)) or None,
                        failed_conditions=ms.get("test_condition") or None,
                        remarks=None,
                        year=year,
                        quarter=quarter,
                    )
                    saved += 1
            print(f"✓ Saved {saved} result(s) to database (Q{quarter} {year})")
        except Exception as e:
            print(f"⚠ Database save skipped: {e}")

    # ── Single-mode pipeline ──────────────────────────────────────────────────

    def _run_single(self, raw_file, spec_file, output_folder,
                    excluded_units, excluded_media_names,
                    test_mode_filter, mode_label):
        """
        Full pipeline for one report.

        mode_label (e.g. 'ADF Scan' / 'ADF Copy') is incorporated into
        the output filename and passed as sub_assembly to the PPTX builder
        so slide titles reflect the correct mode.  None when no split.
        """

        # 1. Detect test type
        pivot_service = PivotService(
            raw_file, spec_file,
            excluded_units=excluded_units,
            excluded_media_names=excluded_media_names,
            test_mode_filter=test_mode_filter,
        )
        sub_assembly, printer, variant, spec_sheet, overview = pivot_service.detect_test_type()
        if mode_label:
            print(f"\n── Generating: {mode_label} ──")

        # 2. Select appropriate categories
        categories = ADF_CATEGORIES if sub_assembly == "ADF" else Paperpath_CATEGORIES

        # 3. Generate all pivots
        all_pivots = pivot_service.generate_all_pivots(categories)

        # Extract unit names from pivot data
        try:
            units = set()
            for cat in all_pivots.values():
                df = cat["combined"]
                if "Unit" in df.columns:
                    unit_vals = df["Unit"].astype(str).str.strip()
                    unit_vals = unit_vals[~unit_vals.str.lower().isin(["grand total", "nan", ""])]
                    units.update(unit_vals.tolist())
            overview["unit_names"] = sorted(units)
        except Exception as e:
            print(f"⚠ Could not extract unit names: {e}")

        # Compute actual_life from Grand Total rows
        try:
            import pandas as pd
            total_tpages = 0.0
            unit_count   = overview.get("unit_count", 0) or 1
            for cat_data in all_pivots.values():
                df = cat_data["combined"]
                if "Unit" in df.columns and "Tpages" in df.columns:
                    gt_mask = df["Unit"].astype(str).str.strip().str.lower() == "grand total"
                    gt_tpages = pd.to_numeric(
                        df.loc[gt_mask, "Tpages"], errors="coerce"
                    ).fillna(0).sum()
                    total_tpages += gt_tpages
                    break
            if unit_count > 0 and total_tpages > 0:
                overview["actual_life"] = int(round(total_tpages / unit_count, 0))
                print(f"✓ Actual test life per unit: {overview['actual_life']:,} pages")
        except Exception as e:
            print(f"⚠ Could not compute actual_life: {e}")

        # 4. Generate summary
        summary_service = SummaryService(all_pivots)
        summary_data, summary_text = summary_service.generate()

        # 5. Detect year and quarter from filename
        try:
            filename = Path(raw_file).name
            year, quarter = extract_year_quarter(filename)
            print(f"✓ Detected from filename: Q{quarter} FY{year}")
        except Exception as e:
            print(f"⚠ Could not detect year/quarter from filename: {e}")
            now = datetime.now()
            year = now.year
            quarter = (now.month - 1) // 3 + 1
            print(f"  Fallback: Q{quarter} {year}")

        # 5b. Persist results to database (non-fatal if unreachable)
        self._save_to_database(summary_data, year, quarter)

        # 6. Build output paths
        from utils.paths import default_output_dir
        output_dir = Path(output_folder) if output_folder else default_output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Use mode_label in filename when split (e.g. "ADF Scan" → "ADF_Scan")
        sa_name    = mode_label.replace(" ", "_") if mode_label else sub_assembly
        name_parts = [p for p in [printer, variant, sa_name] if p]
        phase_part = overview.get("project_phase", "") or f"Q{quarter}FY{year}"
        name_parts.append(phase_part)
        base_name       = "_".join(name_parts)
        excel_filename  = f"{base_name}_Report_{timestamp}.xlsx"
        pptx_filename   = f"{base_name}_Summary_{timestamp}.pptx"
        excel_path      = output_dir / excel_filename
        pptx_path       = output_dir / pptx_filename

        # 7. Save Excel
        storage_service = StorageService()
        storage_service.save_full_report(
            output_path=str(excel_path),
            summary_data=summary_data,
            all_pivots=all_pivots
        )

        # 8. Save PowerPoint
        # Pass mode_label as sub_assembly so slide titles say "ADF Scan" / "ADF Copy"
        pptx_sub_assembly = mode_label if mode_label else sub_assembly
        try:
            generate_summary_pptx(
                output_path=str(pptx_path),
                summary_data=summary_data,
                printer=printer,
                variant=variant,
                sub_assembly=pptx_sub_assembly,
                year=year,
                quarter=quarter,
                overview=overview,
                raw_filename_stem=Path(raw_file).stem,
            )
            try:
                os.startfile(str(pptx_path))
                print(f"✓ PowerPoint opened automatically")
            except Exception as open_err:
                print(f"⚠ Could not auto-open PowerPoint: {open_err}")
        except Exception as e:
            print(f"⚠ PowerPoint generation failed: {e}")
            import traceback
            traceback.print_exc()
            pptx_path = None

        return {
            "output_path":  str(excel_path),
            "pptx_path":    str(pptx_path) if pptx_path else None,
            "printer":      printer,
            "variant":      variant,
            "sub_assembly": pptx_sub_assembly,
            "mode_label":   mode_label,
            "summary_text": summary_text,
            "year":         year,
            "quarter":      quarter
        }
