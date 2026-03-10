"""
test_ai_debug.py - Debug AI service step by step
"""

import urllib.parse
from engine.database_manager import DatabaseManager
from services.llm_service import LLMService

print("\n" + "="*60)
print("AI SERVICE DEBUG TEST")
print("="*60)

# Step 1: Test Database Connection
print("\n[Step 1] Testing database connection...")
try:
    db = DatabaseManager(
        host="15.46.29.115",
        database="quality_sandbox",
        username="pavithra_030226",
        password=urllib.parse.quote_plus("pavithra@030226"),
        db_type="mysql"
    )
    print("✓ Database connected")
except Exception as e:
    print(f"✗ Database failed: {e}")
    exit(1)

# Step 2: Test get_quarter_trends
print("\n[Step 2] Testing get_quarter_trends()...")
try:
    trends = db.get_quarter_trends()
    print(f"✓ Got {len(trends)} trends")
    if trends:
        print("\nFirst trend:")
        print(f"  Category: {trends[0]['category']}")
        print(f"  Media: {trends[0]['media_type']}")
        print(f"  Description: {trends[0]['trend_description']}")
    else:
        print("⚠ No trends in database (need at least 2 quarters)")
except Exception as e:
    print(f"✗ get_quarter_trends failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Step 3: Test LLM Service
print("\n[Step 3] Testing LLM service...")
try:
    llm = LLMService()
    print("✓ LLM service created")
except Exception as e:
    print(f"✗ LLM service creation failed: {e}")
    exit(1)

# Step 4: Test simple LLM call
print("\n[Step 4] Testing simple LLM call...")
try:
    print("Sending simple question to Ollama...")
    response = llm.ask(
        system_prompt="You are a helpful assistant.",
        user_message="Say 'hello' in one word.",
        timeout=30
    )
    print(f"✓ LLM responded: {response[:100]}")
except Exception as e:
    print(f"✗ LLM call failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Step 5: Test full AI service
print("\n[Step 5] Testing full AI service...")
try:
    from services.ai_service import AIService
    ai = AIService()
    print("✓ AI service created")
except Exception as e:
    print(f"✗ AI service creation failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Step 6: Test answer_question
print("\n[Step 6] Testing answer_question()...")
try:
    print("Asking AI a question...")
    response = ai.answer_question("What is a defect?")
    print(f"✓ AI responded ({len(response)} chars)")
    print(f"\nResponse preview:")
    print(response[:200] + "...")
except Exception as e:
    print(f"✗ answer_question failed: {e}")
    import traceback
    traceback.print_exc()

# Step 7: Test analyze_with_context
print("\n[Step 7] Testing analyze_with_context()...")
try:
    context = "Intervention: Plain - 2.3/K PASS\nSoft Error: Plain - 0.8/K PASS"
    print("Asking AI with context...")
    response = ai.analyze_with_context("What failed?", context)
    print(f"✓ AI responded ({len(response)} chars)")
    print(f"\nResponse preview:")
    print(response[:200] + "...")
except Exception as e:
    print(f"✗ analyze_with_context failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("DEBUG TEST COMPLETE")
print("="*60)

db.close()