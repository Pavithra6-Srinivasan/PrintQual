# spec_validator.py

import pandas as pd

class SpecValidator:
    def __init__(self, spec_file_path, sheet_name, spec_category,
             product=None, sub_assembly=None):

        self.spec_file_path = spec_file_path
        self.sheet_name = sheet_name
        self.spec_category = spec_category

        # product here is already the VARIANT
        self.product = str(product).strip().lower() if product else None
        self.sub_assembly = str(sub_assembly).strip().lower() if sub_assembly else None

        self.spec_df = self.load_specs()
        self.has_tray = self._check_has_tray()

    def _check_has_tray(self):
        """True if the spec sheet uses Input Tray as a differentiating column."""
        if "Input Tray" not in self.spec_df.columns:
            return False
        return (
            self.spec_df["Input Tray"]
            .dropna()
            .astype(str)
            .str.strip()
            .ne("")
            .any()
        )

    # LOAD SPEC SHEET
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

    # EXTRACT CONTEXT FROM PIVOT ROW
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
                val = str(pivot_row[col]).strip()
                if col == "Test Condition":
                    # Raw data has specific climatic values (e.g. "15C20RH")
                    # Spec file uses "Climatic" for all non-ambient — normalize accordingly
                    val = "Ambient" if val.lower() == "ambient" else "Climatic"
                context[col] = val.lower()

        return context
    
    # NORMALISATION MAP — raw data abbreviations → spec file full forms
    TRAY_ALIASES = {
        "mpt":           "multipurpose",
        "multipurpose":  "multipurpose",
        "mp tray":       "multipurpose",
        "mp":            "multipurpose",
        "main":          "main",
        "adf":           "adf",
    }

    def _normalise_value(self, value):
        """
        Normalise a pivot value before matching against spec.
        Expands known tray abbreviations and lower-cases everything.
        """
        v = str(value).strip().lower()
        return self.TRAY_ALIASES.get(v, v)

    # MATCH SINGLE CELL
    def cell_matches(self, spec_cell, pivot_value):
        """
        Returns True if:
        - spec cell is blank
        - pivot_value (after normalisation) exists inside comma-separated spec cell
        """

        if pd.isna(spec_cell):
            return True

        spec_cell = str(spec_cell).strip().lower()

        if spec_cell == "":
            return True

        # Normalise the pivot value so abbreviations match full forms
        normalised_pivot = self._normalise_value(pivot_value)

        # Split comma-separated spec options and normalise each
        options = [self._normalise_value(x) for x in spec_cell.split(",")]

        # Exact match
        if normalised_pivot in options:
            return True

        # Plural-tolerant match — try stripping a trailing 's' from the pivot value
        # so "cards" matches "card", "envelopes" matches "envelope", etc.
        singular_pivot = normalised_pivot.rstrip("s") if normalised_pivot.endswith("s") else None
        if singular_pivot and singular_pivot in options:
            return True

        # Word-level match — e.g. variant "hi" matches product entry "marconi hi"
        for opt in options:
            if normalised_pivot in opt.split():
                return True
            if singular_pivot and singular_pivot in opt.split():
                return True

        return False

    # COLUMN-BY-COLUMN ELIMINATION
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

            def is_blank(v):
                return pd.isna(v) or str(v).strip() == ""

            def is_explicit_match(v):
                return not is_blank(v) and self.cell_matches(v, pivot_value)

            explicit_rows = df[df[col].apply(is_explicit_match)]
            wildcard_rows = df[df[col].apply(is_blank)]

            if not explicit_rows.empty:
                df = explicit_rows.reset_index(drop=True)
            elif not wildcard_rows.empty:
                df = wildcard_rows.reset_index(drop=True)

            if len(df) == 1:
                break

        if df.empty:
            return None

        if len(df) > 1:
            df = self._prefer_general_row(df, priority_order)

        return df.iloc[0]

    # COLUMN-BY-COLUMN ELIMINATION (continued)
    def _prefer_general_row(self, df, priority_order):
        """When multiple rows remain after context exhaustion, prefer the most
        specific spec row (most non-blank constraints) — i.e. the row that
        most precisely describes a test condition.  If two rows tie on
        specificity, fall back to the minimum spec value (most conservative)."""
        def specificity(row):
            return sum(
                1 for col in priority_order
                if col in df.columns
                and not (pd.isna(row.get(col)) or str(row.get(col)).strip() == "")
            )
        df = df.copy()
        df["_spec_score"] = df.apply(specificity, axis=1)
        max_score = df["_spec_score"].max()
        return df[df["_spec_score"] == max_score].drop("_spec_score", axis=1).reset_index(drop=True)

    # FINAL EVALUATION
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