import pandas as pd
import numpy as np
from pathlib import Path
from excel_formatter import ExcelFormatter

class PivotGenerator:
    """
    Automates creation of pivot tables for printer quality intervention analysis.
    Creates two pivot tables: one grouped by Media Name, another by Unit.
    """
    
    def __init__(self, raw_data_file):
        """
        Initialize with path to raw data Excel file.
        """

        self.raw_data = pd.read_excel(raw_data_file, header = 2)
        self.media_types = self.raw_data['Media Type'].unique()
        
    def identify_error_columns(self):
        """
        Identify columns for each error type (NP, MP, TP, PJ, PS).
        Returns dict with error type as key and list of column names as value.
        """
        error_columns = {}

        # self.raw_data.columns is all column names in the DataFrame
        # for col in self.raw_data.columns loops through each column name
        
        error_columns['NP'] = [col for col in self.raw_data.columns if 'NP' in str(col)]
        error_columns['MP'] = [col for col in self.raw_data.columns 
                               if 'MP' in str(col) or 'MMP' in str(col)]
        error_columns['TP'] = [col for col in self.raw_data.columns if 'TP' in str(col)]
        error_columns['PJ'] = [col for col in self.raw_data.columns if 'PJ' in str(col)]
        error_columns['PS'] = [col for col in self.raw_data.columns if 'PS' in str(col)]
            
        return error_columns
    
    def create_pivot_by_media_name(self):
        """
        Create pivot table grouped by Media Type, Print Mode, and Media Name.
        """
        error_columns = self.identify_error_columns()
        
        # Creates a list of column names to group by
        # These are "filter combinations" - rows with the same values in these 3 columns will be combined
        groupby_cols = ['Media Type', 'Print Mode', 'Media Name']
        
        # Aggregation rules: when grouping, sum up all the Tpages values
        agg_dict = {'Tpages': 'sum'}
        
        for error_type, cols in error_columns.items():
            for col in cols:
                # verifies the column actually exists
                if col in self.raw_data.columns:
                    # adds a rule: "sum this column when grouping"
                    agg_dict[col] = 'sum'
                    # agg_dict contains summing rules for Tpages and ALL error columns
        
        # Groups rows that have identical values in Media Type, Print Mode, and Media Name
        # dropna=False means keep rows even if they have missing values
        pivot = self.raw_data.groupby(groupby_cols, dropna=False).agg(agg_dict).reset_index()
        
        pivot['Sum of NP/K'] = (pivot[[col for col in error_columns['NP'] if col in pivot.columns]].sum(axis=1) / pivot['Tpages']) * 1000
        pivot['Sum of MP/K'] = (pivot[[col for col in error_columns['MP'] if col in pivot.columns]].sum(axis=1) / pivot['Tpages']) * 1000
        pivot['Sum of TP/K'] = (pivot[[col for col in error_columns['TP'] if col in pivot.columns]].sum(axis=1) / pivot['Tpages']) * 1000
        pivot['Sum of PJ/K'] = (pivot[[col for col in error_columns['PJ'] if col in pivot.columns]].sum(axis=1) / pivot['Tpages']) * 1000
        pivot['Sum of PS/K'] = (pivot[[col for col in error_columns['PS'] if col in pivot.columns]].sum(axis=1) / pivot['Tpages']) * 1000
        
        pivot['Sum of Total intervention'] = (
            pivot['Sum of NP/K'] + 
            pivot['Sum of MP/K'] + 
            pivot['Sum of TP/K'] + 
            pivot['Sum of PJ/K'] + 
            pivot['Sum of PS/K']
        )
        
        final_cols = [
            'Media Type', 'Print Mode', 'Media Name', 'Tpages',
            'Sum of NP/K', 'Sum of MP/K', 'Sum of TP/K', 
            'Sum of PJ/K', 'Sum of PS/K', 'Sum of Total intervention'
        ]
        
        pivot = pivot[final_cols]
        pivot = self.add_grand_totals(pivot, groupby_cols[:2])
        
        return pivot
    
    def create_pivot_by_unit(self):
        """
        Create pivot table grouped by Media Type, Print Mode, and Unit.
        """
        error_columns = self.identify_error_columns()
        
        groupby_cols = ['Media Type', 'Print Mode', 'Unit']
        
        agg_dict = {'Tpages': 'sum'}
        
        for error_type, cols in error_columns.items():
            for col in cols:
                if col in self.raw_data.columns:
                    agg_dict[col] = 'sum'
        
        pivot = self.raw_data.groupby(groupby_cols, dropna=False).agg(agg_dict).reset_index()
        
        pivot['Sum of NP/K'] = (pivot[[col for col in error_columns['NP'] if col in pivot.columns]].sum(axis=1) / pivot['Tpages']) * 1000
        pivot['Sum of MP/K'] = (pivot[[col for col in error_columns['MP'] if col in pivot.columns]].sum(axis=1) / pivot['Tpages']) * 1000
        pivot['Sum of TP/K'] = (pivot[[col for col in error_columns['TP'] if col in pivot.columns]].sum(axis=1) / pivot['Tpages']) * 1000
        pivot['Sum of PJ/K'] = (pivot[[col for col in error_columns['PJ'] if col in pivot.columns]].sum(axis=1) / pivot['Tpages']) * 1000
        pivot['Sum of PS/K'] = (pivot[[col for col in error_columns['PS'] if col in pivot.columns]].sum(axis=1) / pivot['Tpages']) * 1000
        
        pivot['Sum of Total intervention'] = (
            pivot['Sum of NP/K'] + 
            pivot['Sum of MP/K'] + 
            pivot['Sum of TP/K'] + 
            pivot['Sum of PJ/K'] + 
            pivot['Sum of PS/K']
        )
        
        final_cols = [
            'Media Type', 'Print Mode', 'Unit', 'Tpages',
            'Sum of NP/K', 'Sum of MP/K', 'Sum of TP/K', 
            'Sum of PJ/K', 'Sum of PS/K', 'Sum of Total intervention'
        ]

        pivot = pivot[final_cols]
        pivot = self.add_grand_totals(pivot, groupby_cols[:2])

        return pivot
    
    def add_grand_totals(self, df, groupby_cols):
        """
        Add grand total rows for each combination of groupby_cols.
        """
        result_rows = []
        
        # A DataFrame with one row for each unique Media Type/Print Mode combination
        combinations = df[groupby_cols].drop_duplicates().reset_index(drop=True)
        
        # Returns two values: index (ignored with _) and row data (stored in combo)
        for _, combo in combinations.iterrows():
            # mask is True only for rows matching this specific Media Type AND Print Mode
            mask = True
            for col in groupby_cols:
                mask = mask & (df[col] == combo[col])
            
            # df[mask] selects only rows where mask is True
            # .copy() creates a copy (not a reference) to avoid modifying the original
            # subset now contains all rows for this Media Type/Print Mode combination
            subset = df[mask].copy()
            result_rows.append(subset)
            
            grand_total = pd.DataFrame([combo])
            
            # Third grouping column (Media Name or Unit) should be empty or "Grand Total"
            third_col = [col for col in df.columns if col not in groupby_cols and col not in ['Tpages', 'Sum of NP/K', 'Sum of MP/K', 'Sum of TP/K', 'Sum of PJ/K', 'Sum of PS/K', 'Sum of Total intervention']][0]
            grand_total[third_col] = 'Grand Total'
            
            total_tpages = subset['Tpages'].sum()
            grand_total['Tpages'] = total_tpages
            
            rate_cols = ['Sum of NP/K', 'Sum of MP/K', 'Sum of TP/K', 'Sum of PJ/K', 'Sum of PS/K']
            for col in rate_cols:
                if total_tpages > 0:
                    grand_total[col] = (subset[col].sum() * 1000) / total_tpages
                else:
                    grand_total[col] = 0.0
            
            # Total intervention
            grand_total['Sum of Total intervention'] = (subset['Sum of Total intervention'].sum() * 1000) / total_tpages if total_tpages > 0 else 0.0
            
            grand_total = grand_total[df.columns]
            result_rows.append(grand_total)
        
        # pd.concat() combines all DataFrames in the list vertically
        # ignore_index=True creates a new sequential index (0, 1, ...)
        result = pd.concat(result_rows, ignore_index=True)
        
        return result
    
    def generate_and_save(self, output_path='pivot_tables.xlsx'):
        """
        Generate both pivot tables and save to Excel file with separate sheets.
        """
        
        pivot_media_name = self.create_pivot_by_media_name()
        pivot_unit = self.create_pivot_by_unit()
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # index=False: don't write the DataFrame's index as a column
            pivot_media_name.to_excel(writer, sheet_name='Intervention By Media', index=False)
            pivot_unit.to_excel(writer, sheet_name='Intervention By Unit', index=False)
        
            # Apply formatting using the ExcelFormatter
            formatter = ExcelFormatter()
            
            # Format Media Name sheet
            formatter.apply_standard_formatting(
                worksheet=writer.sheets['Intervention By Media'],
                dataframe=pivot_media_name,
                grand_total_identifier='Grand Total',
                bold_columns=['Sum of Total intervention']
            )
            
            # Format Unit sheet
            formatter.apply_standard_formatting(
                worksheet=writer.sheets['Intervention By Unit'],
                dataframe=pivot_unit,
                grand_total_identifier='Grand Total',
                bold_columns=['Sum of Total intervention']
            )

        return pivot_media_name, pivot_unit

if __name__ == "__main__":

    raw_data_file = "Marconi Base Q2FY24.xlsx"
    generator = PivotGenerator(raw_data_file)
    
    pivot_media, pivot_unit = generator.generate_and_save("intervention_pivot_tables.xlsx")
