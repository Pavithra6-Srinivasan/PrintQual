"""
ai_service.py - FIXED

Fixed: Properly formats trend data from database (no 'trend_description' field)
"""

from engine.database_manager import DatabaseManager
from services.llm_service import LLMService

class AIService:

    def __init__(self):
        self.llm = LLMService()
        
        self.db = DatabaseManager(
            host="15.46.29.115",
            user="pavithra_030226",
            password="pavithra@030226",
            database="quality_sandbox"
        )

    def analyze_trends(self, question):
        """Analyze trends using historical database data."""
        
        try:
            trend_data = self.db.get_quarter_trends()

            if not trend_data:
                return "No historical quarter data available yet. Generate a few reports first to see trends."

            # Format trend data properly
            trend_lines = []
            for trend in trend_data:
                category = trend['category']
                media = trend['media_type']
                trend_type = trend['trend_type']
                num_quarters = trend['num_quarters']
                
                earliest = trend['earliest']
                latest = trend['latest']
                
                # Build trend description
                trend_lines.append(f"{category} / {media}: {trend_type} (over {num_quarters} quarters)")
                trend_lines.append(f"  Q{earliest['quarter']} {earliest['year']}: {earliest['overall_result']}")
                
                if earliest.get('failed_units'):
                    trend_lines.append(f"    Units: {earliest['failed_units']}")
                if earliest.get('failed_error_types'):
                    trend_lines.append(f"    Errors: {earliest['failed_error_types']}")
                
                trend_lines.append(f"  Q{latest['quarter']} {latest['year']}: {latest['overall_result']}")
                
                if latest.get('failed_units'):
                    trend_lines.append(f"    Units: {latest['failed_units']}")
                if latest.get('failed_error_types'):
                    trend_lines.append(f"    Errors: {latest['failed_error_types']}")
                
                trend_lines.append("")  # Blank line between trends

            trend_text = "\n".join(trend_lines)

            system_prompt = """You are a printer reliability engineer.

Your task is to identify concerning failure trends across quarters.

Focus on:
- Large increases in fail rate
- Consistent deterioration
- Media types becoming unreliable
- Specific units with recurring problems

Ignore stable or improving results.

Answer briefly and professionally."""

            prompt = f"""User Question:
{question}

Detected Failure Trends:
{trend_text}"""

            return self.llm.ask(system_prompt, prompt)
            
        except Exception as e:
            return f"Error analyzing trends: {str(e)}"
    
    def analyze_with_context(self, question, context):
        """Answer question using the current pivot summary as context."""
        
        try:
            system_prompt = """You are a printer quality analysis expert.

Your task is to analyze test results and provide actionable insights.

Focus on:
- Specific failure patterns in the data
- Root cause analysis

Answer briefly and professionally based on the provided data."""

            prompt = f"""Current Test Report Summary:
{context}

User Question:
{question}"""

            return self.llm.ask(system_prompt, prompt)
            
        except Exception as e:
            return f"Error analyzing report: {str(e)}"
    
    def answer_question(self, question):
        """Answer general question without pivot context."""
        
        try:
            # Try to get historical trends from database
            trend_data = self.db.get_quarter_trends()
            
            if trend_data:
                # Format trend data
                trend_lines = []
                for trend in trend_data[:10]:  # Limit to 10 most important
                    category = trend['category']
                    media = trend['media_type']
                    trend_type = trend['trend_type']
                    latest = trend['latest']
                    
                    trend_lines.append(f"{category} / {media}: {trend_type}")
                    
                    if latest.get('failed_units'):
                        trend_lines.append(f"  Units: {latest['failed_units']}")
                    if latest.get('failed_media_names'):
                        trend_lines.append(f"  Media: {latest['failed_media_names']}")
                    if latest.get('failed_error_types'):
                        trend_lines.append(f"  Errors: {latest['failed_error_types']}")
                
                trend_text = "\n".join(trend_lines)
                
                system_prompt = """You are a printer reliability engineer with access to historical trend data.

Provide helpful insights based on historical trends.

Answer briefly and professionally."""

                prompt = f"""Historical Trends:
{trend_text}

User Question:
{question}"""
                
                return self.llm.ask(system_prompt, prompt)
            
        except Exception as e:
            print(f"Database trend query failed: {e}")
        
        # No historical data available
        try:
            system_prompt = """You are a printer quality testing expert.

Provide general guidance about printer quality testing, defect types, and best practices.

Answer briefly and professionally."""

            prompt = f"""User Question:
{question}

Note: No test data currently available. Provide general guidance or suggest generating a pivot report for data-specific analysis."""

            return self.llm.ask(system_prompt, prompt)
            
        except Exception as e:
            return f"Error: {str(e)}"