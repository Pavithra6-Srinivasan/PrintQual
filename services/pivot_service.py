"""
pivot_service.py - OPTIMIZED

Key optimizations:
1. Shares raw data across all generators
2. Single print statement per category
3. Clears cache at end
"""

from core.pivot_generator import UnifiedPivotGenerator
from core.Spec_Category_config import Paperpath_CATEGORIES

class PivotService:

    def __init__(self, raw_file, spec_file):
        self.raw_file = raw_file
        self.spec_file = spec_file
        self._first_gen = None
        self._first_config = None

    def detect_test_type(self):
        """Detect test type and cache first generator."""
        self._first_config = Paperpath_CATEGORIES[0]
        self._first_gen = UnifiedPivotGenerator(
            self.raw_file,
            self._first_config,
            self.spec_file
        )
        
        # Print detection info once
        print(f"\n✓ Detected: {self._first_gen.detected_main_printer} "
              f"{self._first_gen.detected_variant} {self._first_gen.sub_assembly}")
        
        overview = self._first_gen.extract_overview_info()
        return (self._first_gen.sub_assembly,
                self._first_gen.detected_main_printer,
                self._first_gen.detected_variant,
                self._first_gen.spec_sheet,
                overview)

    def generate_all_pivots(self, categories):
        """
        Generate COMBINED pivot tables - OPTIMIZED.
        Reuses raw data across all categories.
        """
        print(f"\n⏱️  Generating {len(categories)} pivot categories...")
        
        all_pivots = {}

        for idx, config in enumerate(categories, 1):
            # Reuse cached generator for first category
            if (self._first_gen is not None
                    and config.name == self._first_config.name):
                generator = self._first_gen
            else:
                # All subsequent generators share the cached raw data
                generator = UnifiedPivotGenerator(
                    self.raw_file,
                    config,
                    self.spec_file
                )

            combined_pivot = generator.create_combined_pivot()

            all_pivots[config.name] = {
                "combined": combined_pivot,
                "config": config
            }
            
            # Single progress indicator per category
            print(f"   [{idx}/{len(categories)}] {config.name}: {len(combined_pivot)} rows")

        # Clear caches to free memory
        UnifiedPivotGenerator.clear_cache()
        
        return all_pivots