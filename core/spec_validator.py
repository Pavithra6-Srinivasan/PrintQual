# spec_validator.py

import pandas as pd

class SpecValidator:
    def __init__(self, spec_file_path, sheet_name, spec_category,
             product=None, sub_assembly=None):

        self.spec_file_path = spec_file_path
        self.sheet_name = sheet_name
        self.spec_category = spec_category

        # product here is already the VARIANT (Hi / Base / SF)
        self.product = str(product).strip().lower() if product else None
        self.sub_assembly = str(sub_assembly).strip().lower() if sub_assembly else None

        self.spec_df = self.load_specs()

    # ---------------------------------------------------------
    # LOAD SPEC SHEET
    # ---------------------------------------------------------
    def load_specs(self):
        df = pd.read_excel(self.spec_file_path, sheet_name=self.sheet_name)

        if "Spec Category" not in df.columns:
            raise ValueError("Spec file missing 'Spec Category' column")

        df = df[
            df["Spec Category"].astype(str).str.strip().str.lower()
            == self.spec_category.lower()
        ]

        if df.empty:
            raise ValueError(
                f"No specs found for category '{self.spec_category}' "
                f"in sheet '{self.sheet_name}'"
            )

        return df.reset_index(drop=True)

    # ---------------------------------------------------------
    # EXTRACT CONTEXT FROM PIVOT ROW
    # ---------------------------------------------------------
    def extract_test_context(self, pivot_row):

        context = {}

        # Product variant (Hi / Base / SF)
        if self.product:
            context["Product"] = self.product

        # Sub Assembly
        if self.sub_assembly:
            context["Sub Assembly"] = self.sub_assembly

        mapping = [
            "Test Condition",
            "Input Tray",
            "Print Mode",
            "Media Type",
            "Media Cat",
            "Print Quality"
        ]

        for col in mapping:
            if col in pivot_row and pd.notna(pivot_row[col]):
                context[col] = str(pivot_row[col]).strip().lower()

        return context
    
    # ---------------------------------------------------------
    # MATCH SINGLE CELL
    # ---------------------------------------------------------
    def cell_matches(self, spec_cell, pivot_value):
        """
        Returns True if:
        - spec cell is blank (wildcard)
        - pivot_value exists inside comma-separated spec cell
        """

        if pd.isna(spec_cell):
            return True  # blank spec cell = wildcard

        spec_cell = str(spec_cell).strip().lower()

        if spec_cell == "":
            return True

        # Split comma-separated values
        options = [x.strip() for x in spec_cell.split(",")]

        return pivot_value in options

    # ---------------------------------------------------------
    # COLUMN-BY-COLUMN ELIMINATION
    # ---------------------------------------------------------
    def find_best_spec_row(self, context):

        df = self.spec_df.copy()

        priority_order = [
            "Product",
            "Sub Assembly",
            "Test Condition",
            "Input Tray",
            "Print Mode",
            "Media Type",
            "Media Cat",
            "Print Quality"
        ]

        for col in priority_order:

            if col not in df.columns:
                continue

            if col not in context:
                continue

            pivot_value = context[col]

            matched_rows = df[
                df[col].apply(lambda x: self.cell_matches(x, pivot_value))
            ]

            # Only reduce if we found matches
            if not matched_rows.empty:
                df = matched_rows.reset_index(drop=True)

            # If only one row remains → stop early
            if len(df) == 1:
                break

        if df.empty:
            return None

        return df.iloc[0]

    # ---------------------------------------------------------
    # FINAL EVALUATION
    # ---------------------------------------------------------
    def evaluate(self, pivot_row, total_per_k_col):

        context = self.extract_test_context(pivot_row)

        spec_row = self.find_best_spec_row(context)

        actual_per_k = pivot_row.get(total_per_k_col)

        if spec_row is None:
            return None, actual_per_k, "SPEC NOT FOUND"

        spec_limit = spec_row.get("Spec (per K)")

        if pd.isna(actual_per_k):
            return spec_limit, None, "NO DATA"

        result = "PASS" if actual_per_k <= spec_limit else "FAIL"

        return spec_limit, round(actual_per_k, 3), result