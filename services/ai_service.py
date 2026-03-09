"""
ai_service.py

Handles AI trend analysis using database historical data.
Updated to support both context-based and general queries.
"""

import urllib.parse
from engine.database_manager import DatabaseManager
from services.llm_service import LLMService


class AIService:

    def __init__(self):

        self.llm = LLMService()

        self.db = DatabaseManager(
            host="15.46.29.115",
            database="quality_sandbox",
            username="pavithra_030226",
            password=urllib.parse.quote_plus("pavithra@030226"),
            db_type="mysql"
        )

    def analyze_trends(self, question):
        """
        Analyze trends using historical database data.
        """

        trend_data = self.db.get_quarter_trends()

        if not trend_data:
            return "No historical quarter data available yet."

        trend_text = "\n".join([
            f"{row['category']} / {row['media_type']} : {row['trend_description']}"
            for row in trend_data
        ])

        system_prompt = """
You are a printer reliability engineer.

Your task is to identify concerning failure trends across quarters.

Focus on:
- Large increases in fail rate
- Consistent deterioration
- Media types becoming unreliable

Ignore stable or improving results.

Answer briefly and professionally.
"""

        prompt = f"""
User Question:
{question}

Detected Failure Trends:
{trend_text}
"""

        return self.llm.ask(system_prompt, prompt)
    
    def analyze_with_context(self, question, context):
        """
        Answer question using the current pivot summary as context.
        
        Args:
            question: User's question
            context: The summary text from generated pivots
        
        Returns:
            AI response string
        """
        system_prompt = """
You are a printer quality analysis expert.

Your task is to analyze test results and provide actionable insights.

Focus on:
- Specific failure patterns in the data
- Root cause analysis
- Recommendations for improvement

Answer briefly and professionally based on the provided data.
"""

        prompt = f"""
Current Test Report Summary:
{context}

User Question:
{question}
"""

        return self.llm.ask(system_prompt, prompt)
    
    def answer_question(self, question):
        """
        Answer general question without pivot context.
        Uses historical database trends if available.
        
        Args:
            question: User's question
        
        Returns:
            AI response string
        """
        # Try to get historical trends from database
        try:
            trend_data = self.db.get_quarter_trends()
            
            if trend_data:
                # Has historical data - use it
                trend_text = "\n".join([
                    f"{row['category']} / {row['media_type']} : {row['trend_description']}"
                    for row in trend_data
                ])
                
                system_prompt = """
You are a printer reliability engineer with access to historical trend data.

Provide helpful insights based on historical trends.

If the question is about current/recent test results, remind the user to generate a pivot report first.

Answer briefly and professionally.
"""

                prompt = f"""
Historical Trends:
{trend_text}

User Question:
{question}

Note: If user asks about current test results, tell them to generate a pivot report first.
"""
                
                return self.llm.ask(system_prompt, prompt)
            
        except Exception as e:
            # Database query failed - continue to general mode
            pass
        
        # No historical data - provide general guidance
        system_prompt = """
You are a printer quality testing expert.

Provide general guidance about printer quality testing, defect types, and best practices.

If the user asks about specific test results, tell them to generate a pivot report first.

Answer briefly and professionally.
"""

        prompt = f"""
User Question:
{question}

Note: No test data currently available. Provide general guidance or suggest generating a pivot report for data-specific analysis.
"""

        return self.llm.ask(system_prompt, prompt)