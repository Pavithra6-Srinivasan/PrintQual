"""
pivot_generator.py - OPTIMIZED VERSION

Key optimizations:
1. Cached raw data reading (reads file only once)
2. Removed repetitive debug prints
3. Reuses spec validator across categories
"""

import pandas as pd
import numpy as np
from core.auto_header_detector import find_header_row
from core.spec_validator import SpecValidator
from core.column_matcher import standardize_column_names, prepare_error_columns
from core.spec_detector import detect_spec_sheet
from core.pivot_utils import build_groupby_columns, calculate_per_k_rates, calculate_total_rate, apply_spec_validation

# OPTIMIZATION 1: Cache raw data at module level
_RAW_DATA_CACHE = {}

class UnifiedPivotGenerator:
    """Generates pivot tables - OPTIMIZED."""

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
        'Unit': ['Unit', 'unit', 'Unit#', 'Unit #', 'Unit No', 'Unit Number'],
        'Tpages': ['Tpages', 'Tpages Printed', 'Actual Printed Sheets', 'Actual Run Pages', 'ADF TPages'],
        'Print Quality': ['Print Quality', 'Color/Quality']
    }
    
    # OPTIMIZATION 2: Shared spec validator cache
    _spec_validator_cache = {}
    
    def __init__(self, raw_data_file, test_config, spec_file_path=None, raw_data=None,
                 excluded_units=None, excluded_media_names=None, test_mode_filter=None):
        """
        Args:
            raw_data: Optional pre-loaded DataFrame to avoid re-reading file
            excluded_units: iterable of unit names to drop before any calculation
            excluded_media_names: iterable of media names to drop before any calculation
            test_mode_filter: if set, only rows where 'Test mode' matches this value
                              (case-insensitive) are kept
        """
        self.config = test_config
        self.spec_file_path = spec_file_path
        self.spec_validator = None
        self._excluded_units = set(excluded_units or [])
        self._excluded_media = set(excluded_media_names or [])
        self._test_mode_filter = test_mode_filter
        
        # OPTIMIZATION 1: Use cached or provided raw data
        if raw_data is not None:
            self.raw_data = raw_data
        elif raw_data_file in _RAW_DATA_CACHE:
            self.raw_data = _RAW_DATA_CACHE[raw_data_file]
        else:
            header_row = find_header_row(raw_data_file)
            self.raw_data = pd.read_excel(raw_data_file, header=header_row)
            self.raw_data = standardize_column_names(self.raw_data, self.COLUMN_ALIASES)
            _RAW_DATA_CACHE[raw_data_file] = self.raw_data
        
        # Normalise Test Condition: if the first value is "ambient" (any casing/
        # abbreviation like "Amb."), treat the whole column as Ambient so the
        # summary engine doesn't create separate groups for variant spellings.
        if 'Test Condition' in self.raw_data.columns:
            first_tc = (
                self.raw_data['Test Condition']
                .dropna()
                .astype(str)
                .str.strip()
                .iloc[0]
                .lower()
                if not self.raw_data['Test Condition'].dropna().empty
                else ""
            )
            if first_tc == "ambient" or first_tc.startswith("amb"):
                self.raw_data = self.raw_data.copy()
                self.raw_data['Test Condition'] = "Ambient"

        self.spec_sheet = detect_spec_sheet(self.raw_data, spec_file_path)

        result = prepare_error_columns(self.raw_data, self.config)

        if isinstance(result, tuple) and len(result) == 2:
            self.processed_data, self.error_output_columns = result
        else:
            self.processed_data = result if isinstance(result, pd.DataFrame) else pd.DataFrame()
            self.error_output_columns = []

        # Detect printer info before spec validator creation (validator needs variant/sub_assembly).
        # Reads from raw_data so can safely happen before any row filtering.
        if not hasattr(UnifiedPivotGenerator, '_detection_done'):
            self._detect_printer_info()
            UnifiedPivotGenerator._detection_done = True
            UnifiedPivotGenerator._cached_printer = self.detected_main_printer
            UnifiedPivotGenerator._cached_variant = self.detected_variant
            UnifiedPivotGenerator._cached_sub_assembly = self.sub_assembly
        else:
            self.detected_main_printer = UnifiedPivotGenerator._cached_printer
            self.detected_variant = UnifiedPivotGenerator._cached_variant
            self.sub_assembly = UnifiedPivotGenerator._cached_sub_assembly

        # Reuse spec validator if same parameters
        if spec_file_path and self.spec_sheet:
            cache_key = (spec_file_path, self.spec_sheet, self.config.name,
                        self.detected_variant, self.sub_assembly)
            if cache_key in self._spec_validator_cache:
                self.spec_validator = self._spec_validator_cache[cache_key]
            else:
                try:
                    self.spec_validator = SpecValidator(
                        spec_file_path=spec_file_path,
                        sheet_name=self.spec_sheet,
                        spec_category=self.config.name,
                        product=self.detected_variant,
                        sub_assembly=self.sub_assembly
                    )
                    self._spec_validator_cache[cache_key] = self.spec_validator
                except Exception as e:
                    pass  # Silently fail, validator stays None

        # Whether the spec differentiates by Input Tray determines two things below:
        # 1. whether blank-tray rows are dropped
        # 2. whether the Input Tray column is kept in processed_data (and thus groupby)
        self.spec_has_tray = self.spec_validator.has_tray if self.spec_validator else True


        # When the spec has no tray entries, remove the Input Tray column so it is
        # not picked up by build_groupby_columns and does not appear as a table heading.
        if not self.spec_has_tray:
            for tray_col in ["Input Tray", "Input_Tray", "Tray"]:
                if tray_col in self.processed_data.columns:
                    self.processed_data = self.processed_data.drop(columns=[tray_col])
                    break

        # Apply user-requested exclusions (units / media names)
        if self._excluded_units and "Unit" in self.processed_data.columns:
            before = len(self.processed_data)
            self.processed_data = self.processed_data[
                ~self.processed_data["Unit"].astype(str).str.strip().isin(self._excluded_units)
            ].reset_index(drop=True)
            dropped = before - len(self.processed_data)
            if dropped:
                print(f"⚠ Excluded {dropped} rows for {len(self._excluded_units)} unit(s)")

        if self._excluded_media and "Media Name" in self.processed_data.columns:
            before = len(self.processed_data)
            self.processed_data = self.processed_data[
                ~self.processed_data["Media Name"].astype(str).str.strip().isin(self._excluded_media)
            ].reset_index(drop=True)
            dropped = before - len(self.processed_data)
            if dropped:
                print(f"⚠ Excluded {dropped} rows for {len(self._excluded_media)} media name(s)")

        if self._test_mode_filter and "Test mode" in self.processed_data.columns:
            before = len(self.processed_data)
            self.processed_data = self.processed_data[
                self.processed_data["Test mode"]
                .astype(str).str.strip().str.upper()
                == self._test_mode_filter.strip().upper()
            ].reset_index(drop=True)
            print(f"✓ Filtered to Test mode '{self._test_mode_filter}': {len(self.processed_data)} rows (dropped {before - len(self.processed_data)})")

        # Drop duplicate columns (keep first) — duplicate column names cause
        # groupby().agg() to receive a DataFrame instead of a Series and crash.
        if self.processed_data.columns.duplicated().any():
            dupes = self.processed_data.columns[self.processed_data.columns.duplicated()].tolist()
            print(f"⚠ Dropping duplicate columns: {dupes}")
            self.processed_data = self.processed_data.loc[
                :, ~self.processed_data.columns.duplicated()
            ]

        self.numeric_columns = ['Tpages'] + self.error_output_columns

    def _detect_printer_info(self):
        """Extract printer metadata (only called once)."""
        self.detected_main_printer = None
        self.detected_variant = None
        self.sub_assembly = None

        if 'Test Name' in self.raw_data.columns:
            first_test = str(self.raw_data['Test Name'].dropna().iloc[0]).lower()
            if "adf" in first_test:
                self.sub_assembly = "ADF"
            elif any(keyword in first_test for keyword in ["paperpath", "cuslt", "life test", "ppth", "pppl"]):
                self.sub_assembly = "Paperpath"

        if not self.sub_assembly and 'Program & SKU' in self.raw_data.columns:
            first_sku = str(self.raw_data['Program & SKU'].dropna().iloc[0]).lower()
            if "adf" in first_sku:
                self.sub_assembly = "ADF"
            elif "paperpath" in first_sku or "cuslt" in first_sku:
                self.sub_assembly = "Paperpath"

        if not self.sub_assembly:
            self.sub_assembly = None

        if 'Program & SKU' in self.raw_data.columns:
            sku_series = self.raw_data['Program & SKU'].dropna().astype(str)
            if not sku_series.empty:
                raw_sku = sku_series.iloc[0].strip()
                raw_lower = raw_sku.lower()
                
                self.detected_main_printer = raw_sku.split()[0]
                
                if "ruby" in raw_lower:
                    self.detected_variant = "Ruby"
                elif "topaz" in raw_lower:
                    self.detected_variant = "Topaz"
                elif "prem plus" in raw_lower:
                    self.detected_variant = "Prem Plus"
                elif "hi" in raw_lower:
                    self.detected_variant = "Hi"
                elif "base" in raw_lower:
                    self.detected_variant = "Base"
                elif "sf" in raw_lower:
                    self.detected_variant = "SF"
                elif "plus" in raw_lower:
                    self.detected_variant = "Plus"
                elif "lite" in raw_lower:
                    self.detected_variant = "Lite"
                else:
                    self.detected_variant = None

    def extract_overview_info(self):
        """Extract overview information from raw data."""
        df = self.raw_data

        group = ""
        if "Group" in df.columns:
            vals = df["Group"].dropna()
            group = str(vals.iloc[0]).strip() if not vals.empty else ""

        description = ""
        if "Program & SKU" in df.columns:
            vals = df["Program & SKU"].dropna()
            description = str(vals.iloc[0]).strip() if not vals.empty else ""

        objective = ""
        if "Test Name" in df.columns:
            vals = df["Test Name"].dropna()
            objective = str(vals.iloc[0]).strip() if not vals.empty else ""

        unit_names = []
        unit_count = 0

        if "Unit" in df.columns:
            units = (
                df["Unit"]
                .dropna()
                .astype(str)
                .str.strip()
            )
            units = units[~units.str.lower().isin(["grand total", "nan"])]
            if self._excluded_units:
                units = units[~units.isin(self._excluded_units)]
            unit_names = sorted(units.unique())
            unit_count = len(unit_names)

        test_start = ""
        test_end = ""

        date_col = None
        for col in df.columns:
            col_lower = str(col).strip().lower()
            if col_lower == "date" or col_lower.startswith("date"):
                date_col = col
                break

        if date_col:
            raw_dates = df[date_col].dropna()
            # xlsb files return dates as Excel serial integers — convert those first
            if pd.api.types.is_integer_dtype(raw_dates) or pd.api.types.is_float_dtype(raw_dates):
                try:
                    dates = pd.to_datetime(raw_dates.astype(int), unit="D", origin="1899-12-30", errors="coerce").dropna()
                except Exception:
                    dates = pd.Series(dtype="datetime64[ns]")
            else:
                dates = pd.to_datetime(raw_dates, errors="coerce").dropna()
            if not dates.empty:
                test_start = dates.min().strftime("%d %b %Y")
                test_end = dates.max().strftime("%d %b %Y")

        test_condition = ""
        if "Test Condition" in df.columns:
            vals = df["Test Condition"].dropna().astype(str).str.strip()
            if not vals.empty:
                first_val = vals.iloc[0]
                test_condition = "Ambient" if first_val.lower() == "ambient" else "Climatic"

        project_phase = ""
        for col in df.columns:
            if str(col).strip().lower() == "project phase":
                vals = df[col].dropna().astype(str).str.strip()
                if not vals.empty:
                    project_phase = vals.iloc[0]
                break

        return {
            "group": group,
            "description": description,
            "objective": objective,
            "unit_count": unit_count,
            "unit_names": unit_names,
            "test_start": test_start,
            "test_end": test_end,
            "test_condition": test_condition,
            "project_phase": project_phase,
        }

    def create_pivot(self, include_unit=False, include_media_name=False):
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
        pivot, per_k_cols = calculate_total_rate(pivot, self.error_output_columns, self.config.total_column_name)
        pivot = apply_spec_validation(pivot, self.spec_validator, self.config.total_column_name)

        final_cols = groupby_cols + ['Tpages'] + per_k_cols + [self.config.total_column_name]

        if self.spec_validator:
            final_cols.append('Spec Limit')

        final_cols.append('Result')

        if 'Result' in pivot.columns:
            pivot['Result'] = pivot['Result'].astype(str).str.upper()

        pivot = pivot[final_cols]
        return pivot, groupby_cols

    def create_combined_pivot(self):
        """Create COMBINED pivot with both Media Name AND Unit."""
        groupby_cols = build_groupby_columns(
            self.processed_data,
            self.config,
            include_unit=True,
            include_media_name=True
        )

        agg_dict = {c: "sum" for c in self.numeric_columns if c in self.processed_data.columns}

        pivot = (
            self.processed_data
            .groupby(groupby_cols, dropna=False)
            .agg(agg_dict)
            .reset_index()
        )

        pivot = calculate_per_k_rates(pivot, self.error_output_columns)
        pivot, per_k_cols = calculate_total_rate(pivot, self.error_output_columns, self.config.total_column_name)
        pivot = apply_spec_validation(pivot, self.spec_validator, self.config.total_column_name)

        final_cols = groupby_cols + ['Tpages'] + per_k_cols + [self.config.total_column_name]

        if self.spec_validator:
            final_cols.append('Spec Limit')

        final_cols.append('Result')

        if 'Result' in pivot.columns:
            pivot['Result'] = pivot['Result'].astype(str).str.upper()

        pivot = pivot[final_cols]
        
        if 'Unit' in groupby_cols:
            grand_total_groupby = [col for col in groupby_cols if col != 'Unit']
            pivot = self.add_grand_totals(pivot, grand_total_groupby)

        return pivot
    
    def add_grand_totals(self, df, groupby_cols):
        """Add grand total rows - OPTIMIZED with vectorized operations."""
        grand_total_col = 'Unit'
        
        if grand_total_col not in df.columns:
            return df

        result_rows = []
        combinations = df[groupby_cols].drop_duplicates()
        
        per_k_cols = [col for col in df.columns 
                     if col.endswith('/K') and col != self.config.total_column_name]

        for _, combo in combinations.iterrows():
            # Vectorized mask creation — handle NaN values (NaN == NaN is False in pandas)
            mask = pd.Series(True, index=df.index)
            for col in groupby_cols:
                val = combo[col]
                if pd.isna(val):
                    mask &= df[col].isna()
                else:
                    mask &= (df[col] == val)
            
            subset = df[mask]
            
            if len(subset) == 0:
                continue
            
            result_rows.append(subset)
            
            # Create grand total row
            grand_total = pd.DataFrame(columns=df.columns, index=[0])
            for col in groupby_cols:
                grand_total[col] = combo[col]
            
            grand_total[grand_total_col] = 'Grand Total'
            total_tpages = subset['Tpages'].sum()
            grand_total['Tpages'] = total_tpages
            
            if total_tpages > 0:
                # Vectorized calculation for all per-K columns
                for col in per_k_cols:
                    weighted_sum = (subset[col] * subset['Tpages'] / 1000).sum()
                    grand_total[col] = round((weighted_sum / total_tpages) * 1000, 3)
                
                weighted_sum = (subset[self.config.total_column_name] * subset['Tpages'] / 1000).sum()
                grand_total[self.config.total_column_name] = round((weighted_sum / total_tpages) * 1000, 3)
            else:
                for col in per_k_cols:
                    grand_total[col] = 0.0
                grand_total[self.config.total_column_name] = 0.0
            
            if self.spec_validator:
                spec_limit, actual_rate, result = self.spec_validator.evaluate(
                    pivot_row=grand_total.iloc[0],
                    total_per_k_col=self.config.total_column_name,
                )
                grand_total['Spec Limit'] = spec_limit
                grand_total['Result'] = result.upper()
            else:
                grand_total['Result'] = 'NO SPEC PROVIDED'

            result_rows.append(grand_total)
        
        if len(result_rows) == 0:
            return df
        
        result = pd.concat(result_rows, ignore_index=True)
        
        if 'Result' in result.columns:
            result['Result'] = result['Result'].astype(str).str.upper()
        
        return result

    @staticmethod
    def clear_cache():
        """Clear all caches (call at end of processing)."""
        _RAW_DATA_CACHE.clear()
        UnifiedPivotGenerator._spec_validator_cache.clear()
        if hasattr(UnifiedPivotGenerator, '_detection_done'):
            delattr(UnifiedPivotGenerator, '_detection_done')