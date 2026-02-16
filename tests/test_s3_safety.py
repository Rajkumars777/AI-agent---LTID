import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

from capabilities.safety_engine import validate_code

def test_safe_code():
    code = """
import pandas as pd
df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
print(df.describe())
"""
    is_safe, msg = validate_code(code)
    print(f"Test Safe Code: {is_safe} ({msg})")
    assert is_safe == True

def test_unsafe_import():
    code = "import subprocess\nsubprocess.run(['ls'])"
    is_safe, msg = validate_code(code)
    print(f"Test Unsafe Import: {is_safe} ({msg})")
    assert is_safe == False
    assert "Forbidden import" in msg

def test_unsafe_call():
    code = "import os\nos.system('rm -rf /')"
    is_safe, msg = validate_code(code)
    print(f"Test Unsafe Call: {is_safe} ({msg})")
    assert is_safe == False
    assert "Dangerous operation" in msg

def test_unsafe_builtin():
    code = "eval('print(123)')"
    is_safe, msg = validate_code(code)
    print(f"Test Unsafe Builtin: {is_safe} ({msg})")
    assert is_safe == False
    assert "Dangerous function call" in msg

if __name__ == "__main__":
    try:
        test_safe_code()
        test_unsafe_import()
        test_unsafe_call()
        test_unsafe_builtin()
        print("\n✅ Safety Engine Verification Passed!")
    except Exception as e:
        print(f"\n❌ Verification Failed: {e}")
        sys.exit(1)
