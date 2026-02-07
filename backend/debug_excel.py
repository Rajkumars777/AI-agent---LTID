import polars as pl
import os

FILE = "debug.xlsx"

try:
    df = pl.DataFrame({"A": [1, 2, 3]})
    df.write_excel(FILE)
    print(f"Created {FILE}")

    print("Attempt 1: read_excel(FILE)")
    try:
        data = pl.read_excel(FILE)
        print(f"Success 1: Type={type(data)}")
    except Exception as e:
        print(f"Fail 1: {e}")

    print("Attempt 2: read_excel(FILE, sheet_id=0)") # 0-based index?
    try:
        data = pl.read_excel(FILE, sheet_id=0) # Polars param might be different
        print(f"Success 2: {data}")
    except Exception as e:
        print(f"Fail 2: {e}")

    print("Attempt 3: read_excel(FILE, sheet_id=1)") # 1-based index?
    try:
        data = pl.read_excel(FILE, sheet_id=1)
        print(f"Success 3: {data}")
    except Exception as e:
        print(f"Fail 3: {e}")

    print("Attempt 4: read_excel(FILE, sheet_name='Sheet1')")
    try:
        data = pl.read_excel(FILE, sheet_name='Sheet1')
        print(f"Success 4: {data}")
    except Exception as e:
        print(f"Fail 4: {e}")

except Exception as e:
    print(f"Setup failed: {e}")
finally:
    if os.path.exists(FILE):
        os.remove(FILE)
