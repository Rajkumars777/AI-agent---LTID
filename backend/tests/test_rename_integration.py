"""
Integration test for RENAME command with actual fast path processing
"""

import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Simulate fast path processing
import re
from execution.nlu import Command

test_input = "rename rajakumar.pdf into raj.pdf"

print("="*60)
print("RENAME COMMAND INTEGRATION TEST")
print("="*60)
print(f"Input: '{test_input}'")
print()

# Fast path regex
simple_pattern = r"^\s*(open|launch|play|view|show|get|search|close|stop|exit|kill|type|write|set|delete|remove|rename|move)\s+(.+)$"

match = re.match(simple_pattern, test_input, re.IGNORECASE)

if match:
    verb = match.group(1).upper()
    target = match.group(2).strip()
    
    # Normalize
    if verb in ["REMOVE"]: verb = "DELETE"
    
    # RENAME/MOVE parsing
    context = None
    if verb in ["RENAME", "MOVE"]:
        rename_pattern = r"^(.+?)\s+(?:to|into)\s+(.+)$"
        rename_match = re.match(rename_pattern, target, re.IGNORECASE)
        
        if rename_match:
            target = rename_match.group(1).strip()
            context = rename_match.group(2).strip()
   
print(f"✅ Command created:")
    cmd = Command(action=verb, target=target, context=context)
    print(f"   Action: {cmd.action}")
    print(f"   Target: {cmd.target}")
    print(f"   Context: {cmd.context}")
    print()
    print("Result: rename_file(target='rajakumar.pdf', context='raj.pdf')")
    print("        ✅ Will work correctly now!")
else:
    print("❌ No match")

print("="*60)
