"""
master_pivot_generator.py

Master script to generate all pivot tables in a single Excel file.
"""

import pandas as pd
from unified_pivot_generator import UnifiedPivotGenerator
from excel_formatter import ExcelFormatter
from test_category_config import ALL_TEST_CATEGORIES

class MasterPivotGenerator:
    """
    Generates all pivot tables for all test categories in a single Excel file.
    """
    
    def __init__(self, raw_data_file):
        """
        Args:
            raw_data_file: Path to the raw data Excel file
        """
        self.raw_data_file = raw_data_file
        self.all_pivots = {}
    
    def generate_all_pivots(self):
        """
        Generate pivot tables for all test categories.
        Returns dict with structure: {category_name: {'media': df, 'unit': df}}
        """
        for config in ALL_TEST_CATEGORIES:
            print(f"\nGenerating pivots")
            
            generator = UnifiedPivotGenerator(self.raw_data_file, config)
            
            pivot_media = generator.create_pivot_by_media_name()
            pivot_unit = generator.create_pivot_by_unit()
            
            self.all_pivots[config.name] = {
                'media': pivot_media,
                'unit': pivot_unit,
                'config': config
            }

        return self.all_pivots
    
    def save_to_excel(self, output_file="All_Pivot_Tables.xlsx"):
        """
        Save all pivot tables to a single Excel file with proper formatting.
        Each test category gets 2 tabs: one for Media and one for Unit.
        """
        if not self.all_pivots:
            self.generate_all_pivots()
        
        print(f"\nSaving all pivots to {output_file}...")
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            formatter = ExcelFormatter()
            
            for category_name, pivot_data in self.all_pivots.items():
                config = pivot_data['config']
                
                # Sheet names
                sheet_media = f'{category_name} By Media'
                sheet_unit = f'{category_name} By Unit'
                
                # Write to Excel
                pivot_data['media'].to_excel(writer, sheet_name=sheet_media, index=False)
                pivot_data['unit'].to_excel(writer, sheet_name=sheet_unit, index=False)
                
                # Apply formatting
                formatter.apply_standard_formatting(
                    worksheet=writer.sheets[sheet_media],
                    dataframe=pivot_data['media'],
                    grand_total_identifier='Grand Total',
                    bold_columns=[config.total_column_name]
                )
                
                formatter.apply_standard_formatting(
                    worksheet=writer.sheets[sheet_unit],
                    dataframe=pivot_data['unit'],
                    grand_total_identifier='Grand Total',
                    bold_columns=[config.total_column_name]
                )
                        
        return output_file

def main():
    """Main execution function."""
    # Configuration
    raw_data_file = "Marconi Base Q2FY24.xlsx"
    output_file = "All_Pivot_Tables.xlsx"
    
    # Create master generator
    master = MasterPivotGenerator(raw_data_file)
    
    # Generate all pivots
    master.generate_all_pivots()
    
    # Save to Excel
    master.save_to_excel(output_file)


if __name__ == "__main__":
    main()