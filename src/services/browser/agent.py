"""
src/services/browser/agent.py
==============================
Complete browser automation using Playwright (async) + BeautifulSoup4.
Handles navigation, clicking, form filling, scraping, file downloads.
"""

import asyncio
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from bs4 import BeautifulSoup


class BrowserAgent:
    """
    Async browser automation agent.
    Features:
    - Navigate URLs
    - Click elements (CSS selectors, text, XPath)
    - Fill forms
    - Extract structured data (tables, lists, text)
    - Download files
    - Download files
    - Take screenshots
    - Handle popups/alerts
    - Connect to remote browser (CDP)
    """
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.headless = True
        self.download_path = str(Path.home() / "Downloads")
    
    # ══════════════════════════════════════════════════
    # LIFECYCLE
    # ══════════════════════════════════════════════════
    
    async def start(self, headless: bool = True, browser_name: str = "chrome"):
        """
        Starts browser using the specified browser.
        
        browser_name options:
          "brave"  - Brave Browser
          "chrome" - Google Chrome (default)
          "edge"   - Microsoft Edge
        """
        import os
        
        self.headless = headless
        self.playwright = await async_playwright().start()
        
        local_app_data = os.environ.get("LOCALAPPDATA", os.path.join(os.path.expanduser("~"), "AppData", "Local"))
        user_home = os.path.expanduser("~")
        
        name_lower = browser_name.lower().strip()
        
        # ── Brave ────────────────────────────────────────────────────
        if name_lower == "brave":
            brave_paths = [
                r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
                os.path.join(local_app_data, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
            ]
            executable_path = next((p for p in brave_paths if os.path.exists(p)), None)
            if not executable_path:
                print("[Browser] ⚠️  Brave not found, falling back to Chrome")
                name_lower = "chrome"
            else:
                user_data_dir = os.path.join(local_app_data, "BraveSoftware", "Brave-Browser", "User Data")
                print(f"[Browser] 🦁 Launching Brave: {executable_path}")
                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    executable_path=executable_path,
                    headless=headless,
                    viewport={'width': 1920, 'height': 1080},
                    accept_downloads=True,
                    args=['--start-maximized', '--no-sandbox'],
                )
        
        # ── Edge ─────────────────────────────────────────────────────
        if name_lower == "edge":
            user_data_dir = os.path.join(local_app_data, "Microsoft", "Edge", "User Data")
            print("[Browser] 🌐 Launching Microsoft Edge")
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=headless,
                channel="msedge",
                viewport={'width': 1920, 'height': 1080},
                accept_downloads=True,
                args=['--start-maximized', '--no-sandbox'],
            )
        
        # ── Chrome (default) ─────────────────────────────────────────
        if name_lower == "chrome":
            user_data_dir = os.path.join(local_app_data, "Google", "Chrome", "User Data")
            print("[Browser] 🌐 Launching Google Chrome")
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=headless,
                channel="chrome",
                viewport={'width': 1920, 'height': 1080},
                accept_downloads=True,
                args=['--start-maximized', '--no-sandbox'],
            )
        
        # In persistent context, browser is accessed via context
        self.browser = self.context.browser
        
        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = await self.context.new_page()
        
        # Set longer timeout for slow websites
        self.page.set_default_timeout(30000)  # 30 seconds
    
    async def connect(self, port: int = 9222):
        """Connects to an existing browser via CDP."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.connect_over_cdp(f"http://localhost:{port}")
        
        # In CDP mode, we often want to use the first existing page
        if self.browser.contexts:
            self.context = self.browser.contexts[0]
            if self.context.pages:
                self.page = self.context.pages[0]
            else:
                self.page = await self.context.new_page()
        else:
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()
        
        self.page.set_default_timeout(30000)
        return f"✅ Connected to browser on port {port}"
    
    async def stop(self):
        """Stops browser."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def ensure_started(self, browser_name: str = "chrome"):
        """Ensures browser is running. Pass browser_name='brave'/'chrome'/'edge'."""
        if not self.browser:
            await self.start(browser_name=browser_name)
    
    # ══════════════════════════════════════════════════
    # NAVIGATION
    # ══════════════════════════════════════════════════
    
    async def navigate(self, url: str, wait_for: str = "load") -> str:
        """
        Navigates to URL.
        
        wait_for options:
        - "load": Wait for page load event (default)
        - "domcontentloaded": Wait for DOM ready
        - "networkidle": Wait for no network requests (slower but safer)
        """
        await self.ensure_started()
        
        try:
            # Add https:// if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            await self.page.goto(url, wait_until=wait_for)
            return f"✅ Navigated to: {url}"
        except Exception as e:
            return f"❌ Navigation failed: {e}"
    
    async def go_back(self) -> str:
        """Goes back in history."""
        await self.ensure_started()
        try:
            await self.page.go_back()
            return "✅ Went back"
        except Exception as e:
            return f"❌ Go back failed: {e}"
    
    async def go_forward(self) -> str:
        """Goes forward in history."""
        await self.ensure_started()
        try:
            await self.page.go_forward()
            return "✅ Went forward"
        except Exception as e:
            return f"❌ Go forward failed: {e}"
    
    async def refresh(self) -> str:
        """Refreshes page."""
        await self.ensure_started()
        try:
            await self.page.reload()
            return "✅ Page refreshed"
        except Exception as e:
            return f"❌ Refresh failed: {e}"
    
    async def get_current_url(self) -> str:
        """Returns current URL."""
        await self.ensure_started()
        return self.page.url
    
    # ══════════════════════════════════════════════════
    # CLICKING & INTERACTION
    # ══════════════════════════════════════════════════
    
    async def click(
        self,
        selector: str,
        by: str = "css",
        wait_time: float = 5.0
    ) -> str:
        """
        Clicks element.
        
        by options:
        - "css": CSS selector (default) e.g., "#submit-btn"
        - "text": Click by visible text e.g., "Login"
        - "xpath": XPath selector
        """
        await self.ensure_started()
        
        try:
            if by == "css":
                await self.page.click(selector, timeout=wait_time * 1000)
            elif by == "text":
                await self.page.click(f"text={selector}", timeout=wait_time * 1000)
            elif by == "xpath":
                await self.page.click(f"xpath={selector}", timeout=wait_time * 1000)
            else:
                return f"❌ Invalid selector type: {by}"
            
            return f"✅ Clicked: {selector}"
        except Exception as e:
            return f"❌ Click failed on '{selector}': {e}"
    
    async def hover(self, selector: str) -> str:
        """Hovers over element."""
        await self.ensure_started()
        try:
            await self.page.hover(selector)
            return f"✅ Hovered: {selector}"
        except Exception as e:
            return f"❌ Hover failed: {e}"
    
    # ══════════════════════════════════════════════════
    # FORM FILLING
    # ══════════════════════════════════════════════════
    
    async def fill_input(self, selector: str, value: str) -> str:
        """Fills input field."""
        await self.ensure_started()
        try:
            await self.page.fill(selector, value)
            return f"✅ Filled '{selector}' with: {value}"
        except Exception as e:
            return f"❌ Fill failed: {e}"
    
    async def fill_form(self, form_data: Dict[str, str]) -> str:
        """
        Fills multiple form fields.
        
        form_data: {"#email": "test@example.com", "#password": "secret123"}
        """
        await self.ensure_started()
        
        results = []
        for selector, value in form_data.items():
            result = await self.fill_input(selector, value)
            results.append(result)
        
        success_count = sum(1 for r in results if "✅" in r)
        return f"✅ Filled {success_count}/{len(form_data)} fields"
    
    async def select_dropdown(self, selector: str, value: str) -> str:
        """Selects dropdown option by value or label."""
        await self.ensure_started()
        try:
            await self.page.select_option(selector, value)
            return f"✅ Selected '{value}' in dropdown"
        except Exception as e:
            return f"❌ Dropdown selection failed: {e}"
    
    async def check_checkbox(self, selector: str, checked: bool = True) -> str:
        """Checks or unchecks checkbox."""
        await self.ensure_started()
        try:
            if checked:
                await self.page.check(selector)
                return f"✅ Checked: {selector}"
            else:
                await self.page.uncheck(selector)
                return f"✅ Unchecked: {selector}"
        except Exception as e:
            return f"❌ Checkbox operation failed: {e}"
    
    async def upload_file(self, selector: str, file_path: str) -> str:
        """Uploads file to input field."""
        await self.ensure_started()
        try:
            await self.page.set_input_files(selector, file_path)
            return f"✅ Uploaded: {file_path}"
        except Exception as e:
            return f"❌ Upload failed: {e}"
    
    # ══════════════════════════════════════════════════
    # DATA EXTRACTION (BeautifulSoup)
    # ══════════════════════════════════════════════════
    
    async def extract_text(self, selector: str) -> str:
        """Extracts text from element."""
        await self.ensure_started()
        try:
            element = await self.page.query_selector(selector)
            if element:
                text = await element.inner_text()
                return text
            return ""
        except Exception as e:
            return f"Error: {e}"
    
    async def extract_table(self, selector: str = "table") -> List[List[str]]:
        """
        Extracts table data into 2D list.
        Returns: [[header1, header2], [row1col1, row1col2], ...]
        """
        await self.ensure_started()
        
        try:
            # Get page HTML
            html = await self.page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find table
            table = soup.select_one(selector)
            if not table:
                return []
            
            # Extract headers
            headers = [th.get_text(strip=True) for th in table.select('thead th')]
            if not headers:
                # Fallback: first row as headers
                first_row = table.select_one('tr')
                if first_row:
                    headers = [td.get_text(strip=True) for td in first_row.select('th, td')]
            
            # Extract rows
            rows = []
            for tr in table.select('tbody tr, tr'):
                cells = [td.get_text(strip=True) for td in tr.select('td')]
                if cells:  # Skip empty rows
                    rows.append(cells)
            
            # Combine headers + rows
            if headers:
                return [headers] + rows
            return rows
            
        except Exception as e:
            print(f"[Browser] Table extraction error: {e}")
            return []
    
    async def extract_links(self, selector: str = "a") -> List[Dict[str, str]]:
        """
        Extracts all links.
        Returns: [{"text": "Link text", "href": "https://..."}]
        """
        await self.ensure_started()
        
        try:
            html = await self.page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            links = []
            for a in soup.select(selector):
                href = a.get('href', '')
                text = a.get_text(strip=True)
                if href:  # Skip empty hrefs
                    links.append({"text": text, "href": href})
            
            return links
        except Exception as e:
            print(f"[Browser] Link extraction error: {e}")
            return []
    
    async def extract_structured_data(self, css_map: Dict[str, str]) -> Dict[str, str]:
        """
        Extracts structured data using CSS selector mapping.
        
        Example:
            css_map = {
                "title": "h1.product-title",
                "price": "span.price",
                "description": "div.description"
            }
        
        Returns: {"title": "Product Name", "price": "$99.99", ...}
        """
        await self.ensure_started()
        
        result = {}
        for key, selector in css_map.items():
            try:
                text = await self.extract_text(selector)
                result[key] = text
            except:
                result[key] = ""
        
        return result
    
    # ══════════════════════════════════════════════════
    # FILE DOWNLOADS
    # ══════════════════════════════════════════════════
    
    async def download_file(
        self,
        trigger_selector: str,
        save_as: Optional[str] = None
    ) -> str:
        """
        Downloads file by clicking download link/button.
        
        Args:
            trigger_selector: CSS selector of download button/link
            save_as: Optional custom filename
        """
        await self.ensure_started()
        
        try:
            # Start waiting for download before clicking
            async with self.page.expect_download() as download_info:
                await self.page.click(trigger_selector)
            
            download = await download_info.value
            
            # Save file
            if save_as:
                filepath = str(Path(self.download_path) / save_as)
            else:
                filepath = str(Path(self.download_path) / download.suggested_filename)
            
            await download.save_as(filepath)
            
            return f"✅ Downloaded: {filepath}"
        except Exception as e:
            return f"❌ Download failed: {e}"
    
    # ══════════════════════════════════════════════════
    # SCREENSHOTS
    # ══════════════════════════════════════════════════
    
    async def screenshot(
        self,
        path: Optional[str] = None,
        full_page: bool = False
    ) -> str:
        """
        Takes screenshot.
        
        Args:
            path: File path to save (PNG format)
            full_page: Capture entire scrollable page (default: visible area only)
        """
        await self.ensure_started()
        
        try:
            if not path:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = f"screenshot_{timestamp}.png"
            
            await self.page.screenshot(path=path, full_page=full_page)
            return f"✅ Screenshot saved: {path}"
        except Exception as e:
            return f"❌ Screenshot failed: {e}"
    
    async def screenshot_element(self, selector: str, path: str) -> str:
        """Takes screenshot of specific element."""
        await self.ensure_started()
        
        try:
            element = await self.page.query_selector(selector)
            if element:
                await element.screenshot(path=path)
                return f"✅ Element screenshot saved: {path}"
            return f"❌ Element not found: {selector}"
        except Exception as e:
            return f"❌ Screenshot failed: {e}"
    
    # ══════════════════════════════════════════════════
    # WAITING & SCROLLING
    # ══════════════════════════════════════════════════
    
    async def wait_for_selector(self, selector: str, timeout: float = 10.0) -> str:
        """Waits for element to appear."""
        await self.ensure_started()
        try:
            await self.page.wait_for_selector(selector, timeout=timeout * 1000)
            return f"✅ Element appeared: {selector}"
        except Exception as e:
            return f"❌ Wait timeout for '{selector}': {e}"
    
    async def wait_for_text(self, text: str, timeout: float = 10.0) -> str:
        """Waits for text to appear on page."""
        await self.ensure_started()
        try:
            await self.page.wait_for_selector(f"text={text}", timeout=timeout * 1000)
            return f"✅ Text appeared: '{text}'"
        except Exception as e:
            return f"❌ Wait timeout for text '{text}': {e}"
    
    async def scroll_to_bottom(self) -> str:
        """Scrolls to bottom of page."""
        await self.ensure_started()
        try:
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            return "✅ Scrolled to bottom"
        except Exception as e:
            return f"❌ Scroll failed: {e}"
    
    async def scroll_to_element(self, selector: str) -> str:
        """Scrolls element into view."""
        await self.ensure_started()
        try:
            element = await self.page.query_selector(selector)
            if element:
                await element.scroll_into_view_if_needed()
                return f"✅ Scrolled to: {selector}"
            return f"❌ Element not found: {selector}"
        except Exception as e:
            return f"❌ Scroll failed: {e}"
    
    # ══════════════════════════════════════════════════
    # JAVASCRIPT EXECUTION
    # ══════════════════════════════════════════════════
    
    async def execute_js(self, script: str) -> Any:
        """Executes JavaScript on page."""
        await self.ensure_started()
        try:
            result = await self.page.evaluate(script)
            return result
        except Exception as e:
            return f"Error: {e}"
    
    async def get_page_title(self) -> str:
        """Gets page title."""
        await self.ensure_started()
        return await self.page.title()
    
    async def get_page_html(self) -> str:
        """Gets full page HTML."""
        await self.ensure_started()
        return await self.page.content()

    async def login_with_credentials(
        self,
        username_selector: str,
        password_selector: str,
        submit_selector: str,
        site_name: str
    ):
        """
        Performs login with user-provided credentials.
        
        Args:
            username_selector: CSS selector for username field
            password_selector: CSS selector for password field
            submit_selector: CSS selector for submit button
            site_name: Display name for credential request
        """
        from src.core.security.credential_handler import credential_handler
        
        # Request credentials from user
        creds = credential_handler.request_credentials(
            site=site_name,
            fields=["username", "password"]
        )
        
        if not creds:
            return "❌ User cancelled credential request"
        
        # Fill form
        await self.fill_input(username_selector, creds["username"])
        await asyncio.sleep(0.5)
        
        await self.fill_input(password_selector, creds["password"])
        await asyncio.sleep(0.5)
        
        # Submit
        await self.click(submit_selector, by="css")
        await asyncio.sleep(2)
        
        return f"✅ Logged in to {site_name}"

    async def intelligent_login(self, site_name: str):
        """
        Intelligently finds and fills login form.
        Uses common patterns + vision AI fallback.
        """
        from src.core.security.credential_handler import credential_handler
        
        # Request credentials
        creds = credential_handler.request_credentials(site_name)
        if not creds:
            return "❌ Login cancelled"
        
        # Common login selectors
        username_selectors = [
            "input[type='email']",
            "input[name='username']",
            "input[name='email']",
            "#username",
            "#email",
        ]
        
        password_selectors = [
            "input[type='password']",
            "#password",
            "input[name='password']",
        ]
        
        submit_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Sign in')",
            "button:has-text('Login')",
        ]
        
        # Try to fill form - use list search
        try:
            # Find username field
            username_field = None
            for selector in username_selectors:
                try:
                    # Check if element exists before filling
                    exists = await self.page.query_selector(selector)
                    if exists:
                        await self.fill_input(selector, creds["username"])
                        username_field = selector
                        break
                except: continue
            
            if not username_field:
                raise Exception("Could not find username field")
            
            await asyncio.sleep(0.5)
            
            # Find password field
            password_field = None
            for selector in password_selectors:
                try:
                    exists = await self.page.query_selector(selector)
                    if exists:
                        await self.fill_input(selector, creds["password"])
                        password_field = selector
                        break
                except: continue
            
            if not password_field:
                raise Exception("Could not find password field")
            
            await asyncio.sleep(0.5)
            
            # Find and click submit
            for selector in submit_selectors:
                try:
                    exists = await self.page.query_selector(selector)
                    if exists:
                        await self.click(selector, by="css")
                        await asyncio.sleep(3)
                        return f"✅ Logged in to {site_name}"
                except: continue
            
            raise Exception("Could not find submit button")
            
        except Exception as e:
            return f"❌ Login failed: {e}"


# ─────────────────────────────────────────────────────
# GLOBAL INSTANCE
# ─────────────────────────────────────────────────────

browser_agent = BrowserAgent()
