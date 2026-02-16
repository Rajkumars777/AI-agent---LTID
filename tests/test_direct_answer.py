
import sys
import os
import dspy
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'backend', '.env'))

from execution.nlu import get_commands, extract_commands, Command
# Mock the predictor in nlu to avoid real API calls for the classification test if possible,
# but we want to test the LLM's classification.
# So we need real configuring.

from execution.openrouter_adapter import OpenRouterAdapter
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    # Try reading from backend/.env manually if load_dotenv failed
    try:
        with open(os.path.join(os.path.dirname(__file__), '..', 'backend', '.env'), 'r') as f:
            for line in f:
                if "OPENROUTER_API_KEY" in line:
                    api_key = line.split("=")[1].strip().strip('"')
                    os.environ["OPENROUTER_API_KEY"] = api_key
                    break
    except: pass

if not api_key:
    print("SKIPPING: API Key not found.")
    sys.exit(0)

# Configure DSPy
lm = OpenRouterAdapter(model="google/gemini-2.0-flash-001", api_key=api_key)
dspy.settings.configure(lm=lm)

def test_answer_classification():
    print("\n--- Testing Direct Answer Classification ---\n")
    
    # Test 1: General Knowledge
    query1 = "history of india"
    print(f"Query: '{query1}'")
    cmds1 = extract_commands(query1)
    print(f"Result: {cmds1}")
    
    assert len(cmds1) > 0
    cmd1 = cmds1[0]
    # Expect ANSWER
    if cmd1.action == "ANSWER":
        print("✅ Correctly classified as ANSWER")
    else:
        print(f"❌ Failed: Got {cmd1.action}")
        sys.exit(1)

    # Test 1b: Explicit Search (Should also be ANSWER now)
    query_search = "search for AI news"
    print(f"\nQuery: '{query_search}'")
    cmds_s = extract_commands(query_search)
    print(f"Result: {cmds_s}")
    if cmds_s[0].action == "ANSWER":
        print("✅ Explicit search re-routed to ANSWER")
    else:
        print(f"❌ Failed: Got {cmds_s[0].action}")

    # Test 2: Explicit Content Generation
    query2 = "write a poem about AI"
    print(f"\nQuery: '{query2}'")
    cmds2 = extract_commands(query2)
    print(f"Result: {cmds2}")
    
    if len(cmds2) > 0:
        cmd2 = cmds2[0]
        if cmd2.action == "ANSWER":
             print("✅ Correctly classified as ANSWER")
        elif cmd2.action == "TYPE":
             print("warning: Classified as TYPE (context dependent)")
        else:
             print(f"❌ Failed: Got {cmd2.action}")
             sys.exit(1)
    else:
        print("❌ Failed: No commands returned for 'write a poem'")
        # Don't exit yet, let's see the next test

    from execution.nlu import generate_text_content
    print("\n--- Testing Answer Generation ---\n")
    answer = generate_text_content("What is the capital of France?")
    print(f"Answer: {answer}")
    assert "Paris" in answer
    print("✅ Answer content verified")

if __name__ == "__main__":
    test_answer_classification()
