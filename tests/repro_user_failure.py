import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

# Add backend to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Mock capabilities
sys.modules['capabilities.desktop'] = MagicMock()
sys.modules['capabilities.excel_manipulation'] = MagicMock()

# Mock browser capability to avoid real network
mock_browser = MagicMock()
async def mock_orchestrate(url, action, selector=None):
    print(f"MOCK BROWSER CALLED: URL={url}, ACTION={action}, SELECTOR={selector}")
    return {"status": "Scraped data", "data": [{"close": 35000}], "file": "test.xlsx"}

mock_browser.orchestrate_web_task = mock_orchestrate
sys.modules['backend.capabilities.browser'] = mock_browser

# We want to use the REAL NLU (OpenRouterAdapter) to see parsing, 
# but if it fails we might need to mock it. 
# Let's try to use the real one first if possible, or maybe just mock extract_commands
# to return what we *think* it returns, or see what it returns.
# Actually, the user asks "why this command not woked", implying parsing/logic error.
# Using the real NLU is best to diagnose parsing.
# But I can't check the NLU output without running it. 
# `repro_e2e.py` showed we can run agent.py.

from backend.agent import execute_tool

def test_user_failure():
    user_input = """Web Open - pen the Nikkei newspaper website on the web.
Get Value - Retrieve the previous day’s closing value of the Nikkei Stock Average.
File - create a stock.xlsx file and store the value in Avg Nikkei stock price column
Input the value into the Nikkei Stock Average field, rounded to two decimal places."""
    
    print(f"Testing User Input:\n{user_input}\n")
    
    state = {"input": user_input, "messages": [], "intermediate_steps": []}
    
    import json
    results_out = []
    
    try:
        result = execute_tool(state)
        print("\nExecution Results:")
        for step in result.get("intermediate_steps", []):
            print(f"- Type: {step.get('type')}")
            content = step.get('content')
            print(f"  Content: {content}")
            results_out.append({"type": step.get('type'), "content": str(content)})
            
        with open("repro_result.json", "w", encoding="utf-8") as f:
            json.dump(results_out, f, indent=2)
            
    except Exception as e:
        print(f"Execution failed: {e}")
        import traceback
        traceback.print_exc()
        with open("repro_result.json", "w", encoding="utf-8") as f:
            json.dump({"error": str(e)}, f)

if __name__ == "__main__":
    test_user_failure()
