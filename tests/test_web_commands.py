"""
Test all 5 web commands through the NLU pipeline.
Verifies that each command is correctly classified as WEB_CONTROL.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from execution.nlu import get_commands

test_cases = [
    'Go to amazon.in and search for "iPhone 15".',
    'Open wikipedia.org and search for "Artificial Intelligence".',
    'Go to youtube.com and search for "Python tutorial".',
    'Open google.com and search for "weather in Chennai".',
    'Go to flipkart.com and search for "laptop under 50000".',
]

print("=" * 70)
print("WEB COMMAND NLU EXTRACTION TEST")
print("=" * 70)

all_passed = True
for i, cmd in enumerate(test_cases, 1):
    print(f"\n--- Test {i}: {cmd}")
    result = get_commands(cmd)
    
    if result and result[0].action == "WEB_CONTROL":
        print(f"  ✅ PASS → action={result[0].action}, target='{result[0].target}'")
        print(f"           context='{result[0].context[:80]}...'")
    else:
        action = result[0].action if result else "NONE"
        target = result[0].target if result else "NONE"
        print(f"  ❌ FAIL → action={action}, target='{target}'")
        all_passed = False

print("\n" + "=" * 70)
if all_passed:
    print("ALL 5 TESTS PASSED ✅")
else:
    print("SOME TESTS FAILED ❌")
print("=" * 70)
