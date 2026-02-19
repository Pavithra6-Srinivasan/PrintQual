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
        return temp_gen.sub_assembly, temp_gen.product, temp_gen.spec_sheet

    def generate_all_pivots(self, categories):
        all_pivots = {}

        for config in categories:
            generator = UnifiedPivotGenerator(
                self.raw_file,
                config,
                self.spec_file
            )

            all_pivots[config.name] = {
                "media": generator.create_pivot_by_media_name(),
                "unit": generator.create_pivot_by_unit(),
                "config": config
            }

        return all_pivots
