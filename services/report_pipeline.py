"""
report_pipeline.py - WITH POWERPOINT SUMMARY

Generates:
  1. Excel file  — pivot sheets for debugging
  2. PowerPoint  — summary slides (one slide per Input Tray / Print Mode combo)
"""

import os
from pathlib import Path
from datetime import datetime
from services.pivot_service import PivotService
from services.summary_service import SummaryService
from services.storage_service import StorageService
from services.pptx_service import generate_summary_pptx
from engine.database_manager import DatabaseManager
from core.Spec_Category_config import ADF_CATEGORIES, Paperpath_CATEGORIES
from core.spec_detector import extract_year_quarter


class ReportPipeline:

    def run(self, raw_file, spec_file, output_folder):
        """
        Complete pipeline for generating pivot report + summary PowerPoint.

        Args:
            raw_file      : Path to raw data Excel file
            spec_file     : Path to spec Excel file (optional)
            output_folder : Path to output folder

        Returns:
            dict with result info
        """

        # 1. Detect test type
        pivot_service = PivotService(raw_file, spec_file)
        sub_assembly, printer, variant, spec_sheet, overview = pivot_service.detect_test_type()

        # 2. Select appropriate categories
        if sub_assembly == "ADF":
            categories = ADF_CATEGORIES
        else:
            categories = Paperpath_CATEGORIES

        # 3. Generate all pivots
        all_pivots = pivot_service.generate_all_pivots(categories)

        # Extract all unit names from raw pivot data
        try:
            units = set()

            for cat in all_pivots.values():
                df = cat["combined"]

                if "Unit" in df.columns:
                    unit_vals = df["Unit"].astype(str).str.strip()

                    unit_vals = unit_vals[
                        unit_vals.str.lower() != "grand total"
                    ]

                    units.update(unit_vals.tolist())

            overview["unit_names"] = sorted(units)

        except Exception as e:
            print(f"⚠ Could not extract unit names: {e}")

        # 3b. Compute actual_life from Grand Total rows in combined pivots.
        #     raw_data Tpages has one row per print event (not accumulated),
        #     so we must use the pivot Grand Total rows where Tpages is summed.
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
                    break   # one category is enough — Tpages totals are the same
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
            print("  Using current date as fallback")
            now = datetime.now()
            year = now.year
            quarter = (now.month - 1) // 3 + 1
            print(f"  Fallback: Q{quarter} {year}")

        # 6. Build output paths — save directly to user-selected folder
        from utils.paths import default_output_dir
        output_dir = Path(output_folder) if output_folder else default_output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_parts = [p for p in [printer, variant, sub_assembly] if p]
        phase_part = overview.get("project_phase", "") or f"Q{quarter}FY{year}"
        name_parts.append(phase_part)
        base_name  = "_".join(name_parts)
        excel_filename  = f"{base_name}_Report_{timestamp}.xlsx"
        pptx_filename   = f"{base_name}_Summary_{timestamp}.pptx"
        excel_path      = output_dir / excel_filename
        pptx_path       = output_dir / pptx_filename

        # 7. Save Excel (pivot sheets only — no summary sheet)
        storage_service = StorageService()
        storage_service.save_full_report(
            output_path=str(excel_path),
            summary_data=summary_data,
            all_pivots=all_pivots
        )

        # 8. Save PowerPoint summary
        try:
            generate_summary_pptx(
                output_path=str(pptx_path),
                summary_data=summary_data,
                printer=printer,
                variant=variant,
                sub_assembly=sub_assembly,
                year=year,
                quarter=quarter,
                overview=overview
            )
            # Auto-open the PowerPoint on Windows
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

        # 9. Save to database
        try:
            db = DatabaseManager(
                host="15.46.29.115",
                user="pavithra_030226",
                password="pavithra@030226",
                database="quality_sandbox"
            )
            storage_service.save_results_to_database(
                db=db,
                all_pivots=all_pivots,
                year=year,
                quarter=quarter,
                summary_data=summary_data
            )
            print(f"✓ Saved to database: Q{quarter} FY{year}")

        except Exception as e:
            print(f"⚠ Database save failed: {e}")
            import traceback
            traceback.print_exc()

        return {
            "output_path":  str(excel_path),
            "pptx_path":    str(pptx_path) if pptx_path else None,
            "printer":      printer,
            "variant":      variant,
            "sub_assembly": sub_assembly,
            "summary_text": summary_text,
            "year":         year,
            "quarter":      quarter
        }