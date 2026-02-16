import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

from execution.nlu import fast_path_extract

def test_extract_command():
    print("--- Testing NLU Extract Command ---")
    user_input = "extract the information about 'trump' from web"
    cmds = fast_path_extract(user_input)
    
    if not cmds:
        print("❌ Test Failed: No commands extracted")
        return
        
    cmd = cmds[0]
    print(f"Action: {cmd.action}")
    print(f"Target: {cmd.target}")
    print(f"Context: {cmd.context}")
    
    assert cmd.action == "WEB_TASK"
    assert "trump" in cmd.target
    assert "smart_scrape" in cmd.context
    
    print("\n✅ Extraction Verified!")

if __name__ == "__main__":
    test_extract_command()
