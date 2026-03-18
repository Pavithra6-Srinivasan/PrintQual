from engine.summary_engine import PivotSummaryEngine

class SummaryService:

    def __init__(self, pivots):
        self.engine = PivotSummaryEngine(pivots)

    def generate(self):
        summary_data = self.engine.generate_summary()
        return summary_data, ""