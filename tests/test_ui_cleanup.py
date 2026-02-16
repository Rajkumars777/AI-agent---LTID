import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

from execution.nlu import fast_path_extract
from execution.handlers import handle_action
import asyncio

async def test_ui_cleanup():
    print("--- Testing NLU Extraction Robustness ---")
    # Command that previously failed (stayed on google.com)
    user_input = "extract the information about 'trump' from web"
    cmds = fast_path_extract(user_input)
    
    assert cmds[0].action == "WEB_TASK"
    # Target should now be a DuckDuckGo search URL, not just google.com
    print(f"Extraction Target: {cmds[0].target}")
    assert "duckduckgo.com" in cmds[0].target
    assert "trump" in cmds[0].target.lower()

    print("\n--- Testing Screenshot Removal ---")
    # Mocking orchestrate_web_task to check returning fields
    import execution.handlers as h
    async def mock_web_success(url, action, sel):
        return {
            "status": "Success", 
            "data": "Extracted info", 
            "file": "some_file.xlsx" # Should not be a screenshot
        }
    
    original_web = h.orchestrate_web_task
    h.orchestrate_web_task = mock_web_success
    
    res = await h.handle_action("WEB_TASK", "http://example.com", "read_page", "test")
    attachment = res.get("attachment", {})
    
    print(f"Attachment fields: {list(attachment.keys())}")
    assert "screenshot" not in attachment
    assert attachment.get("type") == "web_result"
    
    h.orchestrate_web_task = original_web
    print("\n✅ UI Cleanup and Extraction Verified!")

if __name__ == "__main__":
    asyncio.run(test_ui_cleanup())
