from pathlib import Path
from datetime import datetime
import urllib.parse

from services.pivot_service import PivotService
from services.summary_service import SummaryService
from services.storage_service import StorageService
from engine.database_manager import DatabaseManager
from core.spec_detector import extract_year_quarter
from core.Spec_Category_config import Paperpath_CATEGORIES, ADF_CATEGORIES


class ReportPipeline:

    def run(self, raw_file, spec_file, output_folder):

        pivot_service = PivotService(raw_file, spec_file)

        sub_assembly, printer, variant, sheet = pivot_service.detect_test_type()

        categories = (
            ADF_CATEGORIES if sub_assembly.upper() == "ADF"
            else Paperpath_CATEGORIES
        )

        all_pivots = pivot_service.generate_all_pivots(categories)

        if not all_pivots:
            raise ValueError("No pivot tables generated.")

        summary_service = SummaryService(all_pivots)
        summary_data, summary_text = summary_service.generate()

        year, quarter = extract_year_quarter(Path(raw_file).name)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        reports_folder = Path(output_folder) / "reports"
        reports_folder.mkdir(parents=True, exist_ok=True)

        filename = f"{printer}_{variant}_FY{year}_Q{quarter}_Quality_Report_{timestamp}.xlsx"

        output_path = reports_folder / filename

        storage = StorageService()

        storage.save_full_report(
            output_path=output_path,
            summary_data=summary_data,
            all_pivots=all_pivots
        )

        db = DatabaseManager(
            host="15.46.29.115",
            database="quality_sandbox",
            username="pavithra_030226",
            password=urllib.parse.quote_plus("pavithra@030226"),
            db_type="mysql"
        )

        db.create_tables()
        db.insert_summary(summary_data, year, quarter)
        db.close()

        return {
            "printer": printer,
            "variant": variant,
            "sub_assembly": sub_assembly,
            "summary_text": summary_text,
            "summary_data": summary_data,
            "output_path": output_path
        }