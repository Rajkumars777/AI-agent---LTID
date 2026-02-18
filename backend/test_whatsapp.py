import asyncio
import os
import sys

# Ensure backend is in path
sys.path.append(os.path.abspath("backend"))

# Register core tools
from tools.core_tools import initialize_core_tools
initialize_core_tools()

from execution.nlu import get_commands_dynamic

async def test_whatsapp():
    query = "open whatsapp and type a 'hi' to Little girl akka"
    print(f"\n[Test] Analyzing Query: '{query}'")
    
    commands = await get_commands_dynamic(query)
    
    if not commands:
        print("❌ No commands returned.")
        return

    print(f"\n[Result] NLU generated {len(commands)} steps:")
    for i, cmd in enumerate(commands):
        print(f"  Step {i+1}: {cmd.action} params={cmd.params}")

if __name__ == "__main__":
    asyncio.run(test_whatsapp())
