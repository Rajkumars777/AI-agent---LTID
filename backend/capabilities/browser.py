from playwright.async_api import async_playwright

async def browse_url(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        title = await page.title()
        content = await page.content()
        await browser.close()
        return {"title": title, "content_length": len(content)}

async def screenshot_url(url: str, output_path: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        await page.screenshot(path=output_path)
        await browser.close()
        return output_path

async def click_element(url: str, selector: str):
    """Click an element on a page."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        await page.click(selector)
        # Wait for some effect or return new state
        title = await page.title()
        await browser.close()
        return f"Clicked {selector} on {title}"

async def scrape_table(url: str, table_selector: str):
    """Scrape a table into a list of dicts."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        # Basic table scraping logic (headers + rows)
        rows = await page.eval_on_selector_all(f"{table_selector} tr", """
            rows => rows.map(row => {
                const cells = row.querySelectorAll('td, th');
                return Array.from(cells).map(cell => cell.innerText);
            })
        """)
        await browser.close()
        return rows
