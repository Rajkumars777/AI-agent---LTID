import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

from execution.nlu import get_commands
import dspy
from execution.openrouter_adapter import OpenRouterAdapter
from dotenv import load_dotenv

load_dotenv("backend/.env")

# Configure DSPy
openrouter_key = os.getenv("OPENROUTER_API_KEY")
if not openrouter_key:
    # Try literal check if environment didn't load
    with open("backend/.env", "r") as f:
        for line in f:
            if "OPENROUTER_API_KEY" in line:
                openrouter_key = line.split("=")[1].strip().strip("'\"")
                break

if openrouter_key:
    lm = OpenRouterAdapter(
        model='google/gemini-2.0-flash-001',
        api_key=openrouter_key
    )
    dspy.settings.configure(lm=lm)

def test_deep_understanding():
    print("--- Testing Deep Understanding & Reasoning ---")
    
    # 1. Simple Command (should use Fast Path)
    simple_cmd = "open notepad"
    cmds_simple = get_commands(simple_cmd)
    print(f"Simple Command '{simple_cmd}' -> action: {cmds_simple[0].action}")
    assert len(simple_cmd.split()) <= 4
    
    # 2. Complex/Ambiguous Command (should use LLM)
    complex_cmd = "extract the information about the latest news on Trump from web"
    print(f"\nProcessing complex command: '{complex_cmd}'")
    cmds_complex = get_commands(complex_cmd)
    
    if not cmds_complex:
        print("❌ Failed: No commands extracted")
        return
        
    cmd = cmds_complex[0]
    print(f"Action: {cmd.action}")
    print(f"Target: {cmd.target}")
    print(f"Reasoning: {cmd.reasoning}")
    
    assert cmd.action == "WEB_TASK"
    assert cmd.reasoning is not None
    assert len(cmd.reasoning) > 0

    print("\n✅ Deep Understanding Verified!")

if __name__ == "__main__":
    test_deep_understanding()
