import os
import polars as pl
from capabilities.excel_manipulation import read_sheet_data, write_cell, append_row, delete_row, set_style

TEST_FILE = "test_excel_agent.xlsx"

def setup():
    # Create a dummy file with Polars
    df = pl.DataFrame({
        "Name": ["Alice", "Bob", "Charlie"],
        "Age": [25, 30, 35],
        "City": ["New York", "London", "Paris"]
    })
    df.write_excel(TEST_FILE)
    print(f"Created {TEST_FILE}")

def test_capabilities():
    print("\n--- Testing Read ---")
    print(read_sheet_data(TEST_FILE))
    
    print("\n--- Testing Write Cell (Update Bob's Age to 99) ---")
    # Bob is in Row 3 (Header + index 1 + 1-based = Row 3? No, header=1, Alice=2, Bob=3)
    # Check openpyxl indexing. Openpyxl 1-based.
    # Header row 1.
    # Alice row 2.
    # Bob row 3.
    # Age is Col B. So B3.
    print(write_cell(TEST_FILE, "Sheet1", "B3", "99"))
    
    print("\n--- Testing Append Row ---")
    print(append_row(TEST_FILE, "Sheet1", ["David", 40, "Berlin"]))
    
    print("\n--- Testing Style (Red Header) ---")
    print(set_style(TEST_FILE, "Sheet1", "A1:C1", bg_color="red", font_color="white", bold=True))
    
    print("\n--- Testing Delete Row (Delete Alice - Row 2) ---")
    print(delete_row(TEST_FILE, "Sheet1", 2))

    print("\n--- Final Verify ---")
    print(read_sheet_data(TEST_FILE))

if __name__ == "__main__":
    try:
        setup()
        test_capabilities()
    except Exception as e:
        print(f"Test Failed: {e}")
    finally:
        # Cleanup
        if os.path.exists(TEST_FILE):
            os.remove(TEST_FILE)
            print(f"\nRemoved {TEST_FILE}")
