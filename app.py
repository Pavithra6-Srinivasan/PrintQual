"""
app.py - Life Test Data Analysis Dashboard

Main Streamlit application for processing printer quality test data.
Provides a web interface for uploading raw Excel data files and generating
formatted pivot tables for Paperpath and ADF test categories.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import tempfile
from datetime import datetime
from io import BytesIO

# Import modules from core for pivot generation and formatting
from core.pivot_generator import UnifiedPivotGenerator
from core.Spec_Category_config import Paperpath_TEST_CATEGORIES, ADF_TEST_CATEGORIES, Paperpath_TEST_CATEGORIES
from core.excel_formatter import ExcelFormatter

# PAGE CONFIGURATION
st.set_page_config(
    page_title="Life Test Data Analysis",
    layout="wide"
)

# TITLE AND DESCRIPTION
st.title("Life Test Data Analysis")
st.markdown("Upload your raw test data files to generate pivot tables automatically.")

# SIDEBAR FOR SETTINGS
with st.sidebar:
    st.header("Settings")
    test_type = st.selectbox(
        "Select Test Type",
        ["Paperpath", "ADF"],
        help="Choose the type of test data you're uploading"
    )
    
    st.markdown("---")
    st.markdown("### Instructions")
    st.markdown("""
    1. Select test type (Paperpath or ADF)
    2. Upload your raw data Excel file
    3. Click 'Generate' to create pivot tables
    4. Download the results
    """)

uploaded_file = st.file_uploader(
    "Choose an Excel file",
    type=['xlsx', 'xlsm', 'xls'],
)

# PROCESSING UPLOADED FILE
if uploaded_file:
    st.markdown("---")
    
    # Generate button
    if st.button("Generate", type="primary"):
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
                test_categories = Paperpath_TEST_CATEGORIES
            
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
            
            output_filename = f"{test_type}_Pivot_Tables_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

            output = BytesIO()

            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                formatter = ExcelFormatter()

                for category_name, pivot_data in all_pivots.items():
                    config = pivot_data['config']

                    sheet_media = f'{category_name} Media'
                    sheet_unit = f'{category_name} Unit'

                    pivot_data['media'].to_excel(writer, sheet_name=sheet_media, index=False)
                    pivot_data['unit'].to_excel(writer, sheet_name=sheet_unit, index=False)

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

            # Move pointer to start
            output.seek(0)

            st.download_button(
                label="Download Pivot Tables",
                data=output,
                file_name=output_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
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
                    width=True
                )
            
            with tab2:
                st.dataframe(
                    all_pivots[selected_category]['unit'].head(20),
                    width=True
                )
            
            # Clean up temp file
            Path(tmp_path).unlink()
            
        except Exception as e:
            st.error(f"Error generating pivot tables: {str(e)}")
            st.exception(e)

else:
    # Show info when no file is uploaded
    st.info("Upload a file to get started")