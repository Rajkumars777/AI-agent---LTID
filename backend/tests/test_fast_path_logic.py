
import re
import sys

# Mock Command class
class Command:
    def __init__(self, action, target, context):
        self.action = action
        self.target = target
        self.context = context
    def __repr__(self):
        return f"Command({self.action}, {self.target}, {self.context})"

# Mock execution.nlu
mock_nlu = type("module", (), {})()
mock_nlu.Command = Command
sys.modules["execution.nlu"] = mock_nlu

def test_logic(user_input):
    print(f"Testing input: '{user_input}'")
    
    # LOGIC FROM AGENT.PY (Fast Path)
    simple_pattern = r"^\s*(open|launch|play|view|show|get|search|close|stop|exit|kill|type|write|set)\s+(.+)$"
    
    parts = re.split(r",|\s+and\s+", user_input, flags=re.IGNORECASE)
    parts = [p.strip() for p in parts if p.strip()]
    
    fast_path_commands = []
    all_simple = True
    
    # Heuristic removed
    # if len(user_input.split()) > 4: ...
    
    for part in parts:
        match = re.match(simple_pattern, part, re.IGNORECASE)
        if match:
            verb = match.group(1).upper()
            target = match.group(2).strip()
            
            if verb in ["LAUNCH", "PLAY", "VIEW", "SHOW", "GET", "SEARCH"]: verb = "OPEN"
            if verb in ["STOP", "EXIT", "KILL"]: verb = "CLOSE"
            if verb in ["WRITE"]: verb = "TYPE"
            
            fast_path_commands.append(Command(action=verb, target=target, context=None))
        else:
            print(f"DEBUG: Part '{part}' did not match simple pattern.")
            all_simple = False
            break
            
    if all_simple and fast_path_commands:
        print("Fast Path Success!")
        for cmd in fast_path_commands:
            print(f" - {cmd}")
    else:
        print("Fast Path Failed (would fallback to NLU).")

if __name__ == "__main__":
    test_logic("open notepad and type about japan")
