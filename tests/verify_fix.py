
import sys
import unittest
from unittest.mock import MagicMock

# Mock capabilities before importing agent
mock_desktop = MagicMock()
mock_excel = MagicMock()
mock_code_gen = MagicMock()

sys.modules["capabilities.desktop"] = mock_desktop
sys.modules["capabilities.excel_manipulation"] = mock_excel
sys.modules["capabilities.code_generator"] = mock_code_gen

# Now import agent
# We need to ensure we don't actually configure DSPy if we don't have key, or we mock it.
# agent.py configures dspy at module level.
# We can mock dspy too if needed, but let's see.
import os
os.environ["OPENROUTER_API_KEY"] = "dummy" 
# This will try to import openrouter_adapter and config dspy.
# If openrouter_adapter fails to import, agent.py might fail.
# openrouter_adapter imports openai.

from backend.agent import execute_tool

def test_fast_path():
    print("Testing 'open notepad and type about japan'...")
    state = {"input": "open notepad and type about japan", "messages": [], "intermediate_steps": []}
    result = execute_tool(state)
    
    steps = result.get("intermediate_steps", [])
    print(f"Result steps: {len(steps)}")
    
    actions = []
    for step in steps:
        print(f"Step: {step['content']}")
        if "Desktop Automation (Open)" in step['content'] or "Action: OPEN" in step['content']:
            actions.append("OPEN")
        if "Desktop Automation (Type)" in step['content'] or "Action: TYPE" in step['content']:
            actions.append("TYPE")
            
    # Check if we got expected actions
    if "OPEN" in actions and "TYPE" in actions:
        print("SUCCESS: Fast path execution confirmed.")
    else:
        print("FAILURE: Did not execute expected fast path actions.")
        # Check if it went to dynamic code
        for step in steps:
            if "Dynamic AI Coder" in step['content']:
                print("FAILURE: Fell back to Dynamic Code.")

if __name__ == "__main__":
    try:
        test_fast_path()
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
