import pandas as pd


def build_groupby_columns(df, config, include_unit=False, include_media_name=False):
    """
    Dynamically build groupby columns list.
    """
    base_cols = [
        'Test Condition',
        'Test mode',
        'Media Cat',
        'Input Tray',
        'Media Type',
        'Print Mode'
    ]

    groupby_cols = [c for c in base_cols if c in df.columns]

    for col in config.additional_groupby_cols:
        if col in df.columns:
            groupby_cols.append(col)

    if include_media_name and 'Media Name' in df.columns:
        groupby_cols.append('Media Name')

    if include_unit and 'Unit' in df.columns:
        groupby_cols.append('Unit')

    return groupby_cols


def calculate_per_k_rates(pivot, error_cols):
    """
    Calculate error per-K rates.
    """
    for col in error_cols:
        pivot[f"{col}/K"] = ((pivot[col] / pivot['Tpages']) * 1000).round(3)

    return pivot


def calculate_total_rate(pivot, error_cols, total_col_name):
    """
    Calculate total error rate.
    """
    per_k_cols = [f"{c}/K" for c in error_cols]
    pivot[total_col_name] = pivot[per_k_cols].sum(axis=1).round(3)

    return pivot, per_k_cols


def apply_spec_validation(pivot, spec_validator, total_col):
    """
    Apply spec pass/fail evaluation.
    """
    if not spec_validator:
        pivot['Result'] = "NO SPEC PROVIDED"
        return pivot

    pivot['Spec Limit'] = None
    pivot['Result'] = None

    for idx, row in pivot.iterrows():
        spec_limit, actual_rate, result = spec_validator.evaluate(
            pivot_row=row,
            total_per_k_col=total_col
        )

        pivot.at[idx, 'Spec Limit'] = spec_limit
        pivot.at[idx, 'Result'] = result

    return pivot