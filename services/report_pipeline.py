"""
report_pipeline.py - WITH YEAR/QUARTER DETECTION

Fixed: Now detects year and quarter from filename instead of using current date
"""

from pathlib import Path
from datetime import datetime
from services.pivot_service import PivotService
from services.summary_service import SummaryService
from services.storage_service import StorageService
from engine.database_manager import DatabaseManager
from core.Spec_Category_config import ADF_CATEGORIES, Paperpath_CATEGORIES
from core.spec_detector import extract_year_quarter
import re

class ReportPipeline:
    
    def run(self, raw_file, spec_file, output_folder):
        """
        Complete pipeline for generating pivot report.
        
        Args:
            raw_file: Path to raw data Excel file
            spec_file: Path to spec Excel file (optional)
            output_folder: Path to output folder
        
        Returns:
            dict with result info
        """
        
        # 1. Detect test type
        pivot_service = PivotService(raw_file, spec_file)
        sub_assembly, printer, variant, spec_sheet = pivot_service.detect_test_type()
        
        # 2. Select appropriate categories
        if sub_assembly == "ADF":
            categories = ADF_CATEGORIES
        else:
            categories = Paperpath_CATEGORIES
        
        # 3. Generate all pivots
        all_pivots = pivot_service.generate_all_pivots(categories)
        
        # 4. Generate summary
        summary_service = SummaryService(all_pivots)
        summary_data, summary_text = summary_service.generate()
        
        # 5. DETECT YEAR AND QUARTER FROM FILENAME
        try:
            # Get filename from raw_file path
            filename = Path(raw_file).name
            year, quarter = extract_year_quarter(filename)
            print(f"✓ Detected from filename: Q{quarter} FY{year}")
        except Exception as e:
            # Fallback to current date if detection fails
            print(f"⚠ Could not detect year/quarter from filename: {e}")
            print("  Using current date as fallback")
            now = datetime.now()
            year = now.year
            quarter = (now.month - 1) // 3 + 1
            print(f"  Fallback: Q{quarter} {year}")
        
        # 6. Save to Excel
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{printer}_{variant}_{sub_assembly}_Q{quarter}FY{year}_Report_{timestamp}.xlsx"
        output_path = Path(output_folder) / output_filename
        
        storage_service = StorageService()
        storage_service.save_full_report(
            output_path=str(output_path),
            summary_data=summary_data,
            all_pivots=all_pivots
        )
        
        # 7. Save to database (if enabled)
        try:
            db = DatabaseManager(
                host="15.46.29.115",
                user="pavithra_030226",
                password="pavithra@030226",
                database="quality_sandbox"
            )
            
            # Use detected year and quarter
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
            # Continue even if database save fails
        
        return {
            "output_path": str(output_path),
            "printer": printer,
            "variant": variant,
            "sub_assembly": sub_assembly,
            "summary_text": summary_text,
            "year": year,
            "quarter": quarter
        }