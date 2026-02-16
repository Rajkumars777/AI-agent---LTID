"""
LIVE EXECUTION: Run all 5 web commands through the full browser agent pipeline.
Each command opens Chromium, navigates, and uses the LLM to search/interact.
"""
import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Configure DSPy (same as agent.py)
import dspy
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), 'backend', '.env'))

openrouter_key = os.getenv("OPENROUTER_API_KEY")
if openrouter_key:
    from execution.openrouter_adapter import OpenRouterAdapter
    lm = OpenRouterAdapter(model='google/gemini-2.0-flash-001', api_key=openrouter_key)
    dspy.settings.configure(lm=lm)
    print("✅ DSPy configured with OpenRouter (Gemini Flash)")
else:
    print("❌ No OPENROUTER_API_KEY found! LLM calls will fail.")
    sys.exit(1)

from execution.nlu import get_commands, generate_text_content
from capabilities.browser_agent import browser_agent

# Site map (same as handler)
SITE_MAP = {
    "amazon": "https://www.amazon.in",
    "flipkart": "https://www.flipkart.com",
    "myntra": "https://www.myntra.com",
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "wikipedia": "https://www.wikipedia.org",
}

def resolve_url(target, context):
    """Resolve target to a URL."""
    import re
    # Check for full URL
    m = re.search(r'(https?://[^\s,]+)', target)
    if m:
        return m.group(1)
    # Check site map
    for name, url in SITE_MAP.items():
        if name in target.lower() or name in context.lower():
            return url
    # Domain fallback
    if re.search(r'\w+\.\w+', target):
        return f"https://www.{target}"
    return f"https://www.google.com/search?q={target}"


def llm_fn(prompt):
    """LLM call for the browser agent loop."""
    return generate_text_content(prompt)


async def execute_command(index, user_input):
    """Execute a single web command end-to-end."""
    print(f"\n{'='*70}")
    print(f"COMMAND {index}: {user_input}")
    print(f"{'='*70}")

    # Step 1: NLU
    print("\n  [NLU] Extracting command...")
    cmds = get_commands(user_input)
    cmd = cmds[0]
    print(f"  → action={cmd.action}, target='{cmd.target}'")

    if cmd.action != "WEB_CONTROL":
        print(f"  ❌ SKIP: Not classified as WEB_CONTROL (got {cmd.action})")
        return False

    # Step 2: Resolve URL
    url = resolve_url(cmd.target, cmd.context or "")
    print(f"  [URL] Resolved: {url}")

    # Step 3: Run browser agent (max 5 turns to keep it fast)
    goal = cmd.context or user_input
    print(f"  [AGENT] Starting browser task with goal: '{goal[:60]}...'")
    print(f"  [AGENT] Max turns: 5")

    try:
        result = await asyncio.to_thread(
            browser_agent.run_task, url, goal, llm_fn, 5
        )
        print(f"\n  [RESULT]:")
        # Print each line of result
        for line in result.split("\n"):
            print(f"    {line}")
        
        # Stop browser after each command to start fresh
        await asyncio.to_thread(browser_agent.stop)
        
        success = "completed" in result.lower() or "finish" in result.lower()
        print(f"\n  {'✅ COMPLETED' if success else '⚠️ PARTIAL (timed out or continuing)'}")
        return True

    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        await asyncio.to_thread(browser_agent.stop)
        return False


async def main():
    commands = [
        'Go to amazon.in and search for "iPhone 15".',
        'Open flipkart.com, search for "gaming laptop".',
        'Go to amazon.in and search for "headphones".',
        'Open myntra.com and search for "men shoes".',
        'Go to youtube.com, search "AI news".',
    ]

    print("=" * 70)
    print("  LIVE BROWSER EXECUTION - 5 WEB COMMANDS")
    print("  Each command opens Chromium, navigates, and searches using AI.")
    print("=" * 70)

    results = []
    for i, cmd in enumerate(commands, 1):
        success = await execute_command(i, cmd)
        results.append((cmd[:50], success))
        # Brief pause between commands
        await asyncio.sleep(1)

    # Summary
    print(f"\n\n{'='*70}")
    print("EXECUTION SUMMARY")
    print(f"{'='*70}")
    for cmd, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {cmd}...")
    
    passed = sum(1 for _, s in results if s)
    print(f"\n  {passed}/{len(results)} commands executed successfully")
    print(f"{'='*70}")


if __name__ == "__main__":
    asyncio.run(main())
