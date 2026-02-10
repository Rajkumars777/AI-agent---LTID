import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Configure DSPy
import dspy
from dotenv import load_dotenv
load_dotenv()

openrouter_key = os.getenv("OPENROUTER_API_KEY")
print(f"API Key found: {bool(openrouter_key)}")

if openrouter_key:
    from backend.execution.openrouter_adapter import OpenRouterAdapter
    lm = OpenRouterAdapter(model='google/gemini-2.0-flash-001', api_key=openrouter_key)
    dspy.settings.configure(lm=lm)
    print("DSPy configured successfully")
else:
    print("ERROR: No API Key found!")
    sys.exit(1)

from backend.execution.nlu import extract_commands

# Test the DELETE command
test_commands = [
    "delete sample.xlsx file",
    "delete sample.xls file",
    "remove notes.txt"
]

for test in test_commands:
    print(f"\n{'='*60}")
    print(f"Testing: '{test}'")
    print('='*60)
    try:
        commands = extract_commands(test)
        if commands:
            for cmd in commands:
                print(f"✓ Action: {cmd.action}, Target: {cmd.target}, Context: {cmd.context}")
        else:
            print("✗ No commands extracted")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
