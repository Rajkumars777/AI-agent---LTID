
import sys
import os
import asyncio

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from capabilities.browser import orchestrate_web_task

async def test_scrape():
    print("Testing Scrape Table...")
    result = await orchestrate_web_task("https://datatables.net/examples/basic_init/zero_configuration.html", "scrape_table")
    print("Result keys:", result.keys())
    print("Status:", result.get("status"))
    print("Data length:", len(result.get("data", [])))

async def test_read():
    print("\nTesting Read Page...")
    result = await orchestrate_web_task("https://example.com", "read_page")
    print("Status:", result.get("status"))
    print("Title:", result.get("data", {}).get("title"))

if __name__ == "__main__":
    asyncio.run(test_scrape())
    asyncio.run(test_read())
