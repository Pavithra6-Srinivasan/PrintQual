import pandas as pd

def standardize_column_names(df, column_aliases):
    """
    Rename columns in df using provided dictionary.
    Strips whitespace from all column names first, then tries
    exact match followed by case-insensitive match.
    """
    df = df.copy()
    # Strip leading/trailing whitespace from every column name
    df.columns = [str(c).strip() for c in df.columns]

    # Build a case-insensitive lookup of current column names
    col_lower_map = {str(c).lower(): c for c in df.columns}

    rename_map = {}
    for standard_name, aliases in column_aliases.items():
        for alias in aliases:
            # 1. Exact match
            if alias in df.columns:
                rename_map[alias] = standard_name
                break
            # 2. Case-insensitive match
            if alias.lower() in col_lower_map:
                rename_map[col_lower_map[alias.lower()]] = standard_name
                break

    df.rename(columns=rename_map, inplace=True)
    return df

def prepare_error_columns(raw_data, config):
    """
    Process error columns based on configuration.
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

    # Normalise Tpages once after all error columns are processed
    if 'Tpages' in processed_data.columns:
        col = processed_data['Tpages']
        if isinstance(col, pd.Series):
            processed_data['Tpages'] = pd.to_numeric(col, errors='coerce').fillna(0)
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
    Find a column that exactly matches the target name (case-insensitive).
    """
    target_normalized = target_col.lower().replace('_', ' ').replace('-', ' ').strip()

    for col in df.columns:
        col_normalized = str(col).lower().replace('_', ' ').replace('-', ' ').strip()

        if target_normalized == col_normalized:
            return col

    return None