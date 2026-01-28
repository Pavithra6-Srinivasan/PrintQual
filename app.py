"""
app.py - Main Streamlit Application

Simple interface for uploading raw data files and generating pivot tables.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import tempfile
from datetime import datetime

from core.pivot_generator import UnifiedPivotGenerator
from core.test_category_config import CUSLT_TEST_CATEGORIES, ADF_TEST_CATEGORIES
from core.excel_formatter import ExcelFormatter

# Page configuration
st.set_page_config(
    page_title="Printer Quality Dashboard",
    page_icon="🖨️",
    layout="wide"
)

# Title
st.title("Printer Quality Pivot Table Generator")
st.markdown("Upload your raw test data files to generate pivot tables automatically.")

# Sidebar for settings
with st.sidebar:
    st.header("Settings")
    test_type = st.selectbox(
        "Select Test Type",
        ["CUSLT", "ADF"],
        help="Choose the type of test data you're uploading"
    )
    
    st.markdown("---")
    st.markdown("### Instructions")
    st.markdown("""
    1. Select test type (CUSLT or ADF)
    2. Upload your raw data Excel file
    3. Click 'Generate Pivots'
    4. Download the results
    """)

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.header("Upload Data File")
    uploaded_file = st.file_uploader(
        "Choose an Excel file",
        type=['xlsx', 'xlsm', 'xls'],
        help="Upload your raw test data in Excel format"
    )

with col2:
    st.header("Quick Stats")
    if uploaded_file:
        st.metric("File Name", uploaded_file.name)
        st.metric("File Size", f"{uploaded_file.size / 1024:.1f} KB")
        st.metric("Test Type", test_type)

# Processing section
if uploaded_file:
    st.markdown("---")
    
    # Generate button
    if st.button("Generate Pivot Tables", type="primary", use_container_width=True):
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            
            # Progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Select test categories
            if test_type == "ADF":
                test_categories = ADF_TEST_CATEGORIES
            else:
                test_categories = CUSLT_TEST_CATEGORIES
            
            all_pivots = {}
            total_categories = len(test_categories)
            
            # Generate pivots for each category
            for idx, config in enumerate(test_categories):
                status_text.text(f"Processing {config.name}...")
                progress_bar.progress((idx + 1) / total_categories)
                
                generator = UnifiedPivotGenerator(tmp_path, config)
                pivot_media = generator.create_pivot_by_media_name()
                pivot_unit = generator.create_pivot_by_unit()
                
                all_pivots[config.name] = {
                    'media': pivot_media,
                    'unit': pivot_unit,
                    'config': config
                }
            
            status_text.text("Formatting Excel file...")
            
            # Create output file
            output_filename = f"{test_type}_Pivot_Tables_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            output_path = Path("data/outputs") / output_filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to Excel
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                formatter = ExcelFormatter()
                
                for category_name, pivot_data in all_pivots.items():
                    config = pivot_data['config']
                    
                    # Sheet names
                    sheet_media = f'{category_name} By Media'
                    sheet_unit = f'{category_name} By Unit'
                    
                    # Write to Excel
                    pivot_data['media'].to_excel(writer, sheet_name=sheet_media, index=False)
                    pivot_data['unit'].to_excel(writer, sheet_name=sheet_unit, index=False)
                    
                    # Apply formatting
                    formatter.apply_standard_formatting(
                        worksheet=writer.sheets[sheet_media],
                        dataframe=pivot_data['media'],
                        grand_total_identifier='Grand Total',
                        bold_columns=[config.total_column_name]
                    )
                    
                    formatter.apply_standard_formatting(
                        worksheet=writer.sheets[sheet_unit],
                        dataframe=pivot_data['unit'],
                        grand_total_identifier='Grand Total',
                        bold_columns=[config.total_column_name]
                    )
            
            progress_bar.progress(1.0)
            status_text.text("Complete!")
            
            # Success message
            st.success("🎉 Pivot tables generated successfully!")
            
            # Download button
            with open(output_path, 'rb') as f:
                st.download_button(
                    label="Download Pivot Tables",
                    data=f,
                    file_name=output_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True
                )
            
            # Show preview
            st.markdown("---")
            st.header("Preview")
            
            # Category selector
            selected_category = st.selectbox(
                "Select Category to Preview",
                list(all_pivots.keys())
            )
            
            # Preview tabs
            tab1, tab2 = st.tabs(["By Media Name", "By Unit"])
            
            with tab1:
                st.dataframe(
                    all_pivots[selected_category]['media'].head(20),
                    use_container_width=True
                )
            
            with tab2:
                st.dataframe(
                    all_pivots[selected_category]['unit'].head(20),
                    use_container_width=True
                )
            
            # Clean up temp file
            Path(tmp_path).unlink()
            
        except Exception as e:
            st.error(f"Error generating pivot tables: {str(e)}")
            st.exception(e)

else:
    # Show info when no file is uploaded
    st.info("Upload a file to get started")
    
    # Example
    with st.expander("What happens when you upload?"):
        st.markdown("""
        1. **File Validation**: We check if your file is a valid Excel file
        2. **Header Detection**: Automatically detect where your data starts
        3. **Pivot Generation**: Create pivot tables for all test categories
        4. **Formatting**: Apply professional formatting to the results
        5. **Download**: Get your formatted pivot tables instantly
        
        **Supported Test Types:**
        - **CUSLT**: Intervention, Soft Error, Skew, Other Defects, PQ
        - **ADF**: ADF Intervention, Soft Error, Image Quality, Other Issues, Skew
        """)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
    Printer Quality Dashboard v1.0 | Built with Streamlit
    </div>
    """,
    unsafe_allow_html=True
)