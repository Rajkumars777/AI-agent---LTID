import os
import dspy
from dotenv import load_dotenv
from execution.openrouter_adapter import OpenRouterAdapter
from execution.nlu import extract_commands

# Force load .env
load_dotenv()

key = os.getenv("OPENROUTER_API_KEY")
print(f"API Key present: {bool(key)}")

# Config
try:
    lm = OpenRouterAdapter(
        model='google/gemini-2.0-flash-001',
        api_key=key
    )
    dspy.settings.configure(lm=lm)
    print("OpenRouterAdapter configured.")
except Exception as e:
    print(f"Adapter Init Failed: {e}")
    exit(1)

# Debug the raw LM output
print("\n--- Testing Raw LM Response ---")
try:
    response = lm("Say 'test' and nothing else.")
    print(f"Raw LM Response: {response}")
except Exception as e:
    print(f"Raw LM Error: {e}")

# Test Command Extraction
# Test Command
test_input = "open word , open excel , open powerpoint, open whatsapp"
print(f"\n--- Testing NLU Extraction for: '{test_input}' ---")

try:
    cmds = extract_commands(test_input)
    print(f"Extracted {len(cmds)} commands.")
    for cmd in cmds:
        print(f"CMD: {cmd}")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Extraction Error: {e}")

# Inspect History to see what was sent/received
print("\n--- Adapter History ---")
for entry in lm.history:
    print(f"PROMPT: {entry['prompt'][:100]}...")
    print(f"RESPONSE: {entry['response']}")
    print("-" * 10)
