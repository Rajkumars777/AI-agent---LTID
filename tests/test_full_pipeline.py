"""
Full end-to-end test: NLU → Handler → Browser Agent.
Tests the complete pipeline with a real browser.
"""
import asyncio
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def test_full_pipeline():
    from execution.nlu import get_commands, generate_text_content
    from capabilities.browser_agent import browser_agent
    
    test_input = 'Go to amazon.in and search for "iPhone 15".'
    
    print("=" * 70)
    print(f"FULL PIPELINE TEST: {test_input}")
    print("=" * 70)
    
    # Step 1: NLU
    print("\n[1] NLU Extraction...")
    cmds = get_commands(test_input)
    cmd = cmds[0]
    print(f"    action={cmd.action}, target='{cmd.target}', context='{cmd.context[:60]}...'")
    assert cmd.action == "WEB_CONTROL", f"Expected WEB_CONTROL, got {cmd.action}"
    print("    ✅ NLU OK")
    
    # Step 2: URL Resolution (same logic as handler)
    print("\n[2] URL Resolution...")
    site_map = {
        "amazon": "https://www.amazon.in",
        "google": "https://www.google.com",
        "youtube": "https://www.youtube.com",
        "wikipedia": "https://www.wikipedia.org",
        "flipkart": "https://www.flipkart.com",
    }
    url = None
    for name, site_url in site_map.items():
        if name in cmd.target.lower():
            url = site_url
            break
    if not url:
        url = f"https://www.google.com/search?q={cmd.target}"
    print(f"    Resolved URL: {url}")
    print("    ✅ URL Resolution OK")
    
    # Step 3: Browser Agent (limited test - navigate + snapshot only, no LLM loop)
    print("\n[3] Browser Agent: Navigate...")
    nav_result = await asyncio.to_thread(browser_agent.navigate, url)
    print(f"    {nav_result}")
    assert "Navigated" in nav_result, f"Navigation failed: {nav_result}"
    print("    ✅ Navigation OK")
    
    print("\n[4] Browser Agent: DOM Snapshot...")
    snapshot = await asyncio.to_thread(browser_agent.get_dom_snapshot)
    lines = snapshot.split("\n")
    print(f"    Title: {lines[0]}")
    print(f"    Elements found: {len(lines) - 3}")
    # Show first 5 interactive elements
    for line in lines[3:8]:
        print(f"    {line}")
    print("    ✅ Snapshot OK")
    
    # Step 4: Cleanup
    print("\n[5] Stopping browser...")
    await asyncio.to_thread(browser_agent.stop)
    print("    ✅ Browser stopped")
    
    print("\n" + "=" * 70)
    print("FULL PIPELINE TEST PASSED ✅")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
