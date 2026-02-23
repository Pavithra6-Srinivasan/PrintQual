from core.excel_formatter import ExcelFormatter
import pandas as pd

class StorageService:

    def save_excel(self, output_path, all_pivots):
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            formatter = ExcelFormatter()

            for category_name, pivot_data in all_pivots.items():
                config = pivot_data['config']

                sheet_media = f'{category_name} By Media'
                sheet_unit = f'{category_name} By Unit'

                pivot_data['media'].to_excel(writer, sheet_name=sheet_media, index=False)
                pivot_data['unit'].to_excel(writer, sheet_name=sheet_unit, index=False)

                formatter.apply_standard_formatting(
                    worksheet=writer.sheets[sheet_media],
                    dataframe=pivot_data['media'],
                    grand_total_identifier='Grand Total',
                    bold_columns=[config.total_column_name],
                    highlight_threshold=0.5,
                    total_column_name=config.total_column_name
                )

                formatter.apply_standard_formatting(
                    worksheet=writer.sheets[sheet_unit],
                    dataframe=pivot_data['unit'],
                    grand_total_identifier='Grand Total',
                    bold_columns=[config.total_column_name],
                    highlight_threshold=0.5,
                    total_column_name=config.total_column_name
                )
