import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

from execution.nlu import fast_path_extract
from execution.handlers import handle_action

async def test_empty_url_fix():
    print("--- Testing NLU Empty URL Fix ---")
    # 1. Test "Open website" (Previously resulted in empty target)
    cmds = fast_path_extract("Open website")
    print(f"NLU 'Open website' -> Action: {cmds[0].action}, Target: {cmds[0].target}")
    assert cmds[0].target == "https://www.google.com"
    
    # 2. Test "Search on web"
    cmds = fast_path_extract("Search on web")
    print(f"NLU 'Search on web' -> Action: {cmds[0].action}, Target: {cmds[0].target}")
    # Note: Target for "Search on web" might become DuckDuckGo search for "" or Google
    # According to logic: web_target = "".replace("on web", "") ... then if not web_target ...
    assert "google.com" in cmds[0].target

    print("\n--- Testing Handlers Fallback ---")
    import asyncio
    # Mocking orchestrate_web_task to avoid launch
    import execution.handlers as h
    async def mock_web(url, action, sel):
        print(f"Mock Browser called with URL: '{url}'")
        return {"status": "Success", "data": "Mock data"}
    
    h.orchestrate_web_task = mock_web
    
    # Test handling of empty target
    print("Handling empty target in WEB_TASK...")
    res = await h.handle_action("WEB_TASK", "", "read_page", "test input")
    print(f"Handler fallback result: {res['trace_logs'][-1]}")
    assert "https://www.google.com" in res['trace_logs'][-1]

    print("\n✅ All Fallbacks Verified!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_empty_url_fix())
