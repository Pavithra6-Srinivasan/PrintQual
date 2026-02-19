# spec_matcher.py

import pandas as pd

class SpecValidator:
    def __init__(self, spec_file_path, sheet_name, spec_category, product=None, sub_assembly=None):
        self.spec_file_path = spec_file_path
        self.sheet_name = sheet_name
        self.spec_category = spec_category
        self.product = product
        self.sub_assembly = sub_assembly
        
        self.spec_df = self.load_specs()

    def load_specs(self):
        """Load the correct printer spec sheet"""
        df = pd.read_excel(self.spec_file_path, sheet_name=self.sheet_name)

        if "Spec Category" not in df.columns:
            raise ValueError("Spec file missing 'Spec Category' column")

        df = df[df["Spec Category"].astype(str).str.lower()
                == self.spec_category.lower()]

        return df

    def extract_test_context(self, pivot_row):
        """Extract condition metadata from pivot row"""

        context = {}

        # Inject auto-detected values
        if self.product:
            context["Product"] = self.product.lower()

        if self.sub_assembly:
            context["Sub Assembly"] = self.sub_assembly.lower()

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

    def find_best_spec_row(self, context):
        df = self.spec_df.copy()

        for col, value in context.items():
            if col in df.columns:
                filtered = df[
                    df[col].astype(str).str.lower() == value
                ]
                if not filtered.empty:
                    df = filtered

        if df.empty:
            return None

        # Prefer rows with more filled fields (more specific)
        df["specificity_score"] = df.notna().sum(axis=1)
        df = df.sort_values("specificity_score", ascending=False)

        return df.iloc[0]

    def evaluate(self, pivot_row, total_per_k_col):
        """
        Return Spec Limit, Actual Rate, Pass/Fail
        """
        context = self.extract_test_context(pivot_row)
        spec_row = self.find_best_spec_row(context)

        if spec_row is None:
            return None, pivot_row[total_per_k_col], "SPEC NOT FOUND"

        spec_limit = spec_row["Spec (per K)"]
        actual_per_k = pivot_row[total_per_k_col]

        if pd.isna(actual_per_k):
            return spec_limit, None, "NO DATA"

        result = "PASS" if actual_per_k <= spec_limit else "FAIL"
        return spec_limit, round(actual_per_k, 3), result
