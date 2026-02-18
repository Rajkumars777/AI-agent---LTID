import asyncio
import os
import sys

# Ensure backend folder is in path
sys.path.append(os.path.abspath("backend"))

# Register core tools
from tools.core_tools import initialize_core_tools
initialize_core_tools()

from execution.nlu import get_commands_dynamic

async def test_nlu():
    print("\n[Test] Verifying NLU Extraction...")
    queries = [
        "rename gendat.xlsx to data_backup",
        "screenshot"
    ]
    
    for q in queries:
        print(f"\nQuery: {q}")
        try:
            commands = await get_commands_dynamic(q)
            if not commands:
                print("  ❌ No commands extracted.")
            for cmd in commands:
                print(f"  ✅ Action: {cmd.action}")
                print(f"     Params: {cmd.params}")
        except Exception:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_nlu())
