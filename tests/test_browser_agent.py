"""
End-to-end test for the rewritten Browser Agent (sync Playwright + thread).
Tests: launch → navigate → snapshot → actions → stop
"""
import asyncio
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from capabilities.browser_agent import browser_agent

async def test():
    print("=" * 60)
    print("TEST: Sync Playwright Browser Agent")
    print("=" * 60)

    # 1. Navigate (this auto-starts the browser)
    print("\n[1] Navigating to example.com...")
    result = await asyncio.to_thread(browser_agent.navigate, "https://www.example.com")
    print(f"    Result: {result}")
    assert "Navigated" in result, f"Navigation failed: {result}"

    # 2. DOM Snapshot
    print("\n[2] Getting DOM snapshot...")
    snapshot = await asyncio.to_thread(browser_agent.get_dom_snapshot)
    print(f"    Snapshot:\n{snapshot}")
    assert "Page Title" in snapshot, f"Snapshot failed: {snapshot}"

    # 3. Click action (Example.com has a "More information..." link)
    print("\n[3] Clicking first link...")
    action_result = await asyncio.to_thread(
        browser_agent.execute_action, {"action": "click", "id": 0}
    )
    print(f"    Result: {action_result}")

    # 4. New snapshot after click
    print("\n[4] Snapshot after click...")
    import time
    await asyncio.to_thread(time.sleep, 2)
    snapshot2 = await asyncio.to_thread(browser_agent.get_dom_snapshot)
    print(f"    New page:\n{snapshot2[:300]}")

    # 5. Stop
    print("\n[5] Stopping browser...")
    await asyncio.to_thread(browser_agent.stop)
    print("    Done.")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✅")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test())
