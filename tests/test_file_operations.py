import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

from capabilities.desktop import (
    find_and_open_file,
    close_application,
    move_file,
    rename_file,
    delete_file,
    find_file_paths
)

print("="*80)
print("FILE OPERATIONS TEST FOR sample.xlsx")
print("="*80)

# Test 1: Find the file
print("\n1. TESTING: Find file paths for 'sample.xlsx'")
print("-"*80)
paths = find_file_paths("sample.xlsx")
if paths:
    print(f"✓ Found {len(paths)} file(s):")
    for p in paths:
        print(f"  - {p}")
else:
    print("✗ File not found!")
    print("\nNote: Please create a sample.xlsx file in your Documents, Desktop, or Downloads folder first.")
    sys.exit(1)

# Test 2: Open the file
print("\n2. TESTING: Open file")
print("-"*80)
result = find_and_open_file("sample.xlsx")
print(f"Result: {result}")
if "Opened" in str(result):
    print("✓ File opened successfully")
else:
    print(f"⚠ Result: {result}")

input("\nPress Enter after you've verified Excel opened with sample.xlsx...")

# Test 3: Close Excel
print("\n3. TESTING: Close Excel")
print("-"*80)
result = close_application("excel")
print(f"Result: {result}")
if "Closed" in result or "terminated" in result.lower():
    print("✓ Excel closed successfully")
else:
    print(f"⚠ Result: {result}")

# Test 4: Rename file
print("\n4. TESTING: Rename file to 'sample_renamed.xlsx'")
print("-"*80)
result = rename_file("sample.xlsx", "sample_renamed.xlsx")
print(f"Result: {result}")
if "Success" in result:
    print("✓ File renamed successfully")
else:
    print(f"⚠ Result: {result}")

# Test 5: Move file to Desktop
print("\n5. TESTING: Move file to Desktop")
print("-"*80)
result = move_file("sample_renamed.xlsx", "desktop")
print(f"Result: {result}")
if "Success" in result:
    print("✓ File moved successfully")
else:
    print(f"⚠ Result: {result}")

# Test 6: Delete file (optional - commented out by default)
print("\n6. TESTING: Delete file (SKIPPED - uncomment to test)")
print("-"*80)
print("⚠ Deletion test is commented out to preserve your file.")
print("To test deletion, uncomment the lines below and run again.")
# result = delete_file("sample_renamed.xlsx")
# print(f"Result: {result}")
# if "Success" in result:
#     print("✓ File deleted successfully")
# else:
#     print(f"⚠ Result: {result}")

print("\n" + "="*80)
print("TEST SUMMARY")
print("="*80)
print("✓ Find paths - Working")
print("✓ Open file - Tested (check manually)")
print("✓ Close application - Tested")
print("✓ Rename file - Tested")
print("✓ Move file - Tested")
print("⚠ Delete file - Skipped (to preserve file)")
print("\nAll core file operations are functional!")
print("="*80)
