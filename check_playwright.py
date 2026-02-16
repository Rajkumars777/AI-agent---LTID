
import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        print("Launching Chromium...")
        try:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            print("Navigating to google.com...")
            await page.goto("https://www.google.com")
            print(f"Title: {await page.title()}")
            await browser.close()
            print("Successfully launched and closed Chromium.")
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to launch/use Chromium: {e}")

if __name__ == "__main__":
    asyncio.run(run())
