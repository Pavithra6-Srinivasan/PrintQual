"""
master_pivot_generator.py
Master script to generate all pivot tables in a single Excel file.
"""

import pandas as pd
from core.pivot_generator import UnifiedPivotGenerator 
from core.excel_formatter import ExcelFormatter
from core.Spec_Category_config import Paperpath_CATEGORIES, ADF_CATEGORIES

# Input file path (your raw data Excel file)
RAW_DATA_FILE = "Paperpath/Marconi CUSLT 2.xlsm"

# Optional output file name
OUTPUT_FILE = ""

class MasterPivotGenerator:
    
    def __init__(self, raw_data_file, spec_file_path=None):
        """
        Args:
            raw_data_file: Path to the raw data Excel file
        """
        self.raw_data_file = raw_data_file
        self.spec_file_path = spec_file_path
        self.all_pivots = {}

        self.test_categories = Paperpath_CATEGORIES or ADF_CATEGORIES
    
    def generate_all_pivots(self):
        """
        Generate pivot tables for all test categories.
        Returns dict with structure: {category_name: {'media': df, 'unit': df}}
        """

        for config in self.test_categories:
            print(f"\nGenerating pivots")
            
            generator = UnifiedPivotGenerator(
                self.raw_data_file, 
                config, 
                spec_file_path=self.spec_file_path
            )
            
            pivot_media = generator.create_pivot_by_media_name()
            pivot_unit = generator.create_pivot_by_unit()
            
            self.all_pivots[config.name] = {
                'media': pivot_media,
                'unit': pivot_unit,          
            }

        return self.all_pivots
    
    def save_to_excel(self, output_file="Pivot_Tables.xlsx"):
        if not self.all_pivots:
            self.generate_all_pivots()
        
        print(f"\nSaving all pivots to {output_file}...")
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            formatter = ExcelFormatter()
            
            for category_name, pivot_data in self.all_pivots.items():
                
                # Sheet names
                sheet_media = f'{category_name} By Media'
                sheet_unit = f'{category_name} By Unit'
                
                # Write to Excel
                pivot_data['media'].to_excel(writer, sheet_name=sheet_media, index=False)
                pivot_data['unit'].to_excel(writer, sheet_name=sheet_unit, index=False)
                
                config = self.test_categories[[c.name for c in self.test_categories].index(category_name)]

                # Apply formatting
                formatter.apply_standard_formatting(
                    worksheet=writer.sheets[sheet_media],
                    dataframe=pivot_data['media'],
                    grand_total_identifier='Grand Total',
                    bold_columns=[config.total_column_name],
                    highlight_threshold=0.5
                )
                
                formatter.apply_standard_formatting(
                    worksheet=writer.sheets[sheet_unit],
                    dataframe=pivot_data['unit'],
                    grand_total_identifier='Grand Total',
                    bold_columns=[config.total_column_name],
                    highlight_threshold=0.5
                )
                        
        return output_file

def main():
    """
    Main execution function.
    """
    spec_file = 'spec.xlsx'

    try:
        # Create generator (auto-detects test type)
        master = MasterPivotGenerator(RAW_DATA_FILE, spec_file_path=spec_file)
        
        # Generate all pivots
        master.generate_all_pivots()

        output_file = OUTPUT_FILE or "Pivot_Tables.xlsx"
        
        # Save to excel
        master.save_to_excel(output_file)

        # Show summary
        print("\n" + "=" * 60)
        print("✓ SUCCESS!")
        print("=" * 60)
            
        print(f"\nOutput file: {output_file}")
        print("=" * 60)
        
    except FileNotFoundError:
        print(f"Could not find: {RAW_DATA_FILE}")
        print("Please check:")
        print("1. The file name is correct")
        print("2. The file is in the same folder as this script")
        print("3. The file path is correct")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        print("\nPlease check:")
        print("1. The Excel file format is correct")
        print("2. Required columns exist in the data")
        print("3. The file is not open in Excel")
        print("=" * 60)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()