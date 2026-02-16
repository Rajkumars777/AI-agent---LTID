"""
TEST: Myntra Filter Execution
Verifies that the agent can find and click "Size 9" filter on Myntra.
"""
import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Configure DSPy
import dspy
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), 'backend', '.env'))

openrouter_key = os.getenv("OPENROUTER_API_KEY")
if openrouter_key:
    from execution.openrouter_adapter import OpenRouterAdapter
    lm = OpenRouterAdapter(model='google/gemini-2.0-flash-001', api_key=openrouter_key)
    dspy.settings.configure(lm=lm)
else:
    print("❌ No OPENROUTER_API_KEY found! LLM calls will fail.")
    sys.exit(1)

from capabilities.browser_agent import browser_agent

def llm_fn(prompt):
    # Bypass dspy.Predict and call the LM directly for raw output
    return dspy.settings.lm(prompt)[0]

async def test():
    print("=" * 70)
    print("TEST: Myntra Filter (Size 9)")
    print("=" * 70)

    url = "https://www.myntra.com/men-shoes"
    goal = 'filter size 9'
    
    # 1. Start & Navigate
    print(f"\n[1] Navigating to {url}...")
    # Manually navigate to skip the search step for this test, focusing on filter
    # But wait, the user's command was "Open myntra.com and search for 'men shoes', filter size 9"
    # So let's try the full flow or at least start from the search result page.
    # The URL `https://www.myntra.com/men-shoes` is effectively the search result for "men shoes".
    
    result = await asyncio.to_thread(
        browser_agent.run_task, url, goal, llm_fn, 5
    )
    
    print(f"\n[RESULT]:\n{result}")
    
    await asyncio.to_thread(browser_agent.stop)

if __name__ == "__main__":
    asyncio.run(test())
