"""
auto_header_detector.py

Utility to automatically detect the header row in Excel files.
Simple rule: If "Test Condition" is found, that's the header row.
"""

import pandas as pd


def find_header_row(file_path, required_columns=None, max_search_rows=20):
    """
    Automatically detect which row contains the column headers.
    Rule: If "Test Condition" column is found, that row is the header.
    
    Args:
        file_path: Path to the Excel file
        required_columns: Not used - kept for compatibility
        max_search_rows: Maximum number of rows to search for headers (default: 20)
    
    Returns:
        int: The row number (0-indexed) where headers are found
    
    Example:
        header_row = find_header_row("data.xlsx")
        df = pd.read_excel("data.xlsx", header=header_row)
    """
    
    # Read the file without assuming any header position
    try:
        df_test = pd.read_excel(file_path, header=None, nrows=max_search_rows)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return 1
    
    # Look for "Test Condition" column
    for row_idx in range(min(max_search_rows, len(df_test))):
        row_values = df_test.iloc[row_idx].astype(str).str.strip().tolist()
        
        # Check for "Test Condition" (case-insensitive)
        for val in row_values:
            if 'test condition' in val.lower():
                print(f"✓ Header row detected at row {row_idx} (found 'Test Condition')")
                print(f"  Sample columns: {[v for v in row_values[:10] if v not in ['', 'nan', 'None']]}")
                return row_idx
    
    # If "Test Condition" not found, default to row 2
    print(f"⚠ Warning: 'Test Condition' not found in first {max_search_rows} rows")
    print(f"  Defaulting to row 2")
    return 1


def load_data_with_auto_header(file_path, required_columns=None):
    """
    Convenience function to load Excel data with automatic header detection.
    
    Args:
        file_path: Path to the Excel file
        required_columns: Not used - kept for compatibility
    
    Returns:
        tuple: (DataFrame, header_row_index)
    """
    header_row = find_header_row(file_path, required_columns)
    df = pd.read_excel(file_path, header=header_row)
    
    print(f"✓ Data loaded successfully")
    print(f"  Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"  Columns: {list(df.columns[:5])}...")
    
    return df, header_row