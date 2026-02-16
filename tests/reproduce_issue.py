import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import re
from execution.nlu import extract_commands

def test_fast_path(user_input):
    simple_pattern = r"^\s*(open|launch|play|view|show|get|search|close|stop|exit|kill|type|write|set|delete|remove|rename|move|add|generate|create|insert|read|find|filter|who|what|which|list|count)\s+(.+)$"
    match = re.match(simple_pattern, user_input, re.IGNORECASE)
    if match:
        print(f"[FAST PATH] Match found! Verb: {match.group(1)}")
        return True
    else:
        print("[FAST PATH] No match found.")
        return False

def test_nlu(user_input):
    print(f"\nTesting NLU with input: '{user_input}'")
    commands = extract_commands(user_input)
    print(f"[NLU] Commands extracted: {commands}")

if __name__ == "__main__":
    user_input = "serach on web about today's apple inc stock price value"
    
    # 1. Test Fast Path
    print("--- Fast Path Check ---")
    matched = test_fast_path(user_input)
    
    # 2. Test NLU fallback if Fast Path failed
    if not matched:
        print("\n--- Fallback NLU Check ---")
        try:
            test_nlu(user_input)
        except Exception as e:
            print(f"[NLU] ERROR: {e}")
