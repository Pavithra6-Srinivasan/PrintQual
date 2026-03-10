"""
auto_header_detector.py

Automatically detects the header row in Excel files.
"""

import pandas as pd

def find_header_row(file_path, required_columns=None, max_search_rows=20):
    """
    Automatically detect which row contains the column headers in an Excel file.
    
    Detection Algorithm:
    1. Searches for rows containing at least 2 of the
       3 key columns: 'Test Condition', 'Media Type', 'Unit'
    2. Falls back to row 1 if detection fails
    """
    
    # Attempt to read the Excel file without assuming header position
    try:
        df_test = pd.read_excel(file_path, header=None, nrows=max_search_rows)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return 1
    
    # Define key columns to search for (case-insensitive)
    # These columns should be present in all test data files
    key_columns = ['test condition', 'media type', 'unit']
    
    best_match = {'row': 1, 'score': 0}
    
    # Search each row for key column names    
    for row_idx in range(min(max_search_rows, len(df_test))):
        row_values = df_test.iloc[row_idx].astype(str).str.strip().str.lower().tolist()
        
        # Count how many key columns are present in this row
        score = 0
        for key_col in key_columns:
            if any(key_col in val for val in row_values):
                score += 1
        
        # Update best match if row has a better score
        # Require at least 2 out of 3 key columns for a valid match        
        if score >= 2 and score > best_match['score']:
            best_match = {'row': row_idx, 'score': score}
    
    # If found a row with at least 2 key columns, use it
    if best_match['score'] >= 2:
        row_values = df_test.iloc[best_match['row']].astype(str).str.strip().tolist()
        print(f"✓ Header row detected at row {best_match['row']} (found {best_match['score']}/3 key columns)")
        print(f"  Sample columns: {[v for v in row_values[:10] if v not in ['', 'nan', 'None']]}")
        return best_match['row']
    
    # If all detection methods fail, default to row 1 (second row)
    print(f"  Defaulting to row 2")
    return 1

def load_data_with_auto_header(file_path, required_columns=None):
    """
    Convenience function to load Excel data with automatic header detection.

    Workflow:
        1. Detect the header row using find_header_row()
        2. Load the Excel file with the detected header row
        3. Print summary statistics about the loaded data
        4. Return both the DataFrame and the header row number
    """

    header_row = find_header_row(file_path, required_columns)

    # Load the data using the detected header row
    df = pd.read_excel(file_path, header=header_row)
    
    print(f"✓ Data loaded successfully")
    
    return df, header_row