from engine.summary_engine import PivotSummaryEngine

class SummaryService:

    def __init__(self, pivots):
        self.engine = PivotSummaryEngine(pivots)

    def generate(self):
        summary_data = self.engine.generate_summary()
        summary_text = self.engine.format_summary_text(summary_data)
        return summary_data, summary_text
