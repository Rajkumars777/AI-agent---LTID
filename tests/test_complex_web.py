"""
Test complex multi-step web commands (search + filter/sort).
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

print("=" * 70)
print("COMPLEX WEB COMMAND NLU TEST")
print("=" * 70)

all_passed = True
for i, cmd in enumerate(test_cases, 1):
    print(f"\n--- Test {i}: {cmd[:65]}...")
    result = get_commands(cmd)
    
    if result and result[0].action == "WEB_CONTROL":
        print(f"  ✅ PASS")
        print(f"     action  = {result[0].action}")
        print(f"     target  = '{result[0].target}'")
        print(f"     context = '{result[0].context[:70]}...'")
    else:
        action = result[0].action if result else "NONE"
        target = result[0].target if result else "NONE"
        print(f"  ❌ FAIL → action={action}, target='{target}'")
        if len(result) > 1:
            print(f"     SPLIT into {len(result)} commands:")
            for j, r in enumerate(result):
                print(f"       [{j}] {r.action} → {r.target}")
        all_passed = False

print("\n" + "=" * 70)
if all_passed:
    print("ALL 5 COMPLEX TESTS PASSED ✅")
else:
    print("SOME TESTS FAILED ❌")
print("=" * 70)
