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