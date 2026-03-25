"""
pivot_service.py - COMBINED TABLES

Creates single combined table per category (Media Name + Unit)
Grand Total after each media name group
"""

from core.pivot_generator import UnifiedPivotGenerator
from core.Spec_Category_config import Paperpath_CATEGORIES

class PivotService:

    def __init__(self, raw_file, spec_file):
        self.raw_file = raw_file
        self.spec_file = spec_file

    def detect_test_type(self):
        temp_gen = UnifiedPivotGenerator(
            self.raw_file,
            Paperpath_CATEGORIES[0],
            self.spec_file
        )
        """
pivot_service.py - COMBINED TABLES

Creates single combined table per category (Media Name + Unit)
Grand Total after each media name group
"""

from core.pivot_generator import UnifiedPivotGenerator
from core.Spec_Category_config import Paperpath_CATEGORIES

class PivotService:

    def __init__(self, raw_file, spec_file):
        self.raw_file = raw_file
        self.spec_file = spec_file

    def detect_test_type(self):
        temp_gen = UnifiedPivotGenerator(
            self.raw_file,
            Paperpath_CATEGORIES[0],
            self.spec_file
        )
        overview = temp_gen.extract_overview_info()
        return temp_gen.sub_assembly, temp_gen.detected_main_printer, temp_gen.detected_variant, temp_gen.spec_sheet, overview

    def generate_all_pivots(self, categories):
        """
        Generate COMBINED pivot tables (Media Name + Unit in one table).
        Grand Total rows after each Media Name group.
        """
        all_pivots = {}

        for config in categories:
            generator = UnifiedPivotGenerator(
                self.raw_file,
                config,
                self.spec_file
            )

            # Use COMBINED table only (no separate media/unit tables)
            combined_pivot = generator.create_combined_pivot()

            all_pivots[config.name] = {
                "combined": combined_pivot,
                "config": config
            }

        return all_pivots
        return temp_gen.sub_assembly, temp_gen.detected_main_printer, temp_gen.detected_variant, temp_gen.spec_sheet