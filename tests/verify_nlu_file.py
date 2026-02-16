
import sys
import os
import unittest
from unittest.mock import MagicMock

sys.path.append(os.path.join(os.getcwd(), "backend"))

# Mock dependencies
sys.modules["capabilities.desktop"] = MagicMock()
# sys.modules["capabilities.llm_general"] = MagicMock() - Removed Redundant

# We need the real NLU
import dspy
from dotenv import load_dotenv
load_dotenv()
openrouter_key = os.getenv("OPENROUTER_API_KEY")

if openrouter_key:
    from backend.execution.openrouter_adapter import OpenRouterAdapter
    lm = OpenRouterAdapter(model='google/gemini-2.0-flash-001', api_key=openrouter_key)
    dspy.settings.configure(lm=lm)
else:
    print("WARNING: No API Key found.")

from backend.execution.nlu import extract_commands

class TestNLUFile(unittest.TestCase):
    def test_type_in_file(self):
        text = "type about AI in notes.txt"
        print(f"\nTesting: '{text}'")
        commands = extract_commands(text)
        for cmd in commands:
            print(f"Action: {cmd.action}, Target: {cmd.target}, Context: {cmd.context}")
            
    def test_type_in_notepad(self):
        text = "type about AI in notepad"
        print(f"\nTesting: '{text}'")
        commands = extract_commands(text)
        for cmd in commands:
            print(f"Action: {cmd.action}, Target: {cmd.target}, Context: {cmd.context}")

if __name__ == "__main__":
    unittest.main()
