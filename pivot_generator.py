"""
Pivot table generator that handles all test categories.
Supports both direct column mapping and column summing.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from excel_formatter import ExcelFormatter

def find_header_row(file_path, required_columns=None, max_search_rows=20):
    
    # Read the file without assuming any header position
    try:
        df_test = pd.read_excel(file_path, header=None, nrows=max_search_rows)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return 2
    
    # Look for "Test Condition" column
    for row_idx in range(min(max_search_rows, len(df_test))):
        row_values = df_test.iloc[row_idx].astype(str).str.strip().tolist()
        
        # Check for "Test Condition" (case-insensitive)
        for val in row_values:
            if 'test condition' in val.lower():
                print(f"✓ Header row detected at row {row_idx} (found 'Test Condition')")
                print(f"  Sample columns: {[v for v in row_values[:10] if v not in ['', 'nan', 'None']]}")
                return row_idx
    
    # If "Test Condition" not found, default to row 2
    print(f"⚠ Warning: 'Test Condition' not found in first {max_search_rows} rows")
    print(f"  Defaulting to row 2")
    return 2

class UnifiedPivotGenerator:
    COLUMN_ALIASES = {
        'Input_Tray': ['Input_Tray', 'Tray', 'Input Tray'],
        'Media Type': ['Media Type'],
        'Print Mode': ['Print Mode', 'Paper Mode'],
        'Media Name': ['Media Name'],
        'Test Condition': ['Test Condition'],
        'Unit': ['Unit'],
        'Tpages': ['Tpages', 'Tsheets Printed'],
        'Print Quality': ['Print Quality']
    }
    
    def __init__(self, raw_data_file, test_config):
        """
        Args:
            raw_data_file: Path to raw data Excel file
            test_config: TestCategoryConfig object defining the category
        """
        header_row = find_header_row(raw_data_file)
        
        self.raw_data = pd.read_excel(raw_data_file, header=header_row)
        self.config = test_config

        self._standardize_column_names()
        
        # Process error columns based on config
        self._prepare_error_columns()
    
    def _standardize_column_names(self):
        """
        Rename columns to standard names if they use alternative names.
        E.g., 'Tray' -> 'Input_Tray', 'Input Tray' -> 'Input_Tray'
        """
        rename_map = {}
        
        for standard_name, aliases in self.COLUMN_ALIASES.items():
            # Check if any alias exists in the columns
            for alias in aliases:
                if alias in self.raw_data.columns and alias != standard_name:
                    rename_map[alias] = standard_name
                    print(f"  Mapping '{alias}' → '{standard_name}'")
                    break  # Use first match only
        
        if rename_map:
            self.raw_data.rename(columns=rename_map, inplace=True)
            print(f"✓ Standardized {len(rename_map)} column name(s)")

    def _prepare_error_columns(self):
        """
        Process error columns based on config.
        Handles both direct mapping and summing of multiple columns.
        """
        self.processed_data = self.raw_data.copy()
        self.error_output_columns = []
        
        for output_col, input_spec in self.config.error_column_config.items():
            if isinstance(input_spec, list):
                # Sum multiple columns
                available_cols = [col for col in input_spec if col in self.raw_data.columns]
                if available_cols:
                    self.processed_data[output_col] = self.raw_data[available_cols].sum(axis=1)
                    self.error_output_columns.append(output_col)
                else:
                    print(f"Warning: None of the columns {input_spec} found for {output_col}")
            else:
                # Direct column mapping
                if input_spec in self.raw_data.columns:
                    self.processed_data[output_col] = self.raw_data[input_spec]
                    self.error_output_columns.append(output_col)
                else:
                    print(f"Warning: Column '{input_spec}' not found for {output_col}")
    
    def create_pivot_by_media_name(self):
        """Create pivot table grouped by Media Name."""
        groupby_cols = ['Test Condition', 'Input_Tray', 'Media Type', 'Print Mode']
        groupby_cols.extend(self.config.additional_groupby_cols)  # Add Print Quality here
        groupby_cols.append('Media Name')
        
        # Aggregation rules
        agg_dict = {'Tpages': 'sum'}
        for col in self.error_output_columns:
            agg_dict[col] = 'sum'
        
        # Group and aggregate
        pivot = self.processed_data.groupby(groupby_cols, dropna=False).agg(agg_dict).reset_index()
        
        # Calculate per-K rate for each error column
        for col in self.error_output_columns:
            col_name = f'{col}/K'
            pivot[col_name] = (pivot[col] / pivot['Tpages']) * 1000
        
        # Calculate total
        per_k_cols = [f'{col}/K' for col in self.error_output_columns]
        pivot[self.config.total_column_name] = pivot[per_k_cols].sum(axis=1)
        
        # Add Result column
        pivot['Result'] = pivot.apply(
            lambda row: 'Pass' if row[self.config.total_column_name] < self.config.get_spec_for_media_type(row['Media Type'], row.get('Print Mode')) else 'Fail',
            axis=1
        )
        
        # Select final columns
        final_cols = groupby_cols.copy()
        final_cols.append('Tpages')        
        final_cols.extend(per_k_cols)
        final_cols.extend([self.config.total_column_name, 'Result'])
        
        pivot = pivot[final_cols]
        grand_total_groupby = groupby_cols[:-1]
        pivot = self._add_grand_totals(pivot, grand_total_groupby)
        
        return pivot
    
    def create_pivot_by_unit(self):
        """Create pivot table grouped by Unit."""
        groupby_cols = ['Test Condition', 'Input_Tray', 'Media Type', 'Print Mode']
        groupby_cols.extend(self.config.additional_groupby_cols)  # Add Print Quality here
        groupby_cols.append('Unit')
        
        # Aggregation rules
        agg_dict = {'Tpages': 'sum'}
        for col in self.error_output_columns:
            agg_dict[col] = 'sum'
        
        # Group and aggregate
        pivot = self.processed_data.groupby(groupby_cols, dropna=False).agg(agg_dict).reset_index()
        
        # Calculate per-K rate for each error column
        for col in self.error_output_columns:
            col_name = f'{col}/K'
            pivot[col_name] = (pivot[col] / pivot['Tpages']) * 1000
        
        # Calculate total
        per_k_cols = [f'{col}/K' for col in self.error_output_columns]
        pivot[self.config.total_column_name] = pivot[per_k_cols].sum(axis=1)
        
        # Add Result column
        pivot['Result'] = pivot.apply(
            lambda row: 'Pass' if row[self.config.total_column_name] < self.config.get_spec_for_media_type(row['Media Type'], row.get('Print Mode')) else 'Fail',
            axis=1
        )   
        
        # Select final columns
        final_cols = groupby_cols.copy()
        final_cols.append('Tpages')        
        final_cols.extend(per_k_cols)
        final_cols.extend([self.config.total_column_name, 'Result'])
        
        pivot = pivot[final_cols]
        grand_total_groupby = groupby_cols[:-1]
        pivot = self._add_grand_totals(pivot, grand_total_groupby)      

        return pivot
    
    def _add_grand_totals(self, df, groupby_cols):
        """Add grand total rows for each combination of groupby_cols."""
        result_rows = []
        combinations = df[groupby_cols].drop_duplicates().reset_index(drop=True)
        
        # Get per-K column names
        per_k_cols = [col for col in df.columns if col.endswith('/K') and col != self.config.total_column_name]
        
        for _, combo in combinations.iterrows():
            mask = True
            for col in groupby_cols:
                mask = mask & (df[col] == combo[col])
            
            subset = df[mask].copy()
            result_rows.append(subset)
            
            # Create grand total row
            grand_total = pd.DataFrame(columns=df.columns, index=[0])
            for col in groupby_cols:
                grand_total[col] = combo[col]
            
            # Set remaining grouping column to 'Grand Total'
            remaining_cols = [col for col in df.columns 
                            if col not in groupby_cols 
                            and col not in ['Tpages'] + per_k_cols + [self.config.total_column_name, 'Result']]
            if remaining_cols:
                grand_total[remaining_cols[0]] = 'Grand Total'
            
            # Calculate grand total Tpages
            total_tpages = subset['Tpages'].sum()
            grand_total['Tpages'] = total_tpages
            
            # Calculate weighted average for per-K columns
            for col in per_k_cols:
                if total_tpages > 0:
                    weighted_sum = (subset[col] * subset['Tpages'] / 1000).sum()
                    grand_total[col] = (weighted_sum / total_tpages) * 1000
                else:
                    grand_total[col] = 0.0
            
            # Calculate grand total for Total column
            if total_tpages > 0:
                weighted_sum = (subset[self.config.total_column_name] * subset['Tpages'] / 1000).sum()
                grand_total[self.config.total_column_name] = (weighted_sum / total_tpages) * 1000
            else:
                grand_total[self.config.total_column_name] = 0.0
            
            # Add Result for grand total
            media_type = combo['Media Type']
            print_mode = combo.get('Print Mode')
            spec = self.config.get_spec_for_media_type(media_type, print_mode)
            grand_total['Result'] = 'Pass' if grand_total[self.config.total_column_name].iloc[0] < spec else 'Fail'

            result_rows.append(grand_total)
        
        result = pd.concat(result_rows, ignore_index=True)
        return result