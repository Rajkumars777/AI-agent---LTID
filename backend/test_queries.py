import asyncio
import os
import sys
import pandas as pd

# Ensure backend folder is in path
sys.path.append(os.path.abspath("backend"))

from agent import run_agent

async def run_queries():
    print("🚀 Starting End-to-End Agent Query Test (gendat.xlsx)\n")
    
    # 0. Setup: Create gendat.xlsx
    df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
    df.to_excel("gendat.xlsx", index=False)
    print("✅ Created 'gendat.xlsx' in current directory.")

    queries = [
        ("rename gendat.xlsx to data_backup", lambda: os.path.exists("data_backup.xlsx")),
        ("move data_backup.xlsx to Music", lambda: os.path.exists(os.path.join(os.environ["USERPROFILE"], "Music", "data_backup.xlsx"))),
        ("compress data_backup.xlsx into a zip", lambda: os.path.exists(os.path.join(os.environ["USERPROFILE"], "Music", "data_backup.zip")) or os.path.exists("data_backup.zip"))
    ]

    for i, (query, check_fn) in enumerate(queries, 1):
        print(f"\n--- Query {i}: '{query}' ---")
        try:
            result = await run_agent(query, task_id=f"test_{i}")
            steps = result.get("steps", [])
            if steps:
                print(f"Result: {steps[-1]['content']}")
            else:
                print("Result: No steps returned.")
            
            if check_fn():
                print(f"✅ VERIFIED: File state updated correctly.")
            else:
                print(f"❌ NOT VERIFIED: Physical change not detected.")
        except Exception as e:
            print(f"[Error] Query {i} failed: {e}")

    # Cleanup
    print("\n🧹 Cleaning up...")
    music_path = os.path.join(os.environ["USERPROFILE"], "Music", "data_backup.xlsx")
    zip_path = os.path.join(os.environ["USERPROFILE"], "Music", "data_backup.zip")
    try:
        if os.path.exists("gendat.xlsx"): os.remove("gendat.xlsx")
        if os.path.exists("data_backup.xlsx"): os.remove("data_backup.xlsx")
        if os.path.exists("data_backup.zip"): os.remove("data_backup.zip")
        if os.path.exists(music_path): os.remove(music_path)
        if os.path.exists(zip_path): os.remove(zip_path)
        print("✅ Cleanup complete.")
    except Exception as e:
        print(f"Cleanup error: {e}")

if __name__ == "__main__":
    asyncio.run(run_queries())
