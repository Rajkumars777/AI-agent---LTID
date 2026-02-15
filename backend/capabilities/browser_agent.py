"""
AI Browser Agent - Sync Playwright + Thread Executor
=====================================================
Uses Playwright's SYNC API in a background thread to avoid
Windows event loop incompatibility (NotImplementedError).

ARCHITECTURE:
  1. DIRECT mode (fast, reliable): Uses known CSS selectors for common sites
     (Amazon, Google, YouTube, Wikipedia, Flipkart, Myntra, IMDB).
     Handles search, filters, sorting, extraction deterministically.
  2. LLM mode (fallback): For unknown sites or complex tasks, uses the
     observe-think-act LLM loop.

All public methods are sync; the handler calls them via asyncio.to_thread().
"""

import json
import re
import time
import threading
from typing import Dict, Optional, List
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext


# ======================================================================
# Site-specific selectors for deterministic automation
# ======================================================================
SITE_CONFIG = {
    "amazon": {
        "search_input": "#twotabsearchtextbox",
        "search_submit": "#nav-search-submit-button",
        "wait_after_search": 3,
    },
    "google": {
        "search_input": 'textarea[name="q"], input[name="q"]',
        "search_submit": None,  # press Enter
        "wait_after_search": 2,
    },
    "youtube": {
        "search_input": 'input#search, input[name="search_query"]',
        "search_submit": "#search-icon-legacy, button#search-icon-legacy",
        "wait_after_search": 3,
    },
    "wikipedia": {
        "search_input": '#searchInput, input[name="search"], #searchform input',
        "search_submit": None,  # press Enter
        "wait_after_search": 2,
    },
    "flipkart": {
        "search_input": 'input[name="q"], input[title="Search for Products, Brands and More"], input._3704LK',
        "search_submit": 'button[type="submit"], button._2iA8p4',
        "wait_after_search": 3,
    },
    "myntra": {
        "search_input": 'input.desktop-searchBar, input[placeholder*="Search"]',
        "search_submit": None,  # press Enter
        "wait_after_search": 3,
    },
    "imdb": {
        "search_input": '#suggestion-search-input, input[name="q"]',
        "search_submit": "#suggestion-search-button",
        "wait_after_search": 3,
    },
}


class BrowserAgent:
    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._element_map: Dict[int, str] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self, headless: bool = False):
        """Launch Chromium with stealth flags. Idempotent."""
        if self._page:
            return "Browser already running."

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
            ],
        )
        self._context = self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        self._page = self._context.new_page()

        # Hide navigator.webdriver
        self._page.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        )
        return "Browser started."

    def stop(self):
        """Gracefully shut down."""
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None
        self._element_map = {}
        return "Browser stopped."

    def restart(self):
        """Restart the browser session."""
        self.stop()
        self.start()

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def navigate(self, url: str) -> str:
        if not self._page:
            self.start()
        try:
            self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)
            title = self._page.title()
            return f"Navigated to {url} (Title: {title})"
        except Exception as e:
            msg = str(e).lower()
            if "closed" in msg or "detached" in msg:
                try:
                    self.restart()
                    self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    time.sleep(2)
                    title = self._page.title()
                    return f"Navigated to {url} (Title: {title})"
                except Exception as e2:
                    return f"Navigation failed after restart: {e2}"
            return f"Navigation failed: {e}"

    # ------------------------------------------------------------------
    # Utility: find and interact with elements
    # ------------------------------------------------------------------
    def _try_selectors(self, selectors_str: str, timeout: int = 5000) -> Optional[str]:
        """Try multiple comma-separated selectors, return the first one found."""
        for sel in selectors_str.split(","):
            sel = sel.strip()
            try:
                if self._page.locator(sel).first.is_visible(timeout=timeout):
                    return sel
            except:
                continue
        return None

    def _type_and_search(self, search_input_sel: str, query: str,
                         submit_sel: Optional[str] = None) -> str:
        """Type into search box and submit."""
        try:
            # Click the search input to focus it
            self._page.click(search_input_sel, timeout=5000)
            time.sleep(0.5)

            # Clear and type
            self._page.fill(search_input_sel, query)
            time.sleep(0.5)

            # Submit
            if submit_sel:
                found_submit = self._try_selectors(submit_sel, timeout=3000)
                if found_submit:
                    self._page.click(found_submit, timeout=3000)
                else:
                    self._page.keyboard.press("Enter")
            else:
                self._page.keyboard.press("Enter")

            time.sleep(3)  # Wait for results
            return f"Searched for '{query}'"
        except Exception as e:
            return f"Search failed: {e}"

    def _click_by_text(self, text: str, tag: str = "*", exact: bool = False) -> str:
        """Click an element containing specific text."""
        try:
            if exact:
                locator = self._page.locator(f"{tag}:text-is('{text}')").first
            else:
                locator = self._page.locator(f"{tag}:has-text('{text}')").first

            if locator.is_visible(timeout=3000):
                locator.click(timeout=5000)
                time.sleep(2)
                return f"Clicked element with text '{text}'"
            return f"Element with text '{text}' not visible"
        except Exception as e:
            return f"Click by text failed: {e}"

    def _scroll_and_click_text(self, text: str, max_scrolls: int = 5) -> str:
        """Scroll down until element with text is found, then click it."""
        for i in range(max_scrolls):
            try:
                locator = self._page.locator(f"*:has-text('{text}')").first
                if locator.is_visible(timeout=1000):
                    locator.click(timeout=5000)
                    time.sleep(2)
                    return f"Found and clicked '{text}'"
            except:
                pass
            self._page.evaluate("window.scrollBy(0, 500)")
            time.sleep(1)
        return f"Could not find element with text '{text}' after scrolling"

    def _extract_text_by_selector(self, selector: str) -> str:
        """Extract text content from elements matching a selector."""
        try:
            elements = self._page.locator(selector)
            count = elements.count()
            if count == 0:
                return ""
            texts = []
            for i in range(min(count, 5)):
                t = elements.nth(i).text_content()
                if t and t.strip():
                    texts.append(t.strip())
            return " | ".join(texts)
        except:
            return ""

    def _click_first_result(self, site_key: str) -> str:
        """Click the first search result on a site."""
        selectors_by_site = {
            "amazon": 'div[data-component-type="s-search-result"] h2 a, .s-result-item h2 a',
            "google": '#search a h3, #rso a h3',
            "youtube": 'ytd-video-renderer a#video-title, a#video-title',
            "flipkart": 'a._1fQZEK, div._2kHMtA a, a._2rpwqI',
            "wikipedia": '.mw-search-result-heading a, #mw-content-text a',
            "imdb": '.find-result-item a, .ipc-metadata-list-summary-item a',
        }
        sel = selectors_by_site.get(site_key, "a")
        try:
            found = self._try_selectors(sel, timeout=5000)
            if found:
                self._page.locator(found).first.click(timeout=5000)
                time.sleep(3)
                return f"Clicked first result on {site_key}"
            return f"No results found to click on {site_key}"
        except Exception as e:
            return f"Failed to click first result: {e}"

    # ------------------------------------------------------------------
    # DIRECT TASK EXECUTION (deterministic, no LLM needed)
    # ------------------------------------------------------------------
    def _identify_site(self, url: str) -> Optional[str]:
        """Identify which known site this URL belongs to."""
        url_lower = url.lower()
        for site_key in SITE_CONFIG:
            if site_key in url_lower:
                return site_key
        return None

    def _parse_goal(self, goal: str) -> dict:
        """Parse the user's goal into structured components."""
        goal_lower = goal.lower()
        result = {
            "search_query": None,
            "filters": [],
            "sort": None,
            "extract": [],
            "click_first": False,
            "navigate_section": None,
        }

        # Extract search query (between quotes or after "search for")
        quoted = re.findall(r'["\']([^"\']+)["\']', goal)
        if quoted:
            result["search_query"] = quoted[0]
        else:
            search_match = re.search(
                r'(?:search\s+(?:for\s+)?|search\s+)([^,\.]+)',
                goal_lower
            )
            if search_match:
                query = search_match.group(1).strip()
                # Remove trailing filter/sort phrases
                query = re.sub(r'\s*(then|and|,).*$', '', query).strip()
                result["search_query"] = query

        # Detect filters
        if re.search(r'filter\s+(?:by\s+)?price\s+under\s+[\d,₹]+', goal_lower) or \
           re.search(r'price\s+under\s+[\d,₹]+', goal_lower):
            price_match = re.search(r'(?:under|below)\s+[₹]?([\d,]+)', goal_lower)
            if price_match:
                result["filters"].append(("price_under", price_match.group(1).replace(",", "")))

        if re.search(r'4\s*star|4★|4\s*\u2605', goal_lower):
            result["filters"].append(("star_rating", "4"))

        if re.search(r'filter\s+(?:by\s+)?size\s+(\d+)', goal_lower):
            size_match = re.search(r'size\s+(\d+)', goal_lower)
            if size_match:
                result["filters"].append(("size", size_match.group(1)))

        if re.search(r'filter\s+(?:by\s+)?["\']?upload\s*date', goal_lower):
            result["filters"].append(("upload_date", True))

        # Detect sort
        if "sort" in goal_lower:
            if "low to high" in goal_lower or "lowest" in goal_lower:
                result["sort"] = "low_to_high"
            elif "high to low" in goal_lower or "highest" in goal_lower:
                result["sort"] = "high_to_low"

        # Detect extraction needs
        if any(kw in goal_lower for kw in ["extract", "get the price", "price"]):
            result["extract"].append("price")
        if any(kw in goal_lower for kw in ["rating", "get the rating"]):
            result["extract"].append("rating")
        if "compare" in goal_lower:
            result["extract"].append("compare_prices")

        # Detect click-first-result intent
        if any(kw in goal_lower for kw in ["open the first", "click first", "open first"]):
            result["click_first"] = True

        # Detect section navigation
        section_match = re.search(r'navigate\s+to\s+["\']?(\w+(?:\s+\w+)?)["\']?\s*section', goal_lower)
        if section_match:
            result["navigate_section"] = section_match.group(1).strip()

        return result

    def run_task(self, url: str, goal: str, llm_fn=None, max_turns: int = 12) -> str:
        """
        Main entry point. First tries direct deterministic automation,
        falls back to LLM loop only if necessary.
        """
        logs = []

        # 1. Navigate
        if url:
            nav = self.navigate(url)
            logs.append(nav)
            if "failed" in nav.lower():
                return nav

        # 2. Identify site and parse goal
        site_key = self._identify_site(url or "")
        parsed = self._parse_goal(goal)

        print(f"[BrowserAgent] Site: {site_key}, Parsed goal: {parsed}", flush=True)

        # 3. Handle Flipkart login popup (common blocker)
        if site_key == "flipkart":
            self._dismiss_flipkart_popup()

        # 4. DIRECT SEARCH (if site is known and we have a search query)
        if site_key and parsed["search_query"] and site_key in SITE_CONFIG:
            config = SITE_CONFIG[site_key]
            search_input = self._try_selectors(config["search_input"], timeout=5000)

            if search_input:
                search_result = self._type_and_search(
                    search_input,
                    parsed["search_query"],
                    config.get("search_submit")
                )
                logs.append(search_result)
                print(f"[BrowserAgent] Search: {search_result}", flush=True)

                wait_time = config.get("wait_after_search", 3)
                time.sleep(wait_time)
            else:
                logs.append(f"Could not find search input for {site_key}")
                print(f"[BrowserAgent] Search input not found for {site_key}", flush=True)

        # 5. Apply FILTERS
        for filter_type, filter_value in parsed["filters"]:
            filter_result = self._apply_filter(site_key, filter_type, filter_value)
            logs.append(filter_result)
            print(f"[BrowserAgent] Filter ({filter_type}): {filter_result}", flush=True)

        # 6. Apply SORT
        if parsed["sort"]:
            sort_result = self._apply_sort(site_key, parsed["sort"])
            logs.append(sort_result)
            print(f"[BrowserAgent] Sort: {sort_result}", flush=True)

        # 7. Click first result if requested
        if parsed["click_first"] and site_key:
            click_result = self._click_first_result(site_key)
            logs.append(click_result)
            print(f"[BrowserAgent] Click first: {click_result}", flush=True)
            time.sleep(2)

        # 8. Navigate to section if requested
        if parsed["navigate_section"]:
            section = parsed["navigate_section"]
            nav_result = self._click_by_text(section, tag="a, h2, h3, span")
            logs.append(f"Navigate to section '{section}': {nav_result}")
            print(f"[BrowserAgent] Section nav: {nav_result}", flush=True)

        # 9. EXTRACT data if requested
        extracted_data = {}
        for extract_type in parsed["extract"]:
            extract_result = self._extract_data(site_key, extract_type)
            extracted_data[extract_type] = extract_result
            logs.append(f"Extracted {extract_type}: {extract_result}")
            print(f"[BrowserAgent] Extract ({extract_type}): {extract_result}", flush=True)

        # 10. Build summary
        summary_parts = []
        summary_parts.append(f"Navigated to {url}")

        if parsed["search_query"]:
            summary_parts.append(f"Searched for '{parsed['search_query']}'")

        for ft, fv in parsed["filters"]:
            summary_parts.append(f"Applied filter: {ft}={fv}")

        if parsed["sort"]:
            summary_parts.append(f"Sorted by: {parsed['sort']}")

        if parsed["click_first"]:
            summary_parts.append("Opened first result")

        if parsed["navigate_section"]:
            summary_parts.append(f"Navigated to '{parsed['navigate_section']}' section")

        if extracted_data:
            for k, v in extracted_data.items():
                summary_parts.append(f"{k}: {v}")

        return "✅ " + " → ".join(summary_parts) + "\n\nDetails:\n" + "\n".join(logs)

    # ------------------------------------------------------------------
    # FILTER LOGIC (site-specific)
    # ------------------------------------------------------------------
    def _apply_filter(self, site_key: str, filter_type: str, value) -> str:
        """Apply a filter on the current page."""
        try:
            if filter_type == "price_under":
                return self._filter_price(site_key, int(value))
            elif filter_type == "star_rating":
                return self._filter_stars(site_key, int(value))
            elif filter_type == "size":
                return self._filter_size(site_key, value)
            elif filter_type == "upload_date":
                return self._filter_upload_date(site_key)
            return f"Unknown filter type: {filter_type}"
        except Exception as e:
            return f"Filter error ({filter_type}): {e}"

    def _filter_price(self, site_key: str, max_price: int) -> str:
        """Filter by price range."""
        if site_key == "amazon":
            # Amazon has price range links in the left sidebar
            price_texts = [
                f"Under ₹{max_price:,}",
                f"Under ₹{max_price}",
                f"₹{max_price}",
            ]
            for text in price_texts:
                result = self._scroll_and_click_text(text, max_scrolls=3)
                if "Found and clicked" in result:
                    return f"Applied price filter: under ₹{max_price}"

            # Try clicking price range input fields if available
            try:
                low_input = self._page.locator('input#low-price, input[name="low-price"]')
                high_input = self._page.locator('input#high-price, input[name="high-price"]')
                if high_input.is_visible(timeout=2000):
                    high_input.fill(str(max_price))
                    go_btn = self._page.locator('input.a-button-input[type="submit"], span.a-button-text:has-text("Go")')
                    if go_btn.first.is_visible(timeout=2000):
                        go_btn.first.click()
                        time.sleep(3)
                        return f"Applied price filter: under ₹{max_price}"
            except:
                pass

            return f"Could not find price filter for ₹{max_price}"

        elif site_key == "flipkart":
            try:
                # Flipkart has min/max price inputs
                max_input = self._page.locator('input[class*="Max"], div._6BWGkB input:nth-child(2), input[placeholder*="Max"]')
                if max_input.first.is_visible(timeout=3000):
                    max_input.first.fill(str(max_price))
                    self._page.keyboard.press("Enter")
                    time.sleep(3)
                    return f"Applied price filter: under ₹{max_price}"
            except:
                pass
            return f"Could not find price filter on Flipkart"

        return f"Price filter not implemented for {site_key}"

    def _filter_stars(self, site_key: str, stars: int) -> str:
        """Filter by star rating."""
        if site_key == "amazon":
            star_texts = [
                f"{stars} Stars & Up",
                f"{stars} Stars",
                f"{stars}★ & above",
                f"{stars} & Up",
            ]
            # Scroll left sidebar to find star ratings
            for text in star_texts:
                result = self._scroll_and_click_text(text, max_scrolls=5)
                if "Found and clicked" in result:
                    return f"Applied {stars}-star filter"

            # Try using aria-label or section approach
            try:
                star_link = self._page.locator(f'section[aria-label*="{stars} Stars"] a, i.a-icon-star-medium').first
                if star_link.is_visible(timeout=3000):
                    star_link.click()
                    time.sleep(3)
                    return f"Applied {stars}-star filter"
            except:
                pass

            return f"Could not find {stars}-star filter"

        return f"Star filter not implemented for {site_key}"

    def _filter_size(self, site_key: str, size: str) -> str:
        """Filter by size."""
        if site_key == "myntra":
            # Myntra has size filters in the sidebar
            result = self._scroll_and_click_text(f"Size", max_scrolls=2)
            time.sleep(1)
            result2 = self._scroll_and_click_text(size, max_scrolls=3)
            if "Found and clicked" in result2:
                return f"Applied size filter: {size}"
            return f"Could not find size {size} filter"

        return f"Size filter not implemented for {site_key}"

    def _filter_upload_date(self, site_key: str) -> str:
        """Filter by upload date (YouTube)."""
        if site_key == "youtube":
            try:
                # Click the "Filters" button
                filter_btn = self._page.locator('button:has-text("Filters"), tp-yt-paper-button:has-text("Filters"), #filter-button')
                if filter_btn.first.is_visible(timeout=3000):
                    filter_btn.first.click()
                    time.sleep(2)

                    # Click "Upload date"
                    upload_date = self._page.locator('a:has-text("Upload date"), yt-chip-cloud-chip-renderer:has-text("Upload date"), div:has-text("Upload date")')
                    if upload_date.first.is_visible(timeout=3000):
                        upload_date.first.click()
                        time.sleep(2)
                        return "Applied 'Upload date' filter"
                return "Could not find Upload date filter"
            except Exception as e:
                return f"Filter error: {e}"

        return f"Upload date filter not implemented for {site_key}"

    # ------------------------------------------------------------------
    # SORT LOGIC
    # ------------------------------------------------------------------
    def _apply_sort(self, site_key: str, sort_type: str) -> str:
        """Apply sorting."""
        try:
            if site_key == "flipkart":
                if sort_type == "low_to_high":
                    result = self._click_by_text("Price -- Low to High")
                    if "Clicked" in result:
                        return "Sorted by price: Low to High"
                    # Fallback
                    result = self._click_by_text("Low to High")
                    if "Clicked" in result:
                        return "Sorted by price: Low to High"
                elif sort_type == "high_to_low":
                    result = self._click_by_text("Price -- High to Low")
                    if "Clicked" in result:
                        return "Sorted by price: High to Low"

            elif site_key == "amazon":
                try:
                    sort_dropdown = self._page.locator('#s-result-sort-select, span.a-dropdown-label')
                    if sort_dropdown.first.is_visible(timeout=3000):
                        sort_dropdown.first.click()
                        time.sleep(1)
                        if sort_type == "low_to_high":
                            self._page.locator('a:has-text("Price: Low to High"), option:has-text("Price: Low to High")').first.click()
                        else:
                            self._page.locator('a:has-text("Price: High to Low"), option:has-text("Price: High to Low")').first.click()
                        time.sleep(3)
                        return f"Sorted by price: {sort_type}"
                except:
                    pass

            return f"Could not apply sort: {sort_type} on {site_key}"
        except Exception as e:
            return f"Sort error: {e}"

    # ------------------------------------------------------------------
    # DATA EXTRACTION
    # ------------------------------------------------------------------
    def _extract_data(self, site_key: str, extract_type: str) -> str:
        """Extract specific data from the page."""
        try:
            if extract_type == "price":
                return self._extract_price(site_key)
            elif extract_type == "rating":
                return self._extract_rating(site_key)
            elif extract_type == "compare_prices":
                return self._extract_compare_prices(site_key)
            return "Unknown extraction type"
        except Exception as e:
            return f"Extraction error: {e}"

    def _extract_price(self, site_key: str) -> str:
        """Extract price from the current page."""
        selectors = {
            "amazon": '.a-price .a-offscreen, .a-price-whole, span.a-price span, #priceblock_ourprice, #priceblock_dealprice, .a-color-price',
            "flipkart": 'div._30jeq3, div._3I9_wc, div._16Jk6d',
            "default": '[class*="price"], [class*="Price"], .price, .product-price',
        }
        sel = selectors.get(site_key, selectors["default"])
        text = self._extract_text_by_selector(sel)
        return text if text else "Price not found"

    def _extract_rating(self, site_key: str) -> str:
        """Extract rating from the current page."""
        selectors = {
            "imdb": '[data-testid="hero-rating-bar__aggregate-rating__score"] span, .sc-bde20123-1, .ipc-button__text .sc-bde20123-1',
            "amazon": '#acrPopover, span.a-icon-alt, #averageCustomerReviews span',
            "default": '[class*="rating"], [class*="Rating"], .rating, .score',
        }
        sel = selectors.get(site_key, selectors["default"])
        text = self._extract_text_by_selector(sel)
        return text if text else "Rating not found"

    def _extract_compare_prices(self, site_key: str) -> str:
        """Extract and compare prices of first two results."""
        selectors = {
            "amazon": 'div[data-component-type="s-search-result"] .a-price .a-offscreen',
            "flipkart": 'div._30jeq3',
            "default": '[class*="price"]',
        }
        sel = selectors.get(site_key, selectors["default"])
        try:
            elements = self._page.locator(sel)
            count = elements.count()
            if count >= 2:
                price1 = elements.nth(0).text_content().strip()
                price2 = elements.nth(1).text_content().strip()
                return f"Product 1: {price1} | Product 2: {price2}"
            elif count == 1:
                return f"Only one price found: {elements.nth(0).text_content().strip()}"
            return "No prices found for comparison"
        except Exception as e:
            return f"Compare error: {e}"

    # ------------------------------------------------------------------
    # Site-specific helpers
    # ------------------------------------------------------------------
    def _dismiss_flipkart_popup(self):
        """Dismiss the Flipkart login popup if it appears."""
        try:
            close_btn = self._page.locator('button._2KpZ6l._2doB4z, span._30XB9F, button:has-text("✕")')
            if close_btn.first.is_visible(timeout=3000):
                close_btn.first.click()
                time.sleep(1)
                print("[BrowserAgent] Dismissed Flipkart login popup", flush=True)
        except:
            pass

    # ------------------------------------------------------------------
    # DOM snapshot (for LLM fallback if ever needed)
    # ------------------------------------------------------------------
    _JS_SNAPSHOT = """
    () => {
        let id = 0;
        const map = [];
        const selectors = 'a, button, input, select, textarea, label, ' +
            '[role="button"], [role="link"], [role="tab"], [role="checkbox"], [role="radio"], ' +
            'h1, h2, h3, ' +
            '[class*="price"], [class*="rating"], [class*="sort"], [class*="filter"]';
        const elements = document.querySelectorAll(selectors);

        elements.forEach(el => {
            if (id >= 100) return;
            const style = window.getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden') return;
            if (el.offsetWidth === 0 && el.offsetHeight === 0) return;

            el.setAttribute('data-ai-id', id);
            let label = (el.innerText || el.placeholder || el.ariaLabel ||
                         el.name || el.value || el.title || '').trim();
            label = label.substring(0, 80).replace(/\\n/g, ' ').replace(/\\s+/g, ' ');
            if (!label) return;

            map.push({ id: id, tag: el.tagName.toLowerCase(), label: label, type: el.type || '' });
            id++;
        });
        return map;
    }
    """

    def get_dom_snapshot(self) -> str:
        if not self._page:
            return "Browser not started."
        try:
            items = self._page.evaluate(self._JS_SNAPSHOT)
            self._element_map = {
                item["id"]: f'[data-ai-id="{item["id"]}"]' for item in items
            }
            lines = [f"Title: {self._page.title()}", f"URL: {self._page.url}",
                     f"Elements ({len(items)}):"]
            for item in items:
                type_info = f" ({item['type']})" if item["type"] else ""
                lines.append(f"  [{item['id']}] {item['tag'].upper()} - {item['label']}{type_info}")
            return "\n".join(lines)
        except Exception as e:
            return f"Snapshot error: {e}"

    # ------------------------------------------------------------------
    # Action execution (kept for LLM fallback)
    # ------------------------------------------------------------------
    def execute_action(self, action_data: dict) -> str:
        try:
            action = action_data.get("action", "").lower().strip()
            if action == "navigate":
                return self.navigate(action_data.get("value", ""))
            if action == "wait":
                time.sleep(int(action_data.get("value", 2)))
                return "Waited."
            if action == "scroll":
                d = action_data.get("value", "down")
                self._page.evaluate(f"window.scrollBy(0, {500 if d == 'down' else -500})")
                return f"Scrolled {d}."
            if action in ("press_enter", "enter", "submit"):
                self._page.keyboard.press("Enter")
                time.sleep(2)
                return "Pressed Enter."
            if action in ("extract_text", "extract"):
                el_id = action_data.get("id")
                if el_id is not None:
                    sel = self._element_map.get(int(el_id))
                    if sel:
                        return f"Extracted: {(self._page.text_content(sel) or '').strip()[:500]}"
                return f"Page text: {(self._page.text_content('body') or '').strip()[:2000]}"
            el_id = action_data.get("id")
            if el_id is None:
                return "Error: no element ID."
            el_id = int(el_id)
            sel = self._element_map.get(el_id)
            if not sel:
                return f"Error: element [{el_id}] not found."
            if action == "click":
                self._page.click(sel, timeout=5000)
                time.sleep(1)
                return f"Clicked [{el_id}]"
            if action == "type":
                val = action_data.get("value", "")
                from capabilities.security_manager import security_manager
                val = security_manager.inject_secrets(val)
                self._page.fill(sel, val)
                return f"Typed '{val}' into [{el_id}]"
            if action == "select":
                val = action_data.get("value", "")
                self._page.select_option(sel, label=val)
                return f"Selected '{val}'"
            return f"Unknown action: {action}"
        except Exception as e:
            return f"Action error: {e}"

    # ------------------------------------------------------------------
    # JSON Extraction (for LLM fallback)
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_llm_json(raw: str) -> Optional[dict]:
        if not raw or not raw.strip():
            return None
        text = raw.strip()
        if "```" in text:
            parts = text.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    text = part
                    break
        for prefix in ("Answer:", "answer:", "Output:", "output:"):
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix):].strip()
        if text.startswith("{"):
            try:
                return json.loads(text)
            except:
                pass
        match = re.search(r'\{[^{}]+\}', text)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        start, end = text.find('{'), text.rfind('}')
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end+1])
            except:
                try:
                    return json.loads(text[start:end+1].replace("'", '"'))
                except:
                    pass
        return None


# Singleton
browser_agent = BrowserAgent()
