import re

import pandas as pd
from core.auto_header_detector import find_header_row

def detect_spec_sheet(raw_df):
    """
    Detect which sheet in the spec file to use.
    Input: raw_df (DataFrame)
    Output: sheet name or None
    """

    if 'Program & SKU' not in raw_df.columns:
        print("✗ Program & SKU not found → cannot detect spec sheet")
        return None

    values = raw_df['Program & SKU'].dropna().astype(str).str.lower()

    if values.str.contains('marconi').any():
        print("✓ Spec sheet detected: Marconi")
        return 'Marconi'

    if values.str.contains('moreto').any():
        print("✓ Spec sheet detected: Moreto")
        return 'Moreto'

    print("⚠ Could not detect spec sheet from Program & SKU")
    return None

def extract_year_quarter(filename: str):
        """
        Extract fiscal year and quarter from filename.

        Supported formats:
            FY25Q1
            Q1FY25

        Returns:
            (year, quarter) -> (2025, 1)
        """

        name = filename.upper()

        # Pattern 1: FY25Q1
        match = re.search(r'FY(\d{2})Q([1-4])', name)
        if match:
            fy = int(match.group(1))
            quarter = int(match.group(2))
            year = 2000 + fy
            return year, quarter

        # Pattern 2: Q1FY25
        match = re.search(r'Q([1-4])FY(\d{2})', name)
        if match:
            quarter = int(match.group(1))
            fy = int(match.group(2))
            year = 2000 + fy
            return year, quarter

        raise ValueError(
            "Cannot detect fiscal year and quarter from filename. "
            "Expected format like FY25Q1 or Q1FY25."
        )