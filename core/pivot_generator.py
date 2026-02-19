"""
Core module for generating pivot tables from raw printer quality test data.

Handles data loading, column standardization, error aggregation, and pivot
table creation with grand total calculations.
"""

import pandas as pd
import numpy as np
from core.auto_header_detector import find_header_row
from core.spec_validator import SpecValidator
from core.detector import standardize_column_names, prepare_error_columns
from core.spec_detector import detect_spec_sheet

class UnifiedPivotGenerator:
    """
    Generates pivot tables for any test category based on configuration.
    """

    # Mapping of standard column names to their possible variations
    # Used to handle different naming conventions across data sources
    COLUMN_ALIASES = {
        'Test Name': ['Test Name', 'TestName', 'Test_Name', 'Test name'],
        'Program & SKU': ['Program & SKU', 'Program&SKU', 'Program_SKU'],
        'Test mode': ['Test mode', 'Test Mode'],
        'Input Tray': ['Input_Tray', 'Tray', 'Input Tray'],
        'Media Type': ['Media Type'],
        'Print Mode': ['Print Mode', 'Paper Mode', 'Run Type'],
        'Media Name': ['Media Name'],
        'Media Cat': ['Media Cat', 'Media Category'],
        'Test Condition': ['Test Condition', 'Test conditions'],
        'Unit': ['Unit', 'unit', 'Unit#', 'Unit No'],
        'Tpages': ['Tpages', 'Tpages Printed', 'Actual Printed Sheets', 'Actual Run Pages', 'ADF TPages'],
        'Print Quality': ['Print Quality', 'Color/Quality']
    }
    
    def __init__(self, raw_data_file, test_config, spec_file_path=None):
        """
        Args:
            raw_data_file: Path to raw data Excel file
            test_config: TestCategoryConfig object defining the category
            spec_file_path: Optional path to specification file
        """
        header_row = find_header_row(raw_data_file)

        self.raw_data = pd.read_excel(raw_data_file, header=header_row)
        self.config = test_config
        self.spec_file_path = spec_file_path
        self.spec_validator = None
        
        # Standardize column names using detector module
        self.raw_data = standardize_column_names(self.raw_data, self.COLUMN_ALIASES)
        
        # Auto-detect spec sheet name from raw data using detector module
        self.spec_sheet = detect_spec_sheet(self.raw_data)

        # Process error columns based on config
        result = prepare_error_columns(self.raw_data, self.config)

        if isinstance(result, tuple) and len(result) == 2:
            self.processed_data, self.error_output_columns = result
        else:
            self.processed_data = result if isinstance(result, pd.DataFrame) else pd.DataFrame()
            self.error_output_columns = []

        # Define numeric columns for aggregation
        self.numeric_columns = ['Tpages'] + self.error_output_columns
        
        # Process error columns based on config using detector module
        self.processed_data, self.error_output_columns = prepare_error_columns(
            self.raw_data,
            self.config
        )
        
        # Auto-detect product and sub assembly from raw data
        self.product = None
        self.sub_assembly = None

        # Detect from Test Name FIRST (more reliable)
        if 'Test Name' in self.raw_data.columns:
            first_test = str(self.raw_data['Test Name'].dropna().iloc[0]).lower()

            if "adf" in first_test:
                self.sub_assembly = "ADF"
            elif "paperpath" in first_test or "cuslt" in first_test:
                self.sub_assembly = "Paperpath"

        # Fallback to Program & SKU if still None
        if not self.sub_assembly and 'Program & SKU' in self.raw_data.columns:
            first_sku = str(self.raw_data['Program & SKU'].dropna().iloc[0]).lower()

            if "adf" in first_sku:
                self.sub_assembly = "ADF"
            elif "paperpath" in first_sku or "cuslt" in first_sku:
                self.sub_assembly = "Paperpath"

        if not self.sub_assembly:
            self.sub_assembly = "Unknown"

        # Detect product from Program & SKU
        if 'Program & SKU' in self.raw_data.columns:
            sku_series = self.raw_data['Program & SKU'].dropna().astype(str)
            if not sku_series.empty:
                self.product = sku_series.iloc[0].split()[0]
                
                print(f"[DETECTED] Sub Assembly: {self.sub_assembly}")

        # Initialize spec validator if spec file provided
        if spec_file_path and self.spec_sheet:
            try:
                self.spec_validator = SpecValidator(
                spec_file_path=spec_file_path,
                sheet_name=self.spec_sheet,
                spec_category=self.config.name,
                product=self.product,
                sub_assembly=self.sub_assembly
                )
                print(f"✓ Spec validator initialized using sheet: {self.spec_sheet}")
            except Exception as e:
                print(f"⚠ Spec validator init failed: {e}")
                self.spec_validator = None

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
        groupby_cols = []
        if 'Test Condition' in self.processed_data.columns:
            groupby_cols.append('Test Condition')

        if 'Test mode' in self.processed_data.columns:
            groupby_cols.append('Test mode')

        if 'Media Cat' in self.processed_data.columns:
            groupby_cols.append('Media Cat')

        if 'Input_Tray' in self.processed_data.columns:
            groupby_cols.append('Input_Tray')

        if 'Media Type' in self.processed_data.columns:
            groupby_cols.append('Media Type')

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
        agg_dict = {col: "sum" for col in self.numeric_columns if col in self.processed_data.columns}

        # Before groupby, ensure each column is a Series
        for col in agg_dict:
            if isinstance(self.processed_data[col], pd.DataFrame):
                self.processed_data[col] = self.processed_data[col].squeeze()
        
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
        
        # Determine Pass/Fail based on spec file if available, otherwise use threshold specs
        if self.spec_validator:
            print("  Using spec file for validation...")
            pivot['Spec Limit'] = None
            pivot['Result'] = None
            
            for idx, row in pivot.iterrows():
                spec_limit, actual_rate, result = self.spec_validator.evaluate(
                    pivot_row=row,
                    total_per_k_col=self.config.total_column_name
                )
                pivot.at[idx, 'Spec Limit'] = spec_limit
                pivot.at[idx, 'Result'] = result
        else:
            # No spec file provided - cannot validate
            print("  ⚠ No spec file provided - skipping validation")
            pivot['Result'] = 'NO SPEC FILE'

        # Select final columns in desired order
        final_cols = groupby_cols.copy()
        final_cols.append('Tpages')        
        final_cols.extend(per_k_cols)
        final_cols.append(self.config.total_column_name)
        if self.spec_validator:
            final_cols.append('Spec Limit')
        final_cols.append('Result')
        
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
        groupby_cols = []
        if 'Test Condition' in self.processed_data.columns:
            groupby_cols.append('Test Condition')

        if 'Test mode' in self.processed_data.columns:
            groupby_cols.append('Test mode')

        if 'Media Cat' in self.processed_data.columns:
            groupby_cols.append('Media Cat')

        if 'Input_Tray' in self.processed_data.columns:
            groupby_cols.append('Input_Tray')

        if 'Media Type' in self.processed_data.columns:
            groupby_cols.append('Media Type')

        if 'Print Mode' in self.processed_data.columns:
            groupby_cols.append('Print Mode')

        for col in self.config.additional_groupby_cols:
            if col in self.processed_data.columns:
                groupby_cols.append(col)        
        
        # Always add Unit as the final grouping column
        groupby_cols.append('Unit')
        
        # Aggregation rules
        agg_dict = {col: "sum" for col in self.numeric_columns if col in self.processed_data.columns}

        # Before groupby, ensure each column is a Series
        for col in agg_dict:
            if isinstance(self.processed_data[col], pd.DataFrame):
                self.processed_data[col] = self.processed_data[col].squeeze()
        
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
        
        # Calculate total error rate (sum of all per-K rates)
        per_k_cols = [f'{col}/K' for col in self.error_output_columns]
        pivot[self.config.total_column_name] = (pivot[per_k_cols].sum(axis=1)).round(3)
        
        # Determine Pass/Fail based on spec file if available, otherwise use threshold specs
        if self.spec_validator:
            print("  Using spec file for validation...")
            pivot['Spec Limit'] = None
            pivot['Result'] = None
            
            for idx, row in pivot.iterrows():
                spec_limit, actual_rate, result = self.spec_validator.evaluate(
                    pivot_row=row,
                    total_per_k_col=self.config.total_column_name
                )
                pivot.at[idx, 'Spec Limit'] = spec_limit
                pivot.at[idx, 'Result'] = result
        else:
            # No spec file provided - cannot validate
            print("  ⚠ No spec file provided - skipping validation")
            pivot['Result'] = 'NO SPEC FILE'
        
        # Select final columns in desired order
        final_cols = groupby_cols.copy()
        final_cols.append('Tpages')        
        final_cols.extend(per_k_cols)
        final_cols.append(self.config.total_column_name)
        if self.spec_validator:
            final_cols.append('Spec Limit')
        final_cols.append('Result')
        
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
            
           # Determine Pass/Fail for grand total using spec validator
            if self.spec_validator:
                spec_limit, actual_rate, result = self.spec_validator.evaluate(
                    pivot_row=grand_total.iloc[0],
                    total_per_k_col=self.config.total_column_name,
                )
                grand_total['Spec Limit'] = spec_limit
                grand_total['Result'] = result
            else:
                grand_total['Result'] = 'NO SPEC FILE'

            result_rows.append(grand_total)
        
        # Concatenate all rows
        if len(result_rows) == 0:
            return df
        
        result = pd.concat(result_rows, ignore_index=True)
        return result