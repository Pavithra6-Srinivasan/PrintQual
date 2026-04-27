import re
import openpyxl


def detect_spec_sheet(raw_df, spec_file_path=None):
    """
    Detect which sheet in the spec file to use by matching the product name
    from 'Program & SKU' against the sheet names in the spec file.

    Matching rules (in priority order):
      1. Exact match (case-insensitive)
      2. Sheet name is a substring of the product string (longest match wins)
         e.g. product "Ruby Standard Paperpath" → sheet "Ruby Standard"
      3. Word-token overlap: sheet whose words best overlap with product words
         (most matching words wins; ties broken by longer sheet name)
         e.g. product "Ruby Life Test" → sheet "Ruby Topaz" matches on "Ruby"
    """
    if 'Program & SKU' not in raw_df.columns:
        print("✗ Program & SKU not found → cannot detect spec sheet")
        return None

    product_str = (
        raw_df['Program & SKU']
        .dropna()
        .astype(str)
        .iloc[0]
        .strip()
        if not raw_df['Program & SKU'].dropna().empty
        else ""
    )
    if not product_str:
        print("✗ Program & SKU is empty → cannot detect spec sheet")
        return None

    if not spec_file_path:
        print("✗ No spec file provided → cannot detect spec sheet")
        return None

    # Read sheet names from spec file
    try:
        wb = openpyxl.load_workbook(spec_file_path, read_only=True, data_only=True)
        sheet_names = wb.sheetnames
        wb.close()
    except Exception as e:
        print(f"✗ Could not read spec file sheets: {e}")
        return None

    product_lower = product_str.lower()

    # Priority 1: exact match (case-insensitive)
    for sheet in sheet_names:
        if sheet.lower() == product_lower:
            print(f"✓ Spec sheet matched (exact): {sheet}")
            return sheet

    # Priority 2: sheet name appears in product string — longest match wins
    candidates = [s for s in sheet_names if s.lower() in product_lower]
    if candidates:
        best = max(candidates, key=lambda s: len(s))
        print(f"✓ Spec sheet matched '{product_str}' → '{best}' (substring)")
        return best

    # Priority 3: word-token overlap
    product_tokens = set(product_lower.split())
    best_sheet  = None
    best_score  = 0

    for sheet in sheet_names:
        sheet_tokens = set(sheet.lower().split())
        overlap = len(product_tokens & sheet_tokens)
        if overlap > best_score or (overlap == best_score and best_sheet and len(sheet) > len(best_sheet)):
            best_score = overlap
            best_sheet = sheet

    if best_score > 0:
        print(f"✓ Spec sheet matched '{product_str}' → '{best_sheet}' (token overlap: {best_score} word(s))")
        return best_sheet

    print(f"⚠ No spec sheet matched for '{product_str}'")
    print(f"  Available sheets: {', '.join(sheet_names)}")
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

        # Pattern 1: FY__Q_
        match = re.search(r'FY(\d{2})Q([1-4])', name)
        if match:
            fy = int(match.group(1))
            quarter = int(match.group(2))
            year = 2000 + fy
            return year, quarter

        # Pattern 2: Q_FY__
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