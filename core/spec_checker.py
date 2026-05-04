"""
spec_checker.py - Pre-generation spec coverage check.

Compares unique values in the raw data's dimension columns against what the
spec file explicitly lists.  A warning is raised for each column where the
raw data contains a value that does not appear in any spec row.

Wildcard rule: if ANY spec row has a blank cell for a column, that column is
fully covered (the blank acts as "match all") — no warning is raised for it.
"""

import pandas as pd


DIMENSION_COLS = ["Media Type", "Media Cat", "Print Mode", "Input Tray", "Print Quality"]

# Same aliases used by SpecValidator.cell_matches
_TRAY_ALIASES = {
    "mpt":          "multipurpose",
    "multipurpose": "multipurpose",
    "mp tray":      "multipurpose",
    "mp":           "multipurpose",
    "main":         "main",
    "adf":          "adf",
}


def _normalise(value):
    v = str(value).strip().lower()
    return _TRAY_ALIASES.get(v, v)


def check_spec_coverage(raw_file, spec_file):
    """
    Read raw data and spec file, then for each dimension column compare the
    unique values present in the raw data against those defined in the spec.

    Returns a (possibly empty) list of issue dicts:
        {
            "column":      str,        # e.g. "Input Tray"
            "missing":     [str, ...], # raw values not found in spec
            "spec_values": [str, ...], # all values the spec lists for this column
        }

    An empty list means all dimension values in the raw data are covered.
    """
    # ── Load raw data (use cache when available) ─────────────────────────────
    from core.pivot_generator import _RAW_DATA_CACHE, UnifiedPivotGenerator
    raw_df = _RAW_DATA_CACHE.get(raw_file)

    if raw_df is None:
        try:
            from core.auto_header_detector import find_header_row
            from core.column_matcher import standardize_column_names
            header_row = find_header_row(raw_file)
            raw_df = pd.read_excel(raw_file, header=header_row)
            raw_df = standardize_column_names(raw_df, UnifiedPivotGenerator.COLUMN_ALIASES)
        except Exception:
            return []

    # ── Detect spec sheet ────────────────────────────────────────────────────
    from core.spec_detector import detect_spec_sheet
    spec_sheet = detect_spec_sheet(raw_df, spec_file)
    if not spec_sheet:
        return []

    # ── Load spec (all rows — coverage is across all Spec Categories) ────────
    try:
        spec_df = pd.read_excel(spec_file, sheet_name=spec_sheet)
    except Exception:
        return []

    issues = []

    for col in DIMENSION_COLS:
        if col not in raw_df.columns:
            continue
        if col not in spec_df.columns:
            continue

        # Unique non-empty values from raw data (normalised)
        raw_vals = {
            _normalise(v)
            for v in raw_df[col].dropna().astype(str).str.strip()
            if v.strip() and v.strip().lower() not in ("nan", "none", "")
        }
        if not raw_vals:
            continue

        spec_col = spec_df[col]

        # Wildcard check: any blank cell in the spec column → full coverage
        has_wildcard = (
            spec_col.isna().any()
            or (spec_col.astype(str).str.strip() == "").any()
        )
        if has_wildcard:
            continue

        # Flatten comma-separated spec values and normalise
        spec_vals = set()
        for v in spec_col.dropna():
            for part in str(v).split(","):
                part = part.strip()
                if part:
                    spec_vals.add(_normalise(part))

        if not spec_vals:
            continue

        missing = sorted(raw_vals - spec_vals)
        if missing:
            issues.append({
                "column":      col,
                "missing":     missing,
                "spec_values": sorted(spec_vals),
            })

    return issues
