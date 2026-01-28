"""
Core module for generating pivot tables from raw printer quality test data.

Handles data loading, column standardization, error aggregation, and pivot
table creation with grand total calculations.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from core.excel_formatter import ExcelFormatter
from core.auto_header_detector import find_header_row

class UnifiedPivotGenerator:
    """
    Generates pivot tables for any test category based on configuration.
    """

    # Mapping of standard column names to their possible variations
    # Used to handle different naming conventions across data sources
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

        self.standardize_column_names()
        
        # Process error columns based on config
        self.prepare_error_columns()
    
    def standardize_column_names(self):
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

    def prepare_error_columns(self):
        """
        Process error columns based on configuration.
       
        This method handles two types of column specifications:
            1. Direct mapping: Single column → output column
            2. Column summing: Multiple columns → summed output column

        Column Matching:
            - First attempts exact column name match
            - Falls back to fuzzy matching (handles spacing/case variations)
            - Warns if columns cannot be found
        """
        self.processed_data = self.raw_data.copy()
        self.error_output_columns = []
        
        # Process each configured error column
        for output_col, input_spec in self.config.error_column_config.items():
            if isinstance(input_spec, list):
                # CASE 1: Sum multiple columns into one output column
                available_cols = []
                for col_name in input_spec:
                    # First try exact match
                    if col_name in self.raw_data.columns:
                        available_cols.append(col_name)
                    else:
                        # Try fuzzy match (handle spacing, underscores, etc.)
                        matched = self.find_fuzzy_column_match(col_name)
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

                    # Warn if some columns were not found
                    if len(available_cols) < len(input_spec):
                        missing = len(input_spec) - len(available_cols)
                        print(f"  ⚠ {output_col}: Found {len(available_cols)}/{len(input_spec)} columns (missing: {missing})")
                else:
                    print(f"  ✗ Warning: None of the columns found for {output_col}")
            else:
                # CASE 2: Direct column mapping (one-to-one)
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
            
        # Ensure Tpages is also numeric
        if 'Tpages' in self.processed_data.columns:
            self.processed_data['Tpages'] = pd.to_numeric(self.processed_data['Tpages'], errors='coerce').fillna(0)
    
    def find_fuzzy_column_match(self, target_col):
        """
        Find a column that closely matches the target name.
        
        Handles variations in:
            - Spacing: 'Media Type' vs 'MediaType'
            - Separators: 'Input_Tray' vs 'Input-Tray' vs 'Input Tray'
            - Case: 'Unit' vs 'unit' vs 'UNIT'        
        """
        
        # Normalize target: lowercase, replace separators with spaces
        target_normalized = target_col.lower().replace('_', ' ').replace('-', ' ').strip()
        
        # Check each column in raw data
        for col in self.raw_data.columns:
            col_normalized = str(col).lower().replace('_', ' ').replace('-', ' ').strip()
            
            # Check for exact match after normalization
            if target_normalized == col_normalized:
                return col
            
            # Check if one contains the other (for partial matches)
            if len(target_normalized) > 5:
                if target_normalized in col_normalized or col_normalized in target_normalized:
                    return col
        
        return None

    def create_pivot_by_media_name(self):
        """
        Create pivot table grouped by Media Name.

        Generates a pivot table that groups data by media type/name, showing
        error rates (per-K) and totals for each combination of:
            - Test Condition (always included)
            - Input Tray (if present)
            - Media Type (always included)
            - Print Mode (if present)
            - Print Quality (if configured)
            - Media Name (if present)
        
        Calculations:
            1. Sum Tpages and error counts for each group
            2. Calculate per-K rates: (errors / Tpages) * 1000
            3. Sum all per-K rates to get total error rate
            4. Determine Pass/Fail based on threshold specs
            5. Add grand totals with weighted averages
        """

        # Build groupby columns list dynamically based on what's available
        groupby_cols = ['Test Condition']

        if 'Input_Tray' in self.processed_data.columns:
            groupby_cols.append('Input_Tray')

        groupby_cols.extend(['Media Type'])
        if 'Print Mode' in self.processed_data.columns:
            groupby_cols.append('Print Mode')

        for col in self.config.additional_groupby_cols:
            if col in self.processed_data.columns:
                groupby_cols.append(col)   

        # Track if Media Name is included (determines if grand totals are needed)
        has_media_name = False
        if 'Media Name' in self.processed_data.columns:
            groupby_cols.append('Media Name')
            has_media_name = True
        
        # Define aggregation rules: sum Tpages and all error columns
        agg_dict = {'Tpages': 'sum'}
        for col in self.error_output_columns:
            agg_dict[col] = 'sum'
        
        # Group and aggregate
        pivot = self.processed_data.groupby(groupby_cols, dropna=False).agg(agg_dict).reset_index()
        
        # Calculate per-K rate for each error column
        # Formula: (errors / Tpages) * 1000 = errors per thousand pages
        for col in self.error_output_columns:
            col_name = f'{col}/K'
            pivot[col_name] = ((pivot[col] / pivot['Tpages']) * 1000).round(3)
        
        # Calculate total error rate (sum of all per-K rates)
        per_k_cols = [f'{col}/K' for col in self.error_output_columns]
        pivot[self.config.total_column_name] = (pivot[per_k_cols].sum(axis=1)).round(3)
        
        # Determine Pass/Fail based on threshold specifications
        pivot['Result'] = pivot.apply(
            lambda row: 'Pass' if row[self.config.total_column_name] < self.config.get_spec_for_media_type(row['Media Type'], row.get('Print Mode')) else 'Fail',
            axis=1
        )
        
        # Select final columns in desired order
        final_cols = groupby_cols.copy()
        final_cols.append('Tpages')        
        final_cols.extend(per_k_cols)
        final_cols.extend([self.config.total_column_name, 'Result'])
        
        pivot = pivot[final_cols]
        
        # Add grand totals only if Media Name exists and we have grouping
        if has_media_name and len(groupby_cols) > 1:
            grand_total_groupby = groupby_cols[:-1]  # Exclude Media Name
            pivot = self.add_grand_totals(pivot, grand_total_groupby)
        
        return pivot
    
    def create_pivot_by_unit(self):
        """
        Create pivot table grouped by Unit (printer unit ID).

        Grouping Columns:
        - Test Condition (always included)
        - Input Tray (if present)
        - Media Type (always included)
        - Print Mode (if present)
        - Print Quality (if configured)
        - Unit (always included)
        """

        # Build groupby columns (same as media pivot, but with Unit instead)
        groupby_cols = ['Test Condition']

        if 'Input_Tray' in self.processed_data.columns:
            groupby_cols.append('Input_Tray')

        groupby_cols.extend(['Media Type'])
        if 'Print Mode' in self.processed_data.columns:
            groupby_cols.append('Print Mode')

        for col in self.config.additional_groupby_cols:
            if col in self.processed_data.columns:
                groupby_cols.append(col)        
        
        # Always add Unit as the final grouping column
        groupby_cols.append('Unit')
        
        # Aggregation rules
        agg_dict = {'Tpages': 'sum'}
        for col in self.error_output_columns:
            agg_dict[col] = 'sum'
        
        # Group and aggregate
        pivot = self.processed_data.groupby(groupby_cols, dropna=False).agg(agg_dict).reset_index()
        
        # Calculate per-K rate for each error column
        # Formula: (errors / Tpages) * 1000 = errors per thousand pages 
        for col in self.error_output_columns:
            col_name = f'{col}/K'
            pivot[col_name] = ((pivot[col] / pivot['Tpages']) * 1000).round(3)
        
        # Calculate total error rate (sum of all per-K rates)
        per_k_cols = [f'{col}/K' for col in self.error_output_columns]
        pivot[self.config.total_column_name] = (pivot[per_k_cols].sum(axis=1)).round(3)
        
        # Determine Pass/Fail based on threshold specifications
        pivot['Result'] = pivot.apply(
            lambda row: 'Pass' if row[self.config.total_column_name] < self.config.get_spec_for_media_type(row['Media Type'], row.get('Print Mode')) else 'Fail',
            axis=1
        )   
        
        # Select final columns in desired order
        final_cols = groupby_cols.copy()
        final_cols.append('Tpages')        
        final_cols.extend(per_k_cols)
        final_cols.extend([self.config.total_column_name, 'Result'])
        
        pivot = pivot[final_cols]
        grand_total_groupby = groupby_cols[:-1]
        pivot = self.add_grand_totals(pivot, grand_total_groupby)      

        return pivot
    
    def add_grand_totals(self, df, groupby_cols):
        """
        Add grand total rows for each combination of grouping columns.

        Calculation Method:
            - Tpages: sum
            - Per-K rates: Weighted average using Tpages as weight
            - Total: Weighted average of total error rate
            - Result: Pass/Fail based on grand total vs threshold
        """

        result_rows = []
        combinations = df[groupby_cols].drop_duplicates().reset_index(drop=True)
        
        # Get per-K column names
        per_k_cols = [col for col in df.columns if col.endswith('/K') and col != self.config.total_column_name]

        # Identify which column should display "Grand Total"
        # This is the first column that's in the data but not in groupby_cols
        all_potential_groupby = ['Test Condition', 'Input_Tray', 'Media Type', 'Print Mode', 'Print Quality', 'Media Name', 'Unit']
        
        grand_total_col = None
        for col in all_potential_groupby:
            if col in df.columns and col not in groupby_cols:
                grand_total_col = col
                break
        
        # If no column for grand total, just return the dataframe as-is
        if grand_total_col is None:
            return df

        # Process each combination of groupby columns
        for _, combo in combinations.iterrows():
            # Create mask to filter data for this combination
            mask = True
            for col in groupby_cols:
                mask = mask & (df[col] == combo[col])
            
            # Skip if subset is empty
            subset = df[mask].copy()
            
            # Skip if subset is empty or has only 1 row
            if len(subset) == 0:
                continue
            
            # Add the data rows
            result_rows.append(subset)
            
            # Only add grand total if there are multiple rows to total
            if len(subset) <= 1:
                continue
            
            # Create grand total row
            grand_total = pd.DataFrame(columns=df.columns, index=[0])
            for col in groupby_cols:
                grand_total[col] = combo[col]
            
            # Set the grand total column
            grand_total[grand_total_col] = 'Grand Total'
            
            # Calculate weighted average for per-K columns
            # Formula: weighted_avg = sum(rate * pages / 1000) / total_pages * 1000
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
            
            # Determine Pass/Fail for grand total
            media_type = combo['Media Type']
            print_mode = combo.get('Print Mode')
            spec = self.config.get_spec_for_media_type(media_type, print_mode)
            grand_total['Result'] = 'Pass' if grand_total[self.config.total_column_name].iloc[0] < spec else 'Fail'

            result_rows.append(grand_total)
        
        # Concatenate all rows
        if len(result_rows) == 0:
            return df
        
        result = pd.concat(result_rows, ignore_index=True)
        return result