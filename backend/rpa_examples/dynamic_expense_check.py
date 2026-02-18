
import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.agentic_orchestrator import orchestrator

async def run_demo():
    print("🚀 Starting Dynamic Expense Check Demo (Hybrid Agent)...")
    
    # 1. Define the Goal using Natural Language
    # This prompts the agent to use its new Visual Capabilities
    goal = """
    I need to verify transportation expenses.
    1. Open the file 'expenses.xlsx' (Assume it's on the desktop or I can interpret 'Open Excel').
    2. Read the destination from the screen (Look for 'Destination:' text).
    3. Open Chrome and search for the distance to that destination.
    4. Read the distance from the Google Maps result.
    5. Switch back to Excel and type the distance.
    """
    
    print(f"Goal: {goal}\n")
    
    # 2. Execute
    # In a real scenario, we would provide the starting context.
    # For this demo, we assume the environment is set up or the agent will try to handle it.
    result = await orchestrator.execute_task(goal, task_id="demo_expense_check")
    
    print("\n\n==================================================")
    print("Execution Result:")
    print(f"Success: {result.success}")
    print("\nLog Summary:")
    for log in result.logs:
        print(log)
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_demo())
