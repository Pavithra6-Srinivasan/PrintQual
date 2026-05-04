"""
exclusion_filter.py - Read unique unit and media name values from a raw data file.

Used by the UI to populate the exclusion dialog before the pipeline runs.
"""

import pandas as pd
from core.auto_header_detector import find_header_row
from core.column_matcher import standardize_column_names


_COLUMN_ALIASES = {
    'Unit':       ['Unit', 'unit', 'Unit#', 'Unit No'],
    'Media Name': ['Media Name'],
}

_SKIP_VALUES = {"grand total", "nan", "none", ""}


def read_unique_values(raw_file):
    """
    Return (units, media_names) — sorted lists of unique values from the raw file.
    Uses the module-level raw data cache from pivot_generator if the file was
    already loaded; otherwise does a minimal read.
    """
    from core.pivot_generator import _RAW_DATA_CACHE

    if raw_file in _RAW_DATA_CACHE:
        df = _RAW_DATA_CACHE[raw_file]
    else:
        header_row = find_header_row(raw_file)
        df = pd.read_excel(raw_file, header=header_row)
        df = standardize_column_names(df, _COLUMN_ALIASES)

    units = _unique_col(df, "Unit")
    media_names = _unique_col(df, "Media Name")
    return units, media_names


def _unique_col(df, col):
    if col not in df.columns:
        return []
    vals = (
        df[col]
        .dropna()
        .astype(str)
        .str.strip()
    )
    vals = vals[~vals.str.lower().isin(_SKIP_VALUES)]
    return sorted(vals.unique().tolist())
