
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import asyncio

# Ensure backend is in path
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Mock dependencies BEFORE importing agent
sys.modules["capabilities.desktop"] = MagicMock()
sys.modules["capabilities.llm_general"] = MagicMock()
sys.modules["execution.nlu"] = MagicMock()

# We need to mock system_utils because it imports pygetwindow which might fail in this headless-like env if not careful
# But we want to check if execute_generative_command is called.
mock_sys_utils = MagicMock()
sys.modules["execution.system_utils"] = mock_sys_utils

from backend.execution.nlu import Command

# Mock the Command class to behave like Pydantic model (or just object) for the agent logic
class MockCommand:
    def __init__(self, action, target, context=None):
        self.action = action
        self.target = target
        self.context = context

sys.modules["execution.nlu"].Command = MockCommand

import backend.agent as agent

class TestA1Logic(unittest.TestCase):
    def test_optimization_merge(self):
        print("\n--- Test: Optimization Merge (Open + Type Async) ---")
        
        # Setup inputs: "open notepad and type about AI"
        # Fast Path (Regex) will split this into:
        # 1. OPEN notepad
        # 2. TYPE about AI (Unquoted -> GENERATE_ASYNC)
        
        # We simulate what the regex parser produces in fast_path_commands
        commands_input = [
            MockCommand(action="OPEN", target="notepad"),
            MockCommand(action="TYPE", target="about AI", context="GENERATE_ASYNC")
        ]
        
        # We need to inject these into agent's execute_tool logic.
        # But execute_tool parses string. 
        # Let's verify the parsing AND optimization together.
        
        state = {"input": "open notepad and type about AI", "messages": [], "intermediate_steps": []}
        
        # We mock execute_generative_command to check if it's called
        async def mock_exec_gen(app, prompt):
            print(f"MOCK: Executing Generative Command: App='{app}', Prompt='{prompt}'")
            return "Done"
            
        mock_sys_utils.execute_generative_command = mock_exec_gen
        
        # Run agent
        # We need to ensure parsing happens as expected.
        # "open notepad and type about AI" -> Regex works?
        # "open" is in simple_pattern. "type" is in simple_pattern.
        # split by " and " -> ["open notepad", "type about AI"]
        
        result = agent.execute_tool(state)
        
        # Check if execute_generative_command was called
        # It's an async function properly mocked?
        # agent calls asyncio.run(execute_generative_command(...))
        # Since we mocked it as an async function, asyncio.run should accept it.
        
        # We verify that 'launch_application' was NOT called (optimization worked)
        # agent imports launch_application from capabilities.desktop
        # We can check sys.modules["capabilities.desktop"].launch_application.call_count
        
        launch_count = sys.modules["capabilities.desktop"].launch_application.call_count
        print(f"Launch Count: {launch_count}")
        
        if launch_count == 0:
            print("SUCCESS: Explicit OPEN was optimized away.")
        else:
            print("FAILURE: Explict OPEN was executed.")
            
        # We verify execute_generative_command called with "notepad"
        # We can't easily check call args of the async wrapper if we just assigned it.
        # But the print "MOCK: Executing..." will show up in output.

    def test_quoted_literal(self):
        print("\n--- Test: Quoted Literal (Fast Path) ---")
        state = {"input": 'type "hello world"', "messages": [], "intermediate_steps": []}
        
        agent.execute_tool(state)
        
        # Check type_text called
        start_count = sys.modules["capabilities.desktop"].type_text.call_count
        # It was called once?
        # Note: Previous test might have called it? No, previous test used gen command.
        print(f"Type Text called: {start_count}")
        
if __name__ == "__main__":
    unittest.main()
