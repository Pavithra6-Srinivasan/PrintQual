"""
auto_header_detector.py
If "Test Condition" is found, that's the header row.
"""

import pandas as pd

def find_header_row(file_path, required_columns=None, max_search_rows=20):
    """
    Automatically detect which row contains the column headers.
    Rule: If "Test Condition" column is found, that row is the header.
    """
    
    # Read the file without assuming any header position
    try:
        df_test = pd.read_excel(file_path, header=None, nrows=max_search_rows)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return 1
    
    key_columns = ['test condition', 'media type', 'unit']
    
    best_match = {'row': 1, 'score': 0}
    
    # Look for row with "Test Condition" AND other key columns
    for row_idx in range(min(max_search_rows, len(df_test))):
        row_values = df_test.iloc[row_idx].astype(str).str.strip().str.lower().tolist()
        
        # Count how many key columns are present
        score = 0
        for key_col in key_columns:
            if any(key_col in val for val in row_values):
                score += 1
        
        # Must have at least 2 out of 3 key columns to be considered
        if score >= 2 and score > best_match['score']:
            best_match = {'row': row_idx, 'score': score}
    
    # If we found a good match
    if best_match['score'] >= 2:
        row_values = df_test.iloc[best_match['row']].astype(str).str.strip().tolist()
        print(f"✓ Header row detected at row {best_match['row']} (found {best_match['score']}/3 key columns)")
        print(f"  Sample columns: {[v for v in row_values[:10] if v not in ['', 'nan', 'None']]}")
        return best_match['row']
    
    # Fallback: Look for row with most column-like strings
    for row_idx in range(min(max_search_rows, len(df_test))):
        row_values = df_test.iloc[row_idx]
        non_empty = [str(v).strip() for v in row_values if str(v).strip() and str(v).lower() not in ['nan', 'none']]
        
        # Header rows typically have many non-empty string values
        if len(non_empty) >= 8:
            print(f"⚠ Header row guessed at row {row_idx} ({len(non_empty)} non-empty columns)")
            print(f"  Sample columns: {non_empty[:10]}")
            return row_idx
        
    print(f"  Defaulting to row 2")
    return 1


def load_data_with_auto_header(file_path, required_columns=None):
    """
    Convenience function to load Excel data with automatic header detection.
    """
    header_row = find_header_row(file_path, required_columns)
    df = pd.read_excel(file_path, header=header_row)
    
    print(f"✓ Data loaded successfully")
    print(f"  Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"  Columns: {list(df.columns[:5])}...")
    
    return df, header_row