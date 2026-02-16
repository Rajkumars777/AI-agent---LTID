
import sys
import os
import asyncio

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from capabilities.browser import orchestrate_web_task

async def test_nikkei():
    print("Testing Nikkei Workflow...")
    # Pass the actual URL so the initial page.goto succeeds
    result = await orchestrate_web_task("https://indexes.nikkei.co.jp/en/nkave/", "get_nikkei_closing")
    print("Status:", result.get("status"))
    print("Data:", result.get("data"))
    if result.get("file"):
         print("File created:", result.get("file"))

if __name__ == "__main__":
    asyncio.run(test_nikkei())
