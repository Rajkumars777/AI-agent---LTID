import asyncio
import os
import sys

# Ensure backend is in path
sys.path.append(os.path.abspath("backend"))

# Register core tools
from tools.core_tools import initialize_core_tools
initialize_core_tools()

from execution.nlu import get_commands_dynamic

async def test_open():
    query = "open sales_data.xlsx file"
    print(f"\n[Test] Analyzing Query: '{query}'")
    
    commands = await get_commands_dynamic(query)
    
    if not commands:
        print("❌ No commands returned.")
        return

    for cmd in commands:
        print(f"Action: {cmd.action}")
        print(f"Params: {cmd.params}")
        
        if cmd.action == "ANSWER":
            print("⚠️ ISSUE DETECTED: Agent is answering instead of acting.")
        else:
            print("✅ Agent selected a tool correctly.")

if __name__ == "__main__":
    asyncio.run(test_open())
