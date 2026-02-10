import os
from dotenv import load_dotenv

# Force load .env
load_dotenv()

print(f"API Key present: {bool(os.getenv('GOOGLE_API_KEY') or os.getenv('OPENAI_API_KEY'))}")

import dspy
from execution.nlu import extract_commands

# Re-apply the configuration logic from agent.py to match exactly
google_key = os.getenv("GOOGLE_API_KEY")
openai_key = os.getenv("OPENAI_API_KEY")

candidates = [
    "gemini/gemini-1.5-flash",
    "gemini/gemini-pro",
    "gemini/gemini-1.5-pro",
    "gemini/gemini-1.0-pro"
]

lm = None
if google_key:
    # LiteLLM often requires GEMINI_API_KEY
    os.environ["GEMINI_API_KEY"] = google_key
    
    candidate = "gemini/gemini-2.0-flash"
    print(f"Trying model: {candidate}...")
    try:
        # LiteLLM often requires GEMINI_API_KEY
        os.environ["GEMINI_API_KEY"] = google_key
        lm = dspy.LM(model=candidate, api_key=google_key)
        dspy.settings.configure(lm=lm)
        # Force a simple prediction to check connection
        pred = dspy.Predict("q->a")(q="test")
        print(f"Connection Success! Response: {pred.a}")
    except Exception as e:
        print(f"FAILED: {e}")
        lm = None

    if lm:
        print(f"Final Configuration: {lm.model}")
    else:
        print("All Google models failed.")

# Test Command
test_input = "open the notepad and type hi and play the Attack On Titan S04 E29 (Tamil)"
print(f"\nTesting Input: '{test_input}'")

try:
    cmds = extract_commands(test_input)
    print(f"\nExtracted {len(cmds)} commands:")
    for cmd in cmds:
        print(f" - {cmd}")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"\nFatal Error: {e}")
