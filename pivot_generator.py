"""
Pivot table generator that handles all test categories.
Supports both direct column mapping and column summing.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from excel_formatter import ExcelFormatter

def find_header_row(file_path, required_columns=None, max_search_rows=20):
    """
    Automatically detect which row contains the column headers.
    Rule: If "Test Condition" column is found, that row is the header.
    """
    
    # Read the file without assuming any header position
    try:
        df_test = pd.read_excel(file_path, header=None, nrows=max_search_rows)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return 1
    
    key_columns = ['test condition', 'media type', 'unit']
    
    best_match = {'row': 1, 'score': 0}
    
    # Look for row with "Test Condition" AND other key columns
    for row_idx in range(min(max_search_rows, len(df_test))):
        row_values = df_test.iloc[row_idx].astype(str).str.strip().str.lower().tolist()
        
        # Count how many key columns are present
        score = 0
        for key_col in key_columns:
            if any(key_col in val for val in row_values):
                score += 1
        
        # Must have at least 2 out of 3 key columns to be considered
        if score >= 2 and score > best_match['score']:
            best_match = {'row': row_idx, 'score': score}
    
    # If we found a good match
    if best_match['score'] >= 2:
        row_values = df_test.iloc[best_match['row']].astype(str).str.strip().tolist()
        print(f"✓ Header row detected at row {best_match['row']} (found {best_match['score']}/3 key columns)")
        print(f"  Sample columns: {[v for v in row_values[:10] if v not in ['', 'nan', 'None']]}")
        return best_match['row']
    
    # Fallback: Look for row with most column-like strings
    for row_idx in range(min(max_search_rows, len(df_test))):
        row_values = df_test.iloc[row_idx]
        non_empty = [str(v).strip() for v in row_values if str(v).strip() and str(v).lower() not in ['nan', 'none']]
        
        # Header rows typically have many non-empty string values
        if len(non_empty) >= 8:
            print(f"⚠ Header row guessed at row {row_idx} ({len(non_empty)} non-empty columns)")
            print(f"  Sample columns: {non_empty[:10]}")
            return row_idx
        
    print(f"  Defaulting to row 2")
    return 1

class UnifiedPivotGenerator:
    COLUMN_ALIASES = {
        'Input_Tray': ['Input_Tray', 'Tray', 'Input Tray'],
        'Media Type': ['Media Type'],
        'Print Mode': ['Print Mode', 'Paper Mode', 'Run Type'],
        'Media Name': ['Media Name'],
        'Test Condition': ['Test Condition', 'Test conditions'],
        'Unit': ['Unit', 'unit', 'Unit#'],
        'Tpages': ['Tpages', 'Tsheets Printed', 'Tpages Printed', 'Actual Printed Sheets', 'Actual Run Pages'],
        'Print Quality': ['Print Quality', 'Color/Quality']
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
        Uses fuzzy matching to find columns with slight name variations.
        Converts all error columns to numeric, replacing non-numeric values with 0.
        """
        self.processed_data = self.raw_data.copy()
        self.error_output_columns = []
                
        for output_col, input_spec in self.config.error_column_config.items():
            if isinstance(input_spec, list):
                # Sum multiple columns - try to find each with fuzzy matching
                available_cols = []
                for col_name in input_spec:
                    # First try exact match
                    if col_name in self.raw_data.columns:
                        available_cols.append(col_name)
                    else:
                        # Try fuzzy match (handle spacing, underscores, etc.)
                        matched = self._find_fuzzy_column_match(col_name)
                        if matched:
                            available_cols.append(matched)
                
                if available_cols:
                    # Convert all columns to numeric, replacing errors with 0
                    numeric_cols = []
                    for col in available_cols:
                        numeric_cols.append(pd.to_numeric(self.raw_data[col], errors='coerce').fillna(0))
                    
                    # Sum the numeric columns
                    self.processed_data[output_col] = pd.concat(numeric_cols, axis=1).sum(axis=1)
                    self.error_output_columns.append(output_col)
                    
                    if len(available_cols) < len(input_spec):
                        missing = len(input_spec) - len(available_cols)
                        print(f"  ⚠ {output_col}: Found {len(available_cols)}/{len(input_spec)} columns (missing: {missing})")
                else:
                    print(f"  ✗ Warning: None of the columns found for {output_col}")
            else:
                # Direct column mapping
                if input_spec in self.raw_data.columns:
                    # Convert to numeric, replacing errors with 0
                    self.processed_data[output_col] = pd.to_numeric(self.raw_data[input_spec], errors='coerce').fillna(0)
                    self.error_output_columns.append(output_col)
                else:
                    # Try fuzzy match
                    matched = self._find_fuzzy_column_match(input_spec)
                    if matched:
                        # Convert to numeric, replacing errors with 0
                        self.processed_data[output_col] = pd.to_numeric(self.raw_data[matched], errors='coerce').fillna(0)
                        self.error_output_columns.append(output_col)
                        print(f"  ~ Mapped '{input_spec}' → '{matched}'")
                    else:
                        print(f"  ✗ Warning: Column '{input_spec}' not found")
            
        # Also ensure Tpages is numeric
        if 'Tpages' in self.processed_data.columns:
            self.processed_data['Tpages'] = pd.to_numeric(self.processed_data['Tpages'], errors='coerce').fillna(0)
    
    def _find_fuzzy_column_match(self, target_col):
        """
        Find a column that closely matches the target name.
        Handles variations in spacing, underscores, and case.
        """
        # Normalize target
        target_normalized = target_col.lower().replace('_', ' ').replace('-', ' ').strip()
        
        for col in self.raw_data.columns:
            col_normalized = str(col).lower().replace('_', ' ').replace('-', ' ').strip()
            
            # Check for exact match after normalization
            if target_normalized == col_normalized:
                return col
            
            # Check if one contains the other (for partial matches)
            if len(target_normalized) > 5:  # Only for longer column names
                if target_normalized in col_normalized or col_normalized in target_normalized:
                    return col
        
        return None

    def create_pivot_by_media_name(self):
        """Create pivot table grouped by Media Name."""
        groupby_cols = ['Test Condition']

        # Add Input_Tray only if it exists
        if 'Input_Tray' in self.processed_data.columns:
            groupby_cols.append('Input_Tray')

        groupby_cols.extend(['Media Type'])
        if 'Print Mode' in self.processed_data.columns:
            groupby_cols.append('Print Mode')

        for col in self.config.additional_groupby_cols:
            if col in self.processed_data.columns:
                groupby_cols.append(col)   

        # Track if Media Name was added
        has_media_name = False
        if 'Media Name' in self.processed_data.columns:
            groupby_cols.append('Media Name')
            has_media_name = True
        
        # Aggregation rules
        agg_dict = {'Tpages': 'sum'}
        for col in self.error_output_columns:
            agg_dict[col] = 'sum'
        
        # Group and aggregate
        pivot = self.processed_data.groupby(groupby_cols, dropna=False).agg(agg_dict).reset_index()
        
        # Calculate per-K rate for each error column
        for col in self.error_output_columns:
            col_name = f'{col}/K'
            pivot[col_name] = ((pivot[col] / pivot['Tpages']) * 1000).round(3)
        
        # Calculate total
        per_k_cols = [f'{col}/K' for col in self.error_output_columns]
        pivot[self.config.total_column_name] = (pivot[per_k_cols].sum(axis=1)).round(3)
        
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
        
        # Only add grand totals if we have Media Name column (otherwise there's nothing to total)
        if has_media_name and len(groupby_cols) > 1:
            grand_total_groupby = groupby_cols[:-1]  # Exclude Media Name
            pivot = self._add_grand_totals(pivot, grand_total_groupby)
        
        return pivot
    
    def create_pivot_by_unit(self):
        """Create pivot table grouped by Unit."""
        groupby_cols = ['Test Condition']

        # Add Input_Tray only if it exists
        if 'Input_Tray' in self.processed_data.columns:
            groupby_cols.append('Input_Tray')

        groupby_cols.extend(['Media Type'])
        if 'Print Mode' in self.processed_data.columns:
            groupby_cols.append('Print Mode')

        for col in self.config.additional_groupby_cols:
            if col in self.processed_data.columns:
                groupby_cols.append(col)        
                
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
            pivot[col_name] = ((pivot[col] / pivot['Tpages']) * 1000).round(3)
        
        # Calculate total
        per_k_cols = [f'{col}/K' for col in self.error_output_columns]
        pivot[self.config.total_column_name] = (pivot[per_k_cols].sum(axis=1)).round(3)
        
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
        
        # Identify which column should show "Grand Total"
        all_potential_groupby = ['Test Condition', 'Input_Tray', 'Media Type', 'Print Mode', 'Print Quality', 'Media Name', 'Unit']
        grand_total_col = None
        for col in all_potential_groupby:
            if col in df.columns and col not in groupby_cols:
                grand_total_col = col
                break
        
        # If no column for grand total, just return the dataframe as-is
        if grand_total_col is None:
            return df

        for _, combo in combinations.iterrows():
            mask = True
            for col in groupby_cols:
                mask = mask & (df[col] == combo[col])
            
            subset = df[mask].copy()
            
            # ✅ FIX: Skip if subset is empty or has only 1 row
            if len(subset) == 0:
                continue
            
            # Add the data rows
            result_rows.append(subset)
            
            # ✅ FIX: Only add grand total if there are multiple rows to total
            if len(subset) <= 1:
                continue
            
            # Create grand total row
            grand_total = pd.DataFrame(columns=df.columns, index=[0])
            for col in groupby_cols:
                grand_total[col] = combo[col]
            
            # Set the grand total column
            grand_total[grand_total_col] = 'Grand Total'
            
            # Calculate grand total Tpages
            total_tpages = subset['Tpages'].sum()
            grand_total['Tpages'] = total_tpages
            
            # Calculate weighted average for per-K columns
            for col in per_k_cols:
                if total_tpages > 0:
                    weighted_sum = (subset[col] * subset['Tpages'] / 1000).sum()
                    grand_total[col] = round((weighted_sum / total_tpages) * 1000, 3)
                else:
                    grand_total[col] = 0.0
            
            # Calculate grand total for Total column
            if total_tpages > 0:
                weighted_sum = (subset[self.config.total_column_name] * subset['Tpages'] / 1000).sum()
                grand_total[self.config.total_column_name] = round((weighted_sum / total_tpages) * 1000, 3)
            else:
                grand_total[self.config.total_column_name] = 0.0
            
            # Add Result for grand total
            media_type = combo['Media Type']
            print_mode = combo.get('Print Mode')
            spec = self.config.get_spec_for_media_type(media_type, print_mode)
            grand_total['Result'] = 'Pass' if grand_total[self.config.total_column_name].iloc[0] < spec else 'Fail'

            result_rows.append(grand_total)
        
        if len(result_rows) == 0:
            return df
        
        result = pd.concat(result_rows, ignore_index=True)
        return result