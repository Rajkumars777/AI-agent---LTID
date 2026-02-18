import asyncio
import os
import sys

# Ensure backend folder is in path
sys.path.append(os.path.abspath("backend"))

from agent import run_agent

async def test_evolution():
    print("🚀 Testing Refined Evolution Pipeline\n")
    
    # query that should trigger evolution
    query = "check if the file 'important_notes.txt' contains the word 'Confidential'"
    
    print(f"Query: {query}")
    try:
        result = await run_agent(query, task_id="evolution_test_refined")
        steps = result.get("steps", [])
        for step in steps:
            print(f"[{step['type']}] {step['content']}")
    except Exception as e:
        print(f"❌ Evolution Test Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_evolution())
