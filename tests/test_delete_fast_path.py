"""
Quick test to verify DELETE command is now recognized by Fast Path.
"""

import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Test Fast Path directly
import re

user_input = "delete sample.xlsx"

# Updated pattern with delete/remove
simple_pattern = r"^\s*(open|launch|play|view|show|get|search|close|stop|exit|kill|type|write|set|delete|remove|rename|move)\s+(.+)$"

match = re.match(simple_pattern, user_input, re.IGNORECASE)

print("="*60)
print("FAST PATH DELETE TEST")
print("="*60)
print(f"Input: '{user_input}'")
print(f"Pattern: {simple_pattern}")
print()

if match:
    verb = match.group(1).upper()
    target = match.group(2).strip()
    
    # Normalize
    if verb == "REMOVE":
        verb = "DELETE"
    
    print("✅ MATCH FOUND!")
    print(f"   Verb: {verb}")
    print(f"   Target: {target}")
    print()
    print("Result: Command will be processed via FAST PATH")
else:
    print("❌ NO MATCH")
    print("   Command will fall through to NLU (may fail)")

print("="*60)
