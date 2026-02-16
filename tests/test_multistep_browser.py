
import asyncio
import os
import sys

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from capabilities.browser_agent import browser_agent
from capabilities.security_manager import security_manager

# Mock Execution Handler for testing the loop logic
async def mock_handler_loop():
    print("Testing Multi-Step Loop...")
    
    # 1. Setup Mock Page
    html_content = """
    <html>
        <body>
            <h1>Amazon Mock</h1>
            <input type="text" placeholder="Search Amazon" id="search-box">
            <button id="search-btn" onclick="document.body.innerHTML='<h1>Results</h1><button id=filter-btn>Filter</button>'">Search</button>
        </body>
    </html>
    """
    url = f"data:text/html,{html_content}"
    await browser_agent.navigate(url)
    
    # Simulate the loop logic from handlers.py
    max_turns = 5
    turn_count = 0
    
    print("\n--- LOOP START ---")
    while turn_count < max_turns:
        turn_count += 1
        snapshot = await browser_agent.get_dom_snapshot()
        print(f"\n[Turn {turn_count}] Snapshot:\n{snapshot}")
        
        # Hardcoded "LLM" decisions for the test
        if "Search Amazon" in snapshot:
            print("DECISION: Type 'iPhone'")
            await browser_agent.execute_action({"action": "type", "id": 0, "value": "iPhone"}) # Assume ID 0
            
            print("DECISION: Click Search")
            await browser_agent.execute_action({"action": "click", "id": 1}) # Assume ID 1
            
        elif "Filter" in snapshot:
            print("DECISION: Click Filter")
            await browser_agent.execute_action({"action": "click", "id": 0}) # ID resets on new page gen
            
        else:
            print("DECISION: Finish")
            break
            
        await asyncio.sleep(1)
        
    print("\n--- LOOP END ---")
    await browser_agent.stop()

if __name__ == "__main__":
    asyncio.run(mock_handler_loop())
