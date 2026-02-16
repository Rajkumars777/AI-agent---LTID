"""
Test complex multi-step web commands - VERBOSE output.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from execution.nlu import get_commands

test_cases = [
    'Go to amazon.in and search for "iPhone 15", then filter price under 50,000.',
    'Open flipkart.com, search for "gaming laptop", sort by price low to high.',
    'Go to amazon.in and search for "headphones", select 4 star and above filter.',
    'Open myntra.com and search for "men shoes", filter size 9.',
    'Go to youtube.com, search "AI news", filter by "Upload date".',
]

all_passed = True
for i, cmd in enumerate(test_cases, 1):
    print(f"\n=== Test {i} ===")
    print(f"INPUT: {cmd}")
    result = get_commands(cmd)
    print(f"COMMANDS RETURNED: {len(result)}")
    for j, r in enumerate(result):
        print(f"  [{j}] action={r.action}, target='{r.target}', context='{(r.context or '')[:80]}'")
    
    if result and result[0].action == "WEB_CONTROL" and len(result) == 1:
        print("VERDICT: ✅ PASS")
    else:
        print("VERDICT: ❌ FAIL")
        all_passed = False

print(f"\n{'ALL PASSED ✅' if all_passed else 'SOME FAILED ❌'}")
