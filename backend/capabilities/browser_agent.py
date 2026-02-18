"""
AI Browser Agent - Comprehensive Web Automation
================================================
ARCHITECTURE:
  DIRECT mode: Uses known CSS selectors for common sites.
  Handles search, filters, sorting, extraction, form filling,
  cart operations, conditional logic, and multi-step tasks.

All public methods are sync; the handler calls them via asyncio.to_thread().
"""

import json
import re
import time
import threading
from typing import Dict, Optional, List, Tuple
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext


# ======================================================================
# Site-specific selectors
# ======================================================================
SITE_CONFIG = {
    "amazon": {
        "search_input": "#twotabsearchtextbox",
        "search_submit": "#nav-search-submit-button",
        "first_result": 'div[data-component-type="s-search-result"] h2 a, .s-result-item h2 a',
        "price": '.a-price .a-offscreen, .a-price-whole, #priceblock_ourprice, #priceblock_dealprice, .a-color-price',
        "rating": '#acrPopover, span.a-icon-alt, #averageCustomerReviews span',
        "add_to_cart": '#add-to-cart-button, input#add-to-cart-button',
        "wait": 3,
    },
    "google": {
        "search_input": 'textarea[name="q"], input[name="q"]',
        "search_submit": None,
        "first_result": '#search a h3, #rso a h3',
        "wait": 2,
    },
    "youtube": {
        "search_input": 'input#search, input[name="search_query"]',
        "search_submit": "#search-icon-legacy, button#search-icon-legacy",
        "first_result": 'ytd-video-renderer a#video-title, a#video-title',
        "wait": 3,
    },
    "wikipedia": {
        "search_input": '#searchInput, input[name="search"], #searchform input[type="search"]',
        "search_submit": None,
        "first_result": '.mw-search-result-heading a, .mw-search-results a',
        "wait": 2,
    },
    "flipkart": {
        "search_input": 'input[name="q"], input[title="Search for Products, Brands and More"], input._3704LK',
        "search_submit": 'button[type="submit"], button._2iA8p4',
        "first_result": 'a._1fQZEK, div._2kHMtA a, a._2rpwqI, a.CGtC98',
        "price": 'div._30jeq3, div._3I9_wc, div._16Jk6d',
        "rating": 'div._3LWZlK',
        "add_to_cart": 'button._2KpZ6l._2U9uOA, button:has-text("ADD TO CART")',
        "wait": 3,
    },
    "myntra": {
        "search_input": 'input.desktop-searchBar, input[placeholder*="Search"]',
        "search_submit": None,
        "first_result": 'a.product-base',
        "price": '.product-discountedPrice, .product-price',
        "wait": 3,
    },
    "imdb": {
        "search_input": '#suggestion-search-input, input[name="q"]',
        "search_submit": "#suggestion-search-button",
        "first_result": '.find-result-item a, .ipc-metadata-list-summary-item a, a.ipc-metadata-list-summary-item__t',
        "rating": '[data-testid="hero-rating-bar__aggregate-rating__score"] span, .sc-bde20123-1, span.sc-bde20123-1',
        "wait": 3,
    },
    "github": {
        "search_input": 'input[name="q"], input.header-search-input, input[data-target="query-builder.input"]',
        "search_submit": None,
        "first_result": '.repo-list-item a, a.v-align-middle, div.search-title a',
        "wait": 3,
    },
    "linkedin": {
        "search_input": 'input[placeholder*="Search"], input.search-global-typeahead__input',
        "search_submit": None,
        "first_result": '.search-result__title a, .entity-result__title a',
        "wait": 3,
    },
    "weather": {
        "search_input": '#LocationSearch_input, input[id*="search"], input[placeholder*="Search"]',
        "search_submit": None,
        "first_result": '#LocationSearch_listbox li button, button[data-testid="ctaButton"]',
        "wait": 3,
    },
    "irctc": {
        "search_input": None,
        "wait": 5,
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
        self._element_discovery = None  # Will be initialized when page is ready
        self._use_dynamic_discovery = True  # Feature flag

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
        self._page.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        )
        
        # Initialize dynamic element discovery
        from capabilities.element_discovery import create_element_discovery
        self._element_discovery = create_element_discovery(self._page)
        
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
        self.stop()
        self.start()

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def navigate(self, url: str) -> str:
        """Navigate to URL, ensuring browser is started first"""
        # Always ensure browser is running
        if not self._page:
            print("[Agent] Browser not started, auto-starting...")
            self.start()
            
        try:
            print(f"[Agent] Navigating to: {url}")
            self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)
            title = self._page.title()
            print(f"[Agent] Successfully loaded: {title}")
            return f"Navigated to {url} (Title: {title})"
        except Exception as e:
            # Try to recover by restarting browser
            if any(k in str(e).lower() for k in ["closed", "detached", "target closed"]):
                try:
                    print("[Agent] Browser disconnected, restarting...")
                    self.restart()
                    self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    time.sleep(2)
                    return f"Navigated to {url} (Title: {self._page.title()}) [after restart]"
                except Exception as e2:
                    return f"Navigation failed after restart: {e2}"
            return f"Navigation failed: {e}"

    # ------------------------------------------------------------------
    # Element interaction helpers
    # ------------------------------------------------------------------
    def _find(self, selectors: str, timeout: int = 5000) -> Optional[str]:
        """Try multiple comma-separated selectors, return the first visible one."""
        if not selectors:
            return None
        for sel in selectors.split(","):
            sel = sel.strip()
            try:
                loc = self._page.locator(sel).first
                if loc.is_visible(timeout=timeout):
                    return sel
            except:
                continue
        return None
    
    def _find_smart(self, element_type: str, selectors: Optional[str] = None, timeout: int = 5000) -> Optional[str]:
        """
        Smart element finding: try hardcoded selectors first, fall back to dynamic discovery.
        
        Args:
            element_type: Type of element (search_input, button, price, rating, etc.)
            selectors: Optional comma-separated fallback selectors
            timeout: Timeout in milliseconds
        
        Returns:
            Working CSS selector or None
        """
        # 1. Try hardcoded selectors if provided (fast path)
        if selectors:
            found = self._find(selectors, timeout)
            if found:
                return found
        
        # 2. Use dynamic element discovery if enabled
        if self._use_dynamic_discovery and self._element_discovery:
            try:
                if element_type == "search_input":
                    return self._element_discovery.find_search_input()
                elif element_type == "search_button":
                    return self._element_discovery.find_button("search")
                elif element_type == "submit_button":
                    return self._element_discovery.find_button("submit")
                elif element_type == "first_result":
                    return self._element_discovery.find_first_result()
                elif element_type == "price":
                    return self._element_discovery.find_price()
                elif element_type == "rating":
                    return self._element_discovery.find_rating()
                elif element_type == "add_to_cart":
                    return self._element_discovery.find_add_to_cart_button()
                else:
                    # Generic LLM-based search
                    return self._element_discovery.find_by_llm(element_type)
            except Exception as e:
                print(f"[BrowserAgent] Dynamic discovery failed for {element_type}: {e}")
        
        return None

    def _safe_click(self, selector: str, timeout: int = 5000) -> bool:
        """Click element safely, return True if success."""
        try:
            self._page.click(selector, timeout=timeout)
            time.sleep(1.5)
            return True
        except:
            return False

    def _type_in(self, selector: str, text: str) -> bool:
        """Type text into element safely."""
        try:
            self._page.click(selector, timeout=5000)
            time.sleep(0.3)
            self._page.fill(selector, text)
            time.sleep(0.3)
            return True
        except:
            try:
                # Fallback: type character by character
                self._page.click(selector, timeout=5000)
                time.sleep(0.3)
                self._page.locator(selector).first.press_sequentially(text, delay=50)
                return True
            except:
                return False

    def _press_enter(self):
        self._page.keyboard.press("Enter")
        time.sleep(3)

    def _scroll_down(self, px: int = 500):
        self._page.evaluate(f"window.scrollBy(0, {px})")
        time.sleep(1)

    def _get_text(self, selectors: str, max_items: int = 5) -> str:
        """Extract text from elements matching selectors."""
        for sel in selectors.split(","):
            sel = sel.strip()
            try:
                locs = self._page.locator(sel)
                count = locs.count()
                if count > 0:
                    texts = []
                    for i in range(min(count, max_items)):
                        t = locs.nth(i).text_content()
                        if t and t.strip():
                            texts.append(t.strip()[:200])
                    if texts:
                        return " | ".join(texts)
            except:
                continue
        return ""

    def _click_text(self, text: str, tag: str = "*", scroll: bool = True) -> bool:
        """Find and click element by text content. Scrolls if needed."""
        for attempt in range(5 if scroll else 1):
            try:
                loc = self._page.locator(f"{tag}:has-text('{text}')").first
                if loc.is_visible(timeout=2000):
                    loc.click(timeout=5000)
                    time.sleep(2)
                    return True
            except:
                pass
            if scroll:
                self._scroll_down()
        return False

    def _click_text_exact(self, text: str) -> bool:
        """Click element with exact text match."""
        try:
            loc = self._page.get_by_text(text, exact=True).first
            if loc.is_visible(timeout=3000):
                loc.click(timeout=5000)
                time.sleep(2)
                return True
        except:
            pass
        return False

    # ------------------------------------------------------------------
    # SEARCH
    # ------------------------------------------------------------------
    def _do_search(self, site: str, query: str) -> str:
        """
        Robust search that works on ANY website.
        Ensures browser is running, page is loaded, and uses multiple fallback strategies.
        """
        # CRITICAL: Ensure browser is started
        if not self._page:
            print("[Agent] Browser not started, starting now...")
            self.start()
            time.sleep(2)
        
        config = SITE_CONFIG.get(site, {})
        
        # Give page time to fully load before searching
        try:
            self._page.wait_for_load_state("networkidle", timeout=5000)
        except:
            time.sleep(2)  # Fallback wait
        
        # Try site-specific selector first, with dynamic fallback
        search_sel = config.get("search_input")
        found = self._find_smart("search_input", search_sel, timeout=10000)
        
        if found:
            print(f"[Agent] Found search input via: {found}")
            if self._type_in(found, query):
                submit = config.get("search_submit")
                if submit:
                    # Try configured submit button
                    sub_sel = self._find_smart("search_button", submit, timeout=5000)
                    if sub_sel:
                        print(f"[Agent] Clicking search button: {sub_sel}")
                        self._safe_click(sub_sel)
                    else:
                        print("[Agent] No submit button, pressing Enter")
                        self._press_enter()
                else:
                    print("[Agent] No submit button configured, pressing Enter")
                    self._press_enter()
                time.sleep(config.get("wait", 3))
                return f"✅ Searched for '{query}' on {site or 'page'}"
            else:
                print(f"[Agent] ❌ Failed to type into search input: {found}")

        # FALLBACK 1: Try generic input selectors without smart finding
        print("[Agent] Primary search failed, trying generic selectors...")
        generic_inputs = [
            'input[type="search"]',
            'input[name="search_query"]',  # YouTube
            'input[name*="search" i]',
            'input[name*="q" i]',
            'input[name="q"]',
            'textarea[name="q"]',
            'input[placeholder*="Search" i]',
            'input[aria-label*="Search" i]',
            'input[id*="search" i]',
            '#search',
            'input[type="text"]',
        ]
        
        for sel in generic_inputs:
            try:
                if self._find(sel, timeout=3000):
                    print(f"[Agent] Found via generic selector: {sel}")
                    if self._type_in(sel, query):
                        # Look for any submit button nearby
                        for submit_sel in ['button[type="submit"]', 'button:has-text("Search")', '#search-icon-legacy']:
                            if self._find(submit_sel, timeout=2000):
                                self._safe_click(submit_sel)
                                time.sleep(3)
                                return f"✅ Searched for '{query}' (generic fallback)"
                        # No button, try Enter
                        self._press_enter()
                        time.sleep(3)
                        return f"✅ Searched for '{query}' (generic fallback with Enter)"
            except Exception as e:
                print(f"[Agent] Generic selector {sel} failed: {e}")
                continue

        # FALLBACK 2: Find ANY visible text input and try it
        print("[Agent] Trying to find ANY visible input...")
        try:
            all_inputs = self._page.locator('input[type="text"], input[type="search"], input:not([type="hidden"]):not([type="submit"])').all()
            for inp in all_inputs[:5]:  # Try first 5 visible inputs
                try:
                    if inp.is_visible():
                        print(f"[Agent] Trying visible input...")
                        inp.fill(query)
                        time.sleep(0.5)
                        self._press_enter()
                        time.sleep(3)
                        return f"✅ Searched for '{query}' (found visible input)"
                except:
                    continue
        except Exception as e:
            print(f"[Agent] Fallback input search failed: {e}")

        return f"⚠️ Could not find search input on {site or 'page'} after all attempts"

    # ------------------------------------------------------------------
    # FILTERS
    # ------------------------------------------------------------------
    def _do_filter(self, site: str, ftype: str, fval) -> str:
        try:
            if ftype == "price_under":
                return self._filter_price(site, int(fval))
            elif ftype == "star_rating":
                return self._filter_stars(site, int(fval))
            elif ftype == "size":
                return self._filter_size(site, str(fval))
            elif ftype == "upload_date":
                return self._filter_upload_date(site)
            elif ftype == "ram":
                return self._filter_text_click(f"{fval} GB")
            elif ftype == "ssd":
                return self._filter_text_click("SSD")
            return f"Filter {ftype} not implemented"
        except Exception as e:
            return f"Filter error: {e}"

    def _filter_price(self, site: str, max_price: int) -> str:
        if site == "amazon":
            # Try price range links
            for text in [f"Under ₹{max_price:,}", f"₹{max_price:,}", f"Under ₹{max_price}"]:
                if self._click_text(text, scroll=True):
                    return f"✅ Price filter: under ₹{max_price}"
            # Try manual price input
            try:
                high = self._page.locator('input#high-price, input[name="high-price"]')
                if high.first.is_visible(timeout=3000):
                    high.first.fill(str(max_price))
                    go = self._page.locator('.a-button-text:has-text("Go"), input[type="submit"]')
                    if go.first.is_visible(timeout=2000):
                        go.first.click()
                        time.sleep(3)
                        return f"✅ Price filter: under ₹{max_price}"
            except:
                pass
        elif site == "flipkart":
            try:
                inputs = self._page.locator('input[placeholder*="Max"], div._6BWGkB input')
                if inputs.last.is_visible(timeout=3000):
                    inputs.last.fill(str(max_price))
                    self._press_enter()
                    return f"✅ Price filter: under ₹{max_price}"
            except:
                pass
        return f"⚠️ Could not apply price filter ₹{max_price}"

    def _filter_stars(self, site: str, stars: int) -> str:
        if site == "amazon":
            star_texts = [f"{stars} Stars & Up", f"{stars} Stars", f"{stars}★ & above", f"{stars} & Up"]
            for text in star_texts:
                if self._click_text(text, scroll=True):
                    return f"✅ Applied {stars}-star filter"
            # Try aria-label based
            try:
                loc = self._page.locator(f'section[aria-label*="{stars} Stars"] a, [aria-label*="{stars} Stars"]').first
                if loc.is_visible(timeout=3000):
                    loc.click()
                    time.sleep(3)
                    return f"✅ Applied {stars}-star filter"
            except:
                pass
        elif site == "flipkart":
            if self._click_text(f"{stars}★", scroll=True):
                return f"✅ Applied {stars}-star filter"
        return f"⚠️ Could not apply {stars}-star filter"

    def _filter_size(self, site: str, size: str) -> str:
        if site == "myntra":
            # Click "Size" header first to expand, then click specific size
            self._click_text("Size", tag="div, span, h4", scroll=True)
            time.sleep(1)
            if self._click_text_exact(size):
                return f"✅ Applied size filter: {size}"
            if self._click_text(f"Size {size}", scroll=True):
                return f"✅ Applied size filter: {size}"
        # Generic
        if self._click_text(f"Size {size}", scroll=True) or self._click_text_exact(size):
            return f"✅ Applied size filter: {size}"
        return f"⚠️ Could not apply size {size} filter"

    def _filter_upload_date(self, site: str) -> str:
        if site == "youtube":
            # Click Filters button
            try:
                for sel in ['button#filter-button', 'tp-yt-paper-button:has-text("Filters")',
                            'button:has-text("Filters")']:
                    if self._find(sel, timeout=3000):
                        self._safe_click(sel)
                        time.sleep(2)
                        break

                # Click "Upload date"
                if self._click_text("Upload date"):
                    return "✅ Applied 'Upload date' filter"
                if self._click_text("Last hour") or self._click_text("Today"):
                    return "✅ Applied recent upload filter"
            except:
                pass
        return "⚠️ Could not apply upload date filter"

    def _filter_text_click(self, text: str) -> str:
        """Generic filter: scroll and click text."""
        if self._click_text(text, scroll=True):
            return f"✅ Applied filter: {text}"
        return f"⚠️ Could not find filter: {text}"

    # ------------------------------------------------------------------
    # SORT
    # ------------------------------------------------------------------
    def _do_sort(self, site: str, sort_type: str) -> str:
        try:
            if site == "flipkart":
                label = "Price -- Low to High" if sort_type == "low_to_high" else "Price -- High to Low"
                if self._click_text(label, scroll=False):
                    return f"✅ Sorted: {label}"
                # Try shorter text
                short = "Low to High" if sort_type == "low_to_high" else "High to Low"
                if self._click_text(short, scroll=False):
                    return f"✅ Sorted: {short}"

            elif site == "amazon":
                try:
                    dropdown = self._page.locator('#s-result-sort-select, .a-dropdown-container')
                    if dropdown.first.is_visible(timeout=3000):
                        dropdown.first.click()
                        time.sleep(1)
                        label = "Price: Low to High" if sort_type == "low_to_high" else "Price: High to Low"
                        if self._click_text(label, scroll=False):
                            return f"✅ Sorted: {label}"
                except:
                    pass

            elif site == "youtube":
                if sort_type == "view_count":
                    # Click Filters then Sort by view count
                    for sel in ['button#filter-button', 'button:has-text("Filters")']:
                        if self._find(sel, timeout=2000):
                            self._safe_click(sel)
                            time.sleep(2)
                            break
                    if self._click_text("View count"):
                        return "✅ Sorted by view count"

            # Generic
            label = "Low to High" if sort_type == "low_to_high" else "High to Low"
            if self._click_text(label, scroll=True):
                return f"✅ Sorted: {label}"
        except Exception as e:
            return f"Sort error: {e}"
        return f"⚠️ Could not apply sort: {sort_type}"

    # ------------------------------------------------------------------
    # CLICK FIRST RESULT
    # ------------------------------------------------------------------
    def _do_click_first(self, site: str) -> str:
        config = SITE_CONFIG.get(site, {})
        sel = config.get("first_result")
        if sel:
            found = self._find(sel, timeout=5000)
            if found:
                try:
                    self._page.locator(found).first.click(timeout=5000)
                    time.sleep(3)
                    return f"✅ Opened first result on {site}"
                except:
                    pass
        # Generic fallback
        generic = 'h2 a, h3 a, .result a, .search-result a'
        found = self._find(generic, timeout=3000)
        if found:
            try:
                self._page.locator(found).first.click(timeout=5000)
                time.sleep(3)
                return "✅ Opened first result"
            except:
                pass
        return "⚠️ Could not click first result"

    # ------------------------------------------------------------------
    # CLICK TAB (Images, Reviews, etc.)
    # ------------------------------------------------------------------
    def _do_click_tab(self, tab_name: str) -> str:
        if self._click_text(tab_name, scroll=False):
            return f"✅ Clicked '{tab_name}' tab"
        # Try Google-style tabs
        try:
            loc = self._page.locator(f'a[role="tab"]:has-text("{tab_name}"), div[role="tab"]:has-text("{tab_name}")')
            if loc.first.is_visible(timeout=3000):
                loc.first.click()
                time.sleep(2)
                return f"✅ Clicked '{tab_name}' tab"
        except:
            pass
        return f"⚠️ Could not find '{tab_name}' tab"

    # ------------------------------------------------------------------
    # SECTION NAVIGATION
    # ------------------------------------------------------------------
    def _do_navigate_section(self, section: str) -> str:
        # Try clicking a link/heading matching section name
        for tag in ["a", "h2", "h3", "span", "*"]:
            if self._click_text(section, tag=tag, scroll=True):
                return f"✅ Navigated to '{section}' section"
        # Try Wikipedia-specific TOC
        try:
            toc = self._page.locator(f'a[href*="{section}"], li.toclevel-1 a:has-text("{section}")')
            if toc.first.is_visible(timeout=3000):
                toc.first.click()
                time.sleep(2)
                return f"✅ Navigated to '{section}' section"
        except:
            pass
        return f"⚠️ Could not navigate to '{section}' section"

    # ------------------------------------------------------------------
    # FORM FILLING
    # ------------------------------------------------------------------
    def _do_form_fill(self, fields: dict) -> str:
        results = []
        # Map field names to common selectors
        selector_map = {
            "name": ['input[name="name"]', 'input[placeholder*="name" i]', 'input[id*="name" i]',
                      'input[type="text"]:first-of-type'],
            "email": ['input[type="email"]', 'input[name="email"]', 'input[placeholder*="email" i]',
                       'input[id*="email" i]'],
            "message": ['textarea', 'textarea[name="message"]', 'input[name="message"]'],
            "username": ['input[name="username"]', 'input[id*="user" i]', 'input[placeholder*="user" i]',
                          'input[type="text"]:first-of-type'],
            "password": ['input[type="password"]', 'input[name="password"]', 'input[id*="pass" i]'],
            "phone": ['input[type="tel"]', 'input[name="phone"]', 'input[placeholder*="phone" i]'],
        }

        for field_name, value in fields.items():
            filled = False
            selectors = selector_map.get(field_name, [f'input[name="{field_name}"]', f'input[id="{field_name}"]'])
            for sel in selectors:
                found = self._find(sel, timeout=2000)
                if found:
                    if self._type_in(found, value):
                        results.append(f"✅ Filled {field_name}: '{value}'")
                        filled = True
                        break
            if not filled:
                results.append(f"⚠️ Could not fill {field_name}")

        # Try to submit form
        submit_sels = ['button[type="submit"]', 'input[type="submit"]',
                        'button:has-text("Submit")', 'button:has-text("Login")', 'button:has-text("Sign in")']
        for sel in submit_sels:
            if self._find(sel, timeout=2000):
                self._safe_click(sel)
                results.append("✅ Form submitted")
                break

        return " | ".join(results)

    # ------------------------------------------------------------------
    # ADD TO CART
    # ------------------------------------------------------------------
    def _do_add_to_cart(self, site: str) -> str:
        config = SITE_CONFIG.get(site, {})
        cart_sel = config.get("add_to_cart")
        if cart_sel:
            found = self._find(cart_sel, timeout=5000)
            if found and self._safe_click(found):
                return "✅ Added to cart"
        # Generic
        if self._click_text("Add to Cart", scroll=True) or self._click_text("ADD TO CART", scroll=True):
            return "✅ Added to cart"
        if self._click_text("Buy Now", scroll=True):
            return "✅ Clicked Buy Now"
        return "⚠️ Could not add to cart"

    # ------------------------------------------------------------------
    # DATA EXTRACTION
    # ------------------------------------------------------------------
    def _do_extract(self, site: str, etype: str) -> str:
        config = SITE_CONFIG.get(site, {})
        try:
            if etype == "price":
                sel = config.get("price", '[class*="price"], [class*="Price"], .price')
                return self._get_text(sel, max_items=3) or "Price not found"

            elif etype == "rating":
                sel = config.get("rating", '[class*="rating"], [class*="Rating"], .rating')
                return self._get_text(sel, max_items=2) or "Rating not found"

            elif etype == "compare_prices":
                sel = config.get("price", '[class*="price"], .price')
                try:
                    locs = self._page.locator(sel.split(",")[0].strip())
                    if locs.count() >= 2:
                        p1 = locs.nth(0).text_content().strip()
                        p2 = locs.nth(1).text_content().strip()
                        return f"Product 1: {p1} | Product 2: {p2}"
                except:
                    pass
                return "Could not compare prices"

            elif etype == "population":
                # Wikipedia info extraction
                text = self._get_text('.infobox td, .infobox-data', max_items=20)
                pop_match = re.search(r'[\d,]+(?:\.\d+)?\s*(?:billion|million|crore|lakh)', text, re.IGNORECASE)
                if pop_match:
                    return pop_match.group(0)
                # Try full page text
                body = self._page.text_content("body") or ""
                pop = re.search(r'population[:\s]*[\d,]+(?:\.\d+)?(?:\s*(?:billion|million))?', body.lower())
                if pop:
                    return pop.group(0)
                return "Population data not found"

            elif etype == "temperature":
                text = self._get_text(
                    '[data-testid="TemperatureValue"], .CurrentConditions--tempValue, '
                    '.temp, [class*="temperature"], [class*="temp"]',
                    max_items=3
                )
                return text or "Temperature not found"

        except Exception as e:
            return f"Extraction error: {e}"
        return "Unknown extraction type"

    # ------------------------------------------------------------------
    # CONDITIONAL LOGIC
    # ------------------------------------------------------------------
    def _evaluate_condition(self, site: str, cond_type: str, cond_val, extracted: dict) -> str:
        try:
            if cond_type == "price_below":
                price_text = extracted.get("price", "") or self._do_extract(site, "price")
                # Parse numeric price
                nums = re.findall(r'[\d,]+\.?\d*', price_text.replace(",", ""))
                if nums:
                    price = float(nums[0])
                    if price < cond_val:
                        # Condition met — click the product
                        self._do_click_first(site)
                        return f"✅ Condition met: price ₹{price:,.0f} < ₹{cond_val:,} → opened product"
                    else:
                        return f"❌ Condition NOT met: price ₹{price:,.0f} >= ₹{cond_val:,}"
                return f"⚠️ Could not parse price to evaluate condition"

            elif cond_type == "rating_above":
                rating_text = extracted.get("rating", "") or self._do_extract(site, "rating")
                nums = re.findall(r'[\d.]+', rating_text)
                if nums:
                    rating = float(nums[0])
                    if rating > cond_val:
                        # Condition met — open reviews
                        self._click_text("review", scroll=True) or self._click_text("Reviews", scroll=True)
                        return f"✅ Condition met: rating {rating} > {cond_val} → opened reviews"
                    else:
                        return f"❌ Condition NOT met: rating {rating} <= {cond_val}"
                return f"⚠️ Could not parse rating to evaluate condition"

        except Exception as e:
            return f"Condition error: {e}"
        return f"Unknown condition type: {cond_type}"

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------
    def _identify_site(self, url: str) -> str:
        url_lower = url.lower()
        for key in SITE_CONFIG:
            if key in url_lower:
                return key
        # Extra mappings
        extras = {"irctc": "irctc", "weather.com": "weather", "example.com": "generic"}
        for k, v in extras.items():
            if k in url_lower:
                return v
        return ""

    def _dismiss_popups(self, site: str):
        """Dismiss common popups."""
        if site == "flipkart":
            try:
                for sel in ['button._2KpZ6l._2doB4z', 'span._30XB9F', 'button:has-text("✕")']:
                    loc = self._page.locator(sel)
                    if loc.first.is_visible(timeout=2000):
                        loc.first.click()
                        time.sleep(1)
                        print("[Agent] Dismissed Flipkart popup", flush=True)
                        return
            except:
                pass
        # Generic cookie/notification banners
        try:
            for sel in ['button:has-text("Accept")', 'button:has-text("Got it")',
                         'button:has-text("OK")', '[id*="cookie"] button']:
                loc = self._page.locator(sel)
                if loc.first.is_visible(timeout=1500):
                    loc.first.click()
                    time.sleep(0.5)
                    break
        except:
            pass

    def _build_summary(self, parsed: dict, extracted: dict, logs: list, url: str) -> str:
        parts = []
        if url:
            parts.append(f"Navigated to {url}")
        if parsed["search_query"]:
            parts.append(f"Searched for '{parsed['search_query']}'")
        for ft, fv in parsed["filters"]:
            parts.append(f"Filter: {ft}={fv}")
        if parsed["sort"]:
            parts.append(f"Sort: {parsed['sort']}")
        if parsed["click_first"]:
            parts.append("Opened first result")
        if parsed["click_tab"]:
            parts.append(f"Clicked '{parsed['click_tab']}' tab")
        if parsed["navigate_section"]:
            parts.append(f"Section: '{parsed['navigate_section']}'")
        if parsed["form_fields"]:
            parts.append(f"Form filled: {list(parsed['form_fields'].keys())}")
        if parsed["add_to_cart"]:
            parts.append("Added to cart")
        if extracted:
            for k, v in extracted.items():
                parts.append(f"{k}: {v[:200]}")

        summary = " → ".join(parts) if parts else "Task executed"
        detail = "\n".join([f"  • {l}" for l in logs[-15:]])
        return f"✅ {summary}\n\nExecution Log:\n{detail}"


# Singleton
browser_agent = BrowserAgent()
