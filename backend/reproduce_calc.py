import asyncio
import os
import sys

# Ensure backend is in path
sys.path.append(os.path.abspath("backend"))

# Register core tools
from tools.core_tools import initialize_core_tools
initialize_core_tools()

from execution.nlu import get_commands_dynamic

async def test_calculator():
    # Test 1: Full compound command
    query = "Open Calculator and type 1234 * 5678"
    print(f"\n[Test 1] Analyzing Query: '{query}'")
    
    commands = await get_commands_dynamic(query)
    
    if not commands:
        print("❌ No commands returned.")
    else:
        for cmd in commands:
            print(f"Action: {cmd.action}")
            print(f"Params: {cmd.params}")

    # Test 2: Typing only (simulate 2nd step)
    print("\n[Test 2] Testing type_on_screen execution directly...")
    try:
        from capabilities.desktop_automation import desktop_agent
        # Launch calculator manually first to ensure it exists for this test
        os.system("start calc")
        await asyncio.sleep(2)
        
        result = desktop_agent.type_text("1234 * 5678", window_title="Calculator")
        print(f"Direct Execution Result: {result}")
    except Exception as e:
        print(f"❌ Direct execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_calculator())
