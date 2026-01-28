"""
Reusable Excel formatting configurations for analysis file
"""

from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

class ExcelFormatter:
    """
    Handles all aesthetic formatting
    """
    
    def __init__(self):
        # Define standard colors
        self.blue_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        self.orange_fill = PatternFill(start_color="F4B084", end_color="F4B084", fill_type="solid")
        self.white_bold_font = Font(bold=True, color="FFFFFF")
        self.bold_font = Font(bold=True)
    
    def apply_standard_formatting(self, worksheet, dataframe, grand_total_identifier='Grand Total', 
                                   bold_columns=None, header_row=1, data_start_row=2, highlight_threshold=0.0):
        """
        Args:
            worksheet: openpyxl worksheet object
            dataframe: pandas DataFrame that was written to the worksheet
            grand_total_identifier: String to identify Grand Total rows (default: 'Grand Total')
            bold_columns: List of column names to make bold (default: None)
            header_row: Row number of headers (default: 1)
            data_start_row: First row of data (default: 2)
        """
        
        self.format_header_row(worksheet, dataframe, header_row)
        
        self.enable_filters(worksheet)
        
        self.format_data_rows(worksheet, dataframe, grand_total_identifier, 
                              bold_columns, data_start_row)
        
        self.format_Result_column(worksheet, dataframe)

        self.highlight_high_error_cells(worksheet, dataframe, highlight_threshold, 
                                        grand_total_identifier, data_start_row)
        
        self.auto_adjust_column_widths(worksheet, dataframe)

    
    def format_header_row(self, worksheet, dataframe, header_row):
        """
        Format the header row with blue background and white bold text.
        """
        
        for col_num in range(1, len(dataframe.columns) + 1):
            cell = worksheet.cell(row=header_row, column=col_num)
            cell.fill = self.blue_fill
            cell.font = self.white_bold_font
    
    def enable_filters(self, worksheet):
        """
        Enable Excel autofilter on all columns.
        """
        worksheet.auto_filter.ref = worksheet.dimensions
    
    def format_data_rows(self, worksheet, dataframe, grand_total_identifier, 
                         bold_columns, data_start_row):
        """
        Bold column headings and format data rows including Grand Total rows
        """

        # Find indices of columns to bold
        bold_col_indices = []
        if bold_columns:
            for col_name in bold_columns:
                if col_name in dataframe.columns:
                    # +1 because Excel columns are 1-indexed
                    bold_col_indices.append(list(dataframe.columns).index(col_name) + 1)
        
        # Find which column contains Media Name or Unit (the one with Grand Total)
        grand_total_col_idx = None
        for col_name in ['Media Name', 'Unit']:
            if col_name in dataframe.columns:
                grand_total_col_idx = list(dataframe.columns).index(col_name) + 1
                break
        
        # Loop through all data rows
        num_rows = len(dataframe)
        for row_num in range(data_start_row, num_rows + data_start_row):
            # Check if this is a Grand Total row by checking the correct column
            is_grand_total = False
            if grand_total_col_idx:
                cell_value = worksheet.cell(row=row_num, column=grand_total_col_idx).value
                is_grand_total = (cell_value == grand_total_identifier)
            
            if is_grand_total:
                # Format entire Grand Total row with orange background and white bold text
                for col_num in range(1, len(dataframe.columns) + 1):
                    cell = worksheet.cell(row=row_num, column=col_num)
                    cell.fill = self.orange_fill
                    cell.font = self.white_bold_font
            else:
                # Bold specific columns for regular data rows
                for col_idx in bold_col_indices:
                    cell = worksheet.cell(row=row_num, column=col_idx)
                    cell.font = self.bold_font
    
    def auto_adjust_column_widths(self, worksheet, dataframe, min_width=8, max_width=20):
        """
        Auto-adjust column widths based on content.
        """

        for col_num, column in enumerate(dataframe.columns, start=1):
            column_letter = get_column_letter(col_num)
            
            # Calculate max length in column
            max_length = len(str(column))  # Start with header length
            
            for row_num in range(2, len(dataframe) + 2):
                cell_value = worksheet.cell(row=row_num, column=col_num).value
                if cell_value:
                    max_length = max(max_length, len(str(cell_value)))
            
            # Set width with constraints
            adjusted_width = min(max(max_length + 2, min_width), max_width)
            worksheet.column_dimensions[column_letter].width = adjusted_width

    def format_Result_column(self, worksheet, dataframe):
        """
        Color Pass/Fail column cells: green for Pass, red for Fail.
        """
        # Define colors
        green_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
        red_fill = PatternFill(start_color="FF9999", end_color="FF9999", fill_type="solid")

        # Find Pass/Fail column index
        pass_fail_col_idx = None
        for col_num, col_name in enumerate(dataframe.columns, start=1):
            if col_name == 'Result':
                pass_fail_col_idx = col_num
                break

        if pass_fail_col_idx is None:
            return

        # Color each cell based on Pass/Fail value
        for row_num in range(2, len(dataframe) + 2):
            cell = worksheet.cell(row=row_num, column=pass_fail_col_idx)
            if cell.value == 'Pass':
                cell.fill = green_fill
            elif cell.value == 'Fail':
                cell.fill = red_fill

    def highlight_high_error_cells(self, worksheet, dataframe, threshold, 
                                    grand_total_identifier, data_start_row):
        """
        Highlight individual error cells (per-K columns) that exceed the threshold.
        This helps identify which specific error types are contributing most to failures.
        """
        # Define highlight color (light red/pink for warnings)
        highlight_fill = PatternFill(start_color="FF9999", end_color="FF9999", fill_type="solid")
        
        # Find which column contains Media Name or Unit (to check for Grand Total)
        grand_total_col_idx = None
        for col_name in ['Media Name', 'Unit']:
            if col_name in dataframe.columns:
                grand_total_col_idx = list(dataframe.columns).index(col_name) + 1
                break
        
        # Find all per-K columns (but exclude the total sum column)
        per_k_columns = []
        for col_num, col_name in enumerate(dataframe.columns, start=1):
            # Check if it's a per-K column but NOT the total sum column
            if '/K' in str(col_name) and not any(keyword in str(col_name) for keyword in 
                ['Sum of Total', 'Total']):
                per_k_columns.append(col_num)
        
        # Highlight cells that exceed threshold
        num_rows = len(dataframe)
        for row_num in range(data_start_row, num_rows + data_start_row):
            # Skip Grand Total rows
            is_grand_total = False
            if grand_total_col_idx:
                cell_value = worksheet.cell(row=row_num, column=grand_total_col_idx).value
                is_grand_total = (cell_value == grand_total_identifier)
            
            if not is_grand_total:
                # Check each per-K column
                for col_num in per_k_columns:
                    cell = worksheet.cell(row=row_num, column=col_num)
                    try:
                        value = float(cell.value) if cell.value is not None else 0.0
                        if value > threshold:
                            cell.fill = highlight_fill
                    except (ValueError, TypeError):
                        # Skip if cell value is not a number
                        pass