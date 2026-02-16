import sys
import os

# Add backend to path
current_dir = os.getcwd()
backend_path = os.path.join(current_dir, 'backend')
if backend_path not in sys.path:
    sys.path.append(backend_path)

# Mock capabilities to avoid real browser launch
import unittest.mock
sys.modules['capabilities.desktop'] = unittest.mock.Mock()
sys.modules['capabilities.excel_manipulation'] = unittest.mock.Mock()
sys.modules['capabilities.browser'] = unittest.mock.Mock()

# Now import execute_tool
from backend.agent import execute_tool

def test_nlu_parsing():
    user_input = "Web Open - pen the Nikkei newspaper website on the web. Get Value - Retrieve the previous 10 day’s closing value of the Nikkei Stock Average. File - create a stock.xlsx file and add the stock value in the Nikkei avg stock value column Input the value into the Nikkei Stock Average field, rounded to two decimal places."
    
    print(f"Testing input: {user_input}")
    
    state = {
        "input": user_input, "messages": [], "intermediate_steps": []
    }
    
    # We want to verify if '10 days' is parsed. 
    # Since execute_tool is a black box that executes, mocking the browser capability will intercept the call.
    
    browser_mock = sys.modules['capabilities.browser']
    browser_mock.orchestrate_web_task = unittest.mock.AsyncMock()
    
    try:
        execute_tool(state)
        
        # Check call arguments
        calls = browser_mock.orchestrate_web_task.call_args_list
        if calls:
            print("Browser called with:")
            for call in calls:
                print(call)
        else:
            print("Browser NOT called (NLU failed to trigger browser task, or mocked incorrectly)")
            
    except Exception as e:
        print(f"Execution error: {e}")

if __name__ == "__main__":
    test_nlu_parsing()
