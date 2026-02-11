import pandas as pd
import numpy as np
from pathlib import Path

def standardize_column_names(df, column_aliases):
    """
    Rename columns in df using provided alias dictionary.
    """
    df = df.copy()
    
    rename_map = {}

    for standard_name, aliases in column_aliases.items():
        for alias in aliases:
            if alias in df.columns:
                rename_map[alias] = standard_name

    df.rename(columns=rename_map, inplace=True)
    return df

def prepare_error_columns(raw_data, config):
    """
    Process error columns based on configuration.
    Returns:
        processed_df, error_output_columns
    """

    processed_data = raw_data.copy()
    error_output_columns = []

    for output_col, input_spec in config.error_column_config.items():

        # ---------------- MULTI-COLUMN SUM ----------------
        if isinstance(input_spec, list):
            available_cols = []

            for col_name in input_spec:
                if col_name in raw_data.columns:
                    available_cols.append(col_name)
                else:
                    matched = find_fuzzy_column_match(raw_data, col_name)
                    if matched:
                        available_cols.append(matched)

            if available_cols:
                numeric_cols = [
                    pd.to_numeric(raw_data[col], errors='coerce').fillna(0)
                    for col in available_cols
                ]

                processed_data[output_col] = pd.concat(numeric_cols, axis=1).sum(axis=1)
                error_output_columns.append(output_col)

                if len(available_cols) < len(input_spec):
                    missing = len(input_spec) - len(available_cols)
                    print(f"  ⚠ {output_col}: Found {len(available_cols)}/{len(input_spec)} columns (missing: {missing})")
            else:
                print(f"  ✗ Warning: None of the columns found for {output_col}")

        # ---------------- SINGLE COLUMN ----------------
        else:
            if input_spec in raw_data.columns:
                processed_data[output_col] = pd.to_numeric(raw_data[input_spec], errors='coerce').fillna(0)
                error_output_columns.append(output_col)
            else:
                matched = find_fuzzy_column_match(raw_data, input_spec)
                if matched:
                    processed_data[output_col] = pd.to_numeric(raw_data[matched], errors='coerce').fillna(0)
                    error_output_columns.append(output_col)
                    print(f"  ~ Mapped '{input_spec}' → '{matched}'")
                else:
                    print(f"  ✗ Warning: Column '{input_spec}' not found")

        # Ensure Tpages numeric
        if 'Tpages' in processed_data.columns:
            col = processed_data['Tpages']

            # Case 1: Proper Series
            if isinstance(col, pd.Series):
                processed_data['Tpages'] = pd.to_numeric(col, errors='coerce').fillna(0)

            # Case 2: Duplicate columns → sum them row-wise
            elif isinstance(col, pd.DataFrame):
                print("⚠ Multiple Tpages columns detected — summing them")
                processed_data['Tpages'] = (
                    col.apply(pd.to_numeric, errors='coerce')
                    .fillna(0)
                    .sum(axis=1)
                )

    return processed_data, error_output_columns

def find_fuzzy_column_match(df, target_col):
    """
    Find a column that closely matches the target name.
    """
    target_normalized = target_col.lower().replace('_', ' ').replace('-', ' ').strip()

    for col in df.columns:
        col_normalized = str(col).lower().replace('_', ' ').replace('-', ' ').strip()

        if target_normalized == col_normalized:
            return col

        if len(target_normalized) > 5:
            if target_normalized in col_normalized or col_normalized in target_normalized:
                return col

    return None