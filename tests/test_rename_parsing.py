"""
Test RENAME and MOVE command parsing
"""

import sys
import os
import re
sys.path.append(os.path.join(os.getcwd(), "backend"))

test_commands = [
    "rename rajakumar.pdf into raj.pdf",
    "rename old.txt to new.txt",
    "move file.pdf to desktop",
    "move image.png into documents"
]

print("="*60)
print("RENAME/MOVE PARSING TEST")
print("="*60)

for cmd in test_commands:
    print(f"\nInput: '{cmd}'")
    
    # Extract verb and rest
    simple_pattern = r"^\s*(rename|move)\s+(.+)$"
    match = re.match(simple_pattern, cmd, re.IGNORECASE)
    
    if match:
        verb = match.group(1).upper()
        target_full = match.group(2).strip()
        
        # Parse "X to/into Y"
        rename_pattern = r"^(.+?)\s+(?:to|into)\s+(.+)$"
        rename_match = re.match(rename_pattern, target_full, re.IGNORECASE)
        
        if rename_match:
            old_name = rename_match.group(1).strip()
            new_name = rename_match.group(2).strip()
            
            print(f"✅ Parsed successfully!")
            print(f"   Action: {verb}")
            print(f"   Target: {old_name}")
            print(f"   Context: {new_name}")
        else:
            print(f"❌ Failed to parse 'to/into' pattern")
    else:
        print(f"❌ Not a rename/move command")

print("\n" + "="*60)
