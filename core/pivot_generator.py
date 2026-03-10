"""
Generates pivot tables from raw test data.

Handles data loading, column standardization and pivot
table creation with grand total calculations.
"""

import pandas as pd
import numpy as np
from core.auto_header_detector import find_header_row
from core.spec_validator import SpecValidator
from core.column_matcher import standardize_column_names, prepare_error_columns
from core.spec_detector import detect_spec_sheet
from core.pivot_utils import build_groupby_columns, calculate_per_k_rates, calculate_total_rate, apply_spec_validation

class UnifiedPivotGenerator:
    """
    Generates pivot tables for any test category based on configuration.
    """

    # Mapping of standard column names to different naming conventions across data sources
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

        self.numeric_columns = ['Tpages'] + self.error_output_columns
        
        # Auto-detect product and sub assembly from raw data
        self.detected_main_printer = None
        self.detected_variant = None
        self.sub_assembly = None

        # Detect from Test Name if available
        if 'Test Name' in self.raw_data.columns:
            first_test = str(self.raw_data['Test Name'].dropna().iloc[0]).lower()

            if "adf" in first_test:
                self.sub_assembly = "ADF"
            elif any(keyword in first_test for keyword in ["paperpath", "cuslt", "life test"]):
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

        # Detect product + variant from Program & SKU
        if 'Program & SKU' in self.raw_data.columns:

            sku_series = self.raw_data['Program & SKU'].dropna().astype(str)

            if not sku_series.empty:

                raw_sku = sku_series.iloc[0].strip()
                raw_lower = raw_sku.lower()

                # Detect MAIN printer name
                self.detected_main_printer = raw_sku.split()[0]

                # Detect VARIANT
                if "hi" in raw_lower:
                    self.detected_variant = "Hi"
                elif "base" in raw_lower:
                    self.detected_variant = "Base"
                elif "sf" in raw_lower:
                    self.detected_variant = "SF"
                else:
                    self.detected_variant = "Standard"

                print(f"[DETECTED] Main Printer: {self.detected_main_printer}")
                print(f"[DETECTED] Variant: {self.detected_variant}")
                print(f"[DETECTED] Sub Assembly: {self.sub_assembly}")

        # Initialize spec validator if spec file provided
        if spec_file_path and self.spec_sheet:
            try:
                self.spec_validator = SpecValidator(
                    spec_file_path=spec_file_path,
                    sheet_name=self.spec_sheet,
                    spec_category=self.config.name,
                    product=self.detected_variant,
                    sub_assembly=self.sub_assembly
                )
                print(f"✓ Spec validator initialized using sheet: {self.spec_sheet}")
            except Exception as e:
                print(f"⚠ Spec validator init failed: {e}")
                self.spec_validator = None

    def _create_pivot(self, include_unit=False, include_media_name=False):

        groupby_cols = build_groupby_columns(
            self.processed_data,
            self.config,
            include_unit=include_unit,
            include_media_name=include_media_name
        )

        agg_dict = {c: "sum" for c in self.numeric_columns if c in self.processed_data.columns}

        pivot = (
            self.processed_data
            .groupby(groupby_cols, dropna=False)
            .agg(agg_dict)
            .reset_index()
        )

        pivot = calculate_per_k_rates(pivot, self.error_output_columns)

        pivot, per_k_cols = calculate_total_rate(
            pivot,
            self.error_output_columns,
            self.config.total_column_name
        )

        pivot = apply_spec_validation(
            pivot,
            self.spec_validator,
            self.config.total_column_name
        )

        final_cols = groupby_cols + ['Tpages'] + per_k_cols + [self.config.total_column_name]

        if self.spec_validator:
            final_cols.append('Spec Limit')

        final_cols.append('Result')

        pivot = pivot[final_cols]

        return pivot, groupby_cols

    def create_pivot_by_media_name(self):

        pivot, groupby_cols = self._create_pivot(include_media_name=True)

        if len(groupby_cols) > 1:
            pivot = self.add_grand_totals(pivot, groupby_cols[:-1])

        return pivot
    
    def create_pivot_by_unit(self):

        pivot, groupby_cols = self._create_pivot(include_unit=True)

        pivot = self.add_grand_totals(pivot, groupby_cols[:-1])

        return pivot
    
    def add_grand_totals(self, df, groupby_cols):
        """
        Add grand total rows for each combination of grouping columns.
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
        
        if grand_total_col is None:
            return df

        # Process each combination of groupby columns
        for _, combo in combinations.iterrows():
            # Create mask to filter data for this combination
            mask = True
            for col in groupby_cols:
                mask = mask & (df[col] == combo[col])
            
            subset = df[mask].copy()
            
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
                grand_total['Result'] = 'NO SPEC PROVIDED'

            result_rows.append(grand_total)
        
        if len(result_rows) == 0:
            return df
        
        result = pd.concat(result_rows, ignore_index=True)
        return result