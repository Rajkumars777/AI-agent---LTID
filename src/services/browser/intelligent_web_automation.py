"""
intelligent_web_automation.py
==============================
100% FREE intelligent web automation.

- NO paid APIs (no OpenAI, no Claude API calls)
- Tab-key field navigation for reliable form detection
- CDP BrowserView connection (connect to your real browser)
- Cookie/consent/notification bypass
- Auto-login with credential prompting
- Page survey & info extraction
- Multi-step natural language instructions (heuristic parser)
- Error recovery & retries
- Page change detection
- Scroll, drag, screenshot support
"""

import asyncio
import re
import json
import getpass
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
from .agent import browser_agent


# ══════════════════════════════════════════════════════════════
# CONNECT TO BROWSERVIEW (CDP)
# Launch Chrome/Chromium with:
#   chrome --remote-debugging-port=9222
# Then call connect_to_browserview() to attach.
# ══════════════════════════════════════════════════════════════

async def connect_to_browserview(port: int = 9222) -> str:
    """
    Connects to an existing browser via Chrome DevTools Protocol.
    Start your browser with:
        chrome --remote-debugging-port=9222
        chromium-browser --remote-debugging-port=9222
    """
    result = await browser_agent.connect(port)
    print(f"[BrowserView] {result}")
    return result


# ══════════════════════════════════════════════════════════════
# CREDENTIAL HANDLER  (free, secure, in-memory only)
# ══════════════════════════════════════════════════════════════

class CredentialHandler:
    """Prompts user for credentials at runtime. Never logs or stores to disk."""

    def __init__(self):
        self._cache: Dict[str, Dict[str, str]] = {}

    def request_credentials(self, site: str, fields: List[str] = None) -> Dict[str, str]:
        if site in self._cache:
            print(f"[Auth] Using cached credentials for: {site}")
            return self._cache[site]

        fields = fields or ["username", "password"]
        print(f"\n🔐 Login required for: {site}")
        print("   (credentials stored in memory only, never saved to disk)\n")
        creds: Dict[str, str] = {}
        for field in fields:
            if "password" in field.lower():
                creds[field] = getpass.getpass(f"   {field}: ")
            else:
                creds[field] = input(f"   {field}: ").strip()

        self._cache[site] = creds
        return creds

    def clear(self, site: Optional[str] = None):
        if site:
            self._cache.pop(site, None)
        else:
            self._cache.clear()


credential_handler = CredentialHandler()


# ══════════════════════════════════════════════════════════════
# TAB-KEY FIELD NAVIGATOR
# ══════════════════════════════════════════════════════════════

class TabNavigator:
    """
    Uses the Tab key to walk through all focusable elements on a page.
    This is the most reliable way to find interactive fields without
    depending on specific CSS selectors or any paid AI.
    """

    def __init__(self, page):
        self.page = page

    async def get_all_focusable(self) -> List[Dict[str, Any]]:
        """
        Presses Tab repeatedly and collects info about every focused element.
        Returns list of element descriptors.
        """
        try:
            await self.page.click("body", position={"x": 0, "y": 0})
        except Exception:
            pass

        await asyncio.sleep(0.2)

        focusable = []
        seen_ids  = set()
        max_tabs  = 60

        for _ in range(max_tabs):
            await self.page.keyboard.press("Tab")
            await asyncio.sleep(0.08)

            info = await self.page.evaluate("""
                () => {
                    const el = document.activeElement;
                    if (!el || el === document.body) return null;
                    const rect = el.getBoundingClientRect();
                    return {
                        tag:         el.tagName.toLowerCase(),
                        type:        el.type || '',
                        name:        el.name || '',
                        id:          el.id   || '',
                        placeholder: el.placeholder || '',
                        ariaLabel:   el.getAttribute('aria-label') || '',
                        text:        el.innerText ? el.innerText.trim().slice(0, 80) : '',
                        value:       el.value || '',
                        visible:     rect.width > 0 && rect.height > 0,
                        x:           rect.x,
                        y:           rect.y,
                        width:       rect.width,
                        height:      rect.height,
                        dataTestId:  el.getAttribute('data-testid') || '',
                        className:   el.className || '',
                    };
                }
            """)

            if not info or not info.get("visible"):
                continue

            uid = f"{info['tag']}|{info['id']}|{info['name']}|{info['x']:.0f}|{info['y']:.0f}"
            if uid in seen_ids:
                break   # wrapped around — all elements seen
            seen_ids.add(uid)
            focusable.append(info)

        return focusable

    async def tab_to_field(self, hint: str) -> bool:
        """
        Tabs to a specific field matching the hint and leaves focus there.
        Returns True if found.
        """
        hint = hint.lower()

        try:
            await self.page.click("body", position={"x": 0, "y": 0})
        except Exception:
            pass

        await asyncio.sleep(0.15)

        for _ in range(60):
            await self.page.keyboard.press("Tab")
            await asyncio.sleep(0.08)

            info = await self.page.evaluate("""
                () => {
                    const el = document.activeElement;
                    if (!el) return null;
                    return {
                        tag:         el.tagName.toLowerCase(),
                        type:        el.type || '',
                        name:        el.name || '',
                        id:          el.id   || '',
                        placeholder: el.placeholder || '',
                        ariaLabel:   el.getAttribute('aria-label') || '',
                        text:        el.innerText ? el.innerText.trim().slice(0,80) : '',
                        dataTestId:  el.getAttribute('data-testid') || '',
                        className:   el.className || '',
                    };
                }
            """)

            if not info:
                continue

            haystack = " ".join([
                info.get("type",""),
                info.get("name",""),
                info.get("id",""),
                info.get("placeholder",""),
                info.get("ariaLabel",""),
                info.get("text",""),
                info.get("dataTestId",""),
                info.get("className",""),
            ]).lower()

            if hint in haystack:
                return True

        return False

    async def type_in_focused(self, text: str, delay: int = 55):
        """Types text into the currently focused element."""
        await self.page.keyboard.press("Control+a")
        await asyncio.sleep(0.1)
        await self.page.keyboard.type(text, delay=delay)

    async def fill_by_tab(self, hint: str, value: str) -> str:
        """Tabs to a field matching hint and types the value."""
        found = await self.tab_to_field(hint)
        if not found:
            return f"❌ Could not find field: '{hint}' via Tab navigation"
        await self.type_in_focused(value)
        return f"✅ Filled '{hint}' with value via Tab"

    async def press_tab_submit(self) -> str:
        """Tabs forward until a submit button is focused, then presses Enter."""
        for _ in range(10):
            await self.page.keyboard.press("Tab")
            await asyncio.sleep(0.08)
            info = await self.page.evaluate("""
                () => {
                    const el = document.activeElement;
                    if (!el) return null;
                    return {tag: el.tagName.toLowerCase(), type: el.type || ''};
                }
            """)
            if info and (info["tag"] == "button" or info["type"] in ("submit", "button")):
                await self.page.keyboard.press("Enter")
                return "✅ Pressed Enter on submit button (Tab)"
        await self.page.keyboard.press("Enter")
        return "✅ Pressed Enter (fallback)"


# ══════════════════════════════════════════════════════════════
# OVERLAY / COOKIE / NOTIFICATION BYPASS
# ══════════════════════════════════════════════════════════════

_COOKIE_BUTTON_TEXTS = [
    "Accept all", "Accept All", "Accept All Cookies", "Allow all cookies",
    "Allow all", "I Agree", "Agree", "OK", "Got it", "Close",
    "Agree and Continue", "Accept cookies", "Accept Cookies",
    "Allow Cookies", "Consent", "Yes, I agree", "Continue",
]

_COOKIE_CSS = [
    "#onetrust-accept-btn-handler",
    "#onetrust-reject-all-handler",
    ".onetrust-accept-btn-handler",
    "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
    ".qc-cmp2-summary-buttons button:first-child",
    "[data-testid='cookie-policy-dialog-accept-button']",
    "[aria-label='Accept cookies']",
    "[aria-label='Accept all cookies']",
    ".cookie-accept", ".accept-cookies", "#accept-cookies",
    ".js-accept-cookies", ".cc-accept", "#cookieAccept",
    "[data-action='accept']", ".gdpr-accept",
]

async def bypass_overlays(page) -> int:
    """
    Four-layer overlay bypass — all free:
    1. Deny browser-level notification permissions via JS
    2. Try known CSS selectors for cookie banners
    3. Scan all visible buttons by text content
    4. Inject CSS to hide remaining overlays
    """
    dismissed = 0

    # Layer 1: Block notification permission prompt
    try:
        await page.context.grant_permissions([])
        await page.evaluate("""
            Object.defineProperty(Notification, 'permission', {get: () => 'denied'});
            Notification.requestPermission = () => Promise.resolve('denied');
        """)
    except Exception:
        pass

    await asyncio.sleep(1.2)

    # Layer 2: Known CSS selectors
    for sel in _COOKIE_CSS:
        try:
            el = await page.query_selector(sel)
            if el and await el.is_visible():
                await el.click()
                dismissed += 1
                await asyncio.sleep(0.5)
                break
        except Exception:
            continue

    # Layer 3: Button text scan
    if dismissed == 0:
        for text in _COOKIE_BUTTON_TEXTS:
            for tag in ["button", "a", "[role='button']"]:
                try:
                    el = await page.query_selector(f"{tag}:has-text('{text}')")
                    if el and await el.is_visible():
                        await el.click()
                        dismissed += 1
                        await asyncio.sleep(0.5)
                        break
                except Exception:
                    continue
            if dismissed:
                break

    # Layer 4: CSS injection (hide remaining banners)
    if dismissed == 0:
        try:
            await page.add_style_tag(content="""
                [class*='cookie'],[id*='cookie'],
                [class*='consent'],[id*='consent'],
                [class*='gdpr'],[id*='gdpr'],
                [class*='banner']:not(header):not(nav),
                [id*='cookie-banner'],[id*='gdpr-banner'],
                [class*='notification-bar'],
                div[style*='z-index: 9999']:not(video):not(canvas)
                { display:none!important; visibility:hidden!important; }
                body { overflow:auto!important; }
            """)
            dismissed += 1
        except Exception:
            pass

    if dismissed:
        print(f"[Overlay] ✅ Dismissed {dismissed} overlay(s)")
    return dismissed


# ══════════════════════════════════════════════════════════════
# AUTO-LOGIN  (Tab-based, 100% free)
# ══════════════════════════════════════════════════════════════

async def auto_login(page, site_name: str) -> str:
    """
    Full auto-login pipeline using Tab navigation:
    1. Prompt user for credentials (secure, in-memory)
    2. Bypass overlays
    3. Tab-navigate to username/email field → type
    4. Tab-navigate to password field → type
    5. Tab to submit → press Enter
    6. Wait for page load & verify success
    """
    creds = credential_handler.request_credentials(site_name)
    if not creds:
        return "❌ Login cancelled"

    nav = TabNavigator(page)

    await bypass_overlays(page)
    await asyncio.sleep(0.5)

    # Fill username / email
    username_hints = ["email", "username", "user", "login", "phone", "mobile"]
    filled_user = False
    for hint in username_hints:
        result = await nav.fill_by_tab(hint, creds["username"])
        if "✅" in result:
            filled_user = True
            print(f"[Login] Found user field via hint: '{hint}'")
            break

    if not filled_user:
        return "❌ Could not find username/email field via Tab"

    await asyncio.sleep(0.4)

    # Fill password
    result = await nav.fill_by_tab("password", creds["password"])
    if "❌" in result:
        # Some sites hide password field until email is submitted
        await page.keyboard.press("Tab")
        await asyncio.sleep(0.3)
        await nav.type_in_focused(creds["password"])
        print("[Login] Used fallback: Tab once → type password")

    await asyncio.sleep(0.4)

    # Submit
    submit_result = await nav.press_tab_submit()
    print(f"[Login] {submit_result}")

    # Wait for navigation
    try:
        await page.wait_for_load_state("networkidle", timeout=15_000)
    except Exception:
        await asyncio.sleep(3)

    # Verify: password field should be gone after login
    pw_visible = await page.query_selector("input[type='password']")
    if pw_visible:
        return f"⚠️ Login may have failed for {site_name} (password field still visible)"

    return f"✅ Logged in to {site_name}"


# ══════════════════════════════════════════════════════════════
# PAGE SURVEY
# ══════════════════════════════════════════════════════════════

async def survey_page(page, tab_scan: bool = True) -> Dict[str, Any]:
    """
    Comprehensive page survey using BeautifulSoup + Tab key scan.
    """
    from bs4 import BeautifulSoup

    html  = await page.content()
    soup  = BeautifulSoup(html, "html.parser")
    title = await page.title()
    url   = page.url

    headings = [h.get_text(strip=True) for h in soup.find_all(["h1","h2","h3"])[:12]]

    links = [
        {"text": a.get_text(strip=True)[:60], "href": a.get("href","")[:120]}
        for a in soup.find_all("a", href=True) if a.get_text(strip=True)
    ][:25]

    buttons = [
        b.get_text(strip=True)[:60]
        for b in soup.find_all("button") if b.get_text(strip=True)
    ][:15]

    forms = []
    for form in soup.find_all("form")[:5]:
        inputs = [
            {
                "tag":         i.name,
                "type":        i.get("type","text"),
                "name":        i.get("name","") or i.get("id",""),
                "placeholder": i.get("placeholder",""),
            }
            for i in form.find_all(["input","textarea","select","button"])
        ]
        forms.append({"action": form.get("action",""), "inputs": inputs})

    tables = []
    for tbl in soup.find_all("table")[:3]:
        rows   = tbl.find_all("tr")
        sample = [
            [td.get_text(strip=True) for td in r.find_all(["th","td"])]
            for r in rows[:3]
        ]
        tables.append(sample)

    body_text = re.sub(r"\s+", " ", soup.get_text(separator=" ", strip=True))[:800]

    tab_fields = []
    if tab_scan:
        try:
            nav = TabNavigator(page)
            tab_fields = await nav.get_all_focusable()
            print(f"[Survey] Tab scan found {len(tab_fields)} focusable elements")
        except Exception as e:
            print(f"[Survey] Tab scan skipped: {e}")

    return {
        "url":        url,
        "title":      title,
        "headings":   headings,
        "links":      links,
        "buttons":    buttons,
        "forms":      forms,
        "tables":     tables,
        "text":       body_text,
        "tab_fields": tab_fields,
    }


# ══════════════════════════════════════════════════════════════
# RETRY HELPER
# ══════════════════════════════════════════════════════════════

async def with_retry(coro_fn: Callable, retries: int = 3, delay: float = 1.5) -> Any:
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            return await coro_fn()
        except Exception as e:
            last_exc = e
            print(f"[Retry] Attempt {attempt}/{retries} failed: {e}")
            await asyncio.sleep(delay * attempt)
    raise RuntimeError(f"All {retries} attempts failed: {last_exc}") from last_exc


# ══════════════════════════════════════════════════════════════
# PAGE CHANGE MONITOR
# ══════════════════════════════════════════════════════════════

class PageChangeMonitor:
    """Polls for URL or DOM changes and fires an async callback."""

    def __init__(self, page, on_change: Optional[Callable] = None):
        self.page       = page
        self.on_change  = on_change
        self._last_url  = ""
        self._last_hash = ""
        self._running   = False

    async def start(self, interval: float = 1.0):
        self._running   = True
        self._last_url  = self.page.url
        self._last_hash = await self._dom_hash()
        asyncio.create_task(self._loop(interval))
        print("[Monitor] Page change monitor started")

    def stop(self):
        self._running = False
        print("[Monitor] Page change monitor stopped")

    async def _dom_hash(self) -> str:
        try:
            txt = await self.page.evaluate(
                "document.body ? document.body.innerText.slice(0,2000) : ''"
            )
            return str(hash(txt))
        except Exception:
            return ""

    async def _loop(self, interval: float):
        while self._running:
            await asyncio.sleep(interval)
            try:
                cur_url  = self.page.url
                cur_hash = await self._dom_hash()
                if cur_url != self._last_url or cur_hash != self._last_hash:
                    event = {
                        "type": "url_change" if cur_url != self._last_url else "dom_change",
                        "from": self._last_url,
                        "to":   cur_url,
                    }
                    self._last_url  = cur_url
                    self._last_hash = cur_hash
                    print(f"[Monitor] {event['type']} → {cur_url}")
                    if self.on_change:
                        await self.on_change(event)
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════
# HEURISTIC INSTRUCTION PARSER  (100% free, no LLM needed)
# ══════════════════════════════════════════════════════════════

def parse_instruction(instruction: str) -> List[Dict[str, Any]]:
    """
    Converts a natural language instruction into typed action steps.
    Pure regex/string matching — zero cost, zero API calls.

    Supported phrases:
      go to / open / visit / navigate to <url>
      search for <term>
      click [on] <target>
      fill <field> with <value>
      type <value> in[to] <field>
      login / log in / sign in
      scroll down / up / to bottom / to top / to <element>
      screenshot / take a photo / capture
      survey / scan page / analyze page
      extract tables / links / text
      wait <N> seconds
      bypass cookies / dismiss / accept cookies
      drag <source> to <target>
      go back / go forward
      reload / refresh
      tab fields / list fields / focusable
    """
    inst  = instruction.strip()
    lower = inst.lower()

    # Navigate
    m = re.match(r"(?:go to|open|navigate to|visit)\s+(.+)", lower)
    if m:
        url = m.group(1).strip()
        if not url.startswith("http"):
            url = "https://" + url
        return [
            {"action": "navigate", "url": url},
            {"action": "bypass_overlays"},
        ]

    # Search
    m = re.match(r"search(?:\s+for)?\s+(.+)", lower)
    if m:
        return [{"action": "search", "term": m.group(1).strip()}]

    # Fill:  "fill <field> with <value>"
    m = re.match(r"fill\s+(.+?)\s+with\s+(.+)", lower)
    if m:
        return [{"action": "fill", "target": m.group(1).strip(), "value": m.group(2).strip()}]

    # Type:  "type <value> in[to] <field>"
    m = re.match(r"type\s+(.+?)\s+in(?:to)?\s+(.+)", lower)
    if m:
        return [{"action": "fill", "target": m.group(2).strip(), "value": m.group(1).strip()}]

    # Click
    m = re.match(r"click(?:\s+on)?\s+(.+)", lower)
    if m:
        return [{"action": "click", "target": m.group(1).strip()}]

    # Login
    if re.search(r"\blog\s*in\b|\blogin\b|\bsign\s*in\b", lower):
        return [{"action": "login"}]

    # Scroll
    if re.search(r"scroll\s*(to\s*)?(bottom|down)", lower):
        return [{"action": "scroll", "direction": "bottom"}]
    if re.search(r"scroll\s*(to\s*)?(top|up)", lower):
        return [{"action": "scroll", "direction": "top"}]
    m = re.match(r"scroll\s+to\s+(.+)", lower)
    if m:
        return [{"action": "scroll", "direction": "element", "target": m.group(1).strip()}]

    # Screenshot
    if re.search(r"\bscreenshot\b|\btake a photo\b|\bcapture\b", lower):
        return [{"action": "screenshot"}]

    # Survey
    if re.search(r"\bsurvey\b|\bscan page\b|\banalyze page\b|\bwhat.s on\b", lower):
        return [{"action": "survey"}]

    # Extract
    m = re.match(r"extract\s+(.+)", lower)
    if m:
        what = m.group(1).strip()
        kind = "tables" if "table" in what else "links" if "link" in what else "text"
        return [{"action": "extract", "what": kind}]
    if re.search(r"\bget info\b|\bscrape\b|\bfetch data\b", lower):
        return [{"action": "extract", "what": "text"}]

    # Wait
    m = re.search(r"wait\s+(\d+(?:\.\d+)?)\s*(?:second|sec|s)", lower)
    if m:
        return [{"action": "wait", "seconds": float(m.group(1))}]

    # Bypass
    if re.search(r"\bbypass\b|\bdismiss\b|\baccept\s+cook|\bclose\s+banner\b|\bcookie\b", lower):
        return [{"action": "bypass_overlays"}]

    # Drag
    m = re.match(r"drag\s+(.+?)\s+to\s+(.+)", lower)
    if m:
        return [{"action": "drag", "source": m.group(1).strip(), "target": m.group(2).strip()}]

    # Navigation history
    if re.search(r"\bgo\s+back\b|\bback\b", lower):
        return [{"action": "back"}]
    if re.search(r"\bgo\s+forward\b|\bforward\b", lower):
        return [{"action": "forward"}]
    if re.search(r"\breload\b|\brefresh\b", lower):
        return [{"action": "refresh"}]

    # Tab field scan
    if re.search(r"\btab\s*fields\b|\bfocusable\b|\blist\s*fields\b", lower):
        return [{"action": "tab_scan"}]

    return []   # unrecognised


# ══════════════════════════════════════════════════════════════
# MAIN AUTOMATION CLASS
# ══════════════════════════════════════════════════════════════

class IntelligentWebAutomation:
    """
    Natural language web automation.
    100% free — Tab-based field detection, heuristic parser, CDP BrowserView.
    """

    def __init__(self, browser=None):
        self.browser = browser or browser_agent
        self.monitor: Optional[PageChangeMonitor] = None

    @property
    def _page(self):
        return self.browser.page

    # ── Overlay bypass ─────────────────────────────────────────
    async def dismiss_overlays(self) -> str:
        await self.browser.ensure_started()
        n = await bypass_overlays(self._page)
        return f"✅ Dismissed {n} overlay(s)"

    # ── Login ──────────────────────────────────────────────────
    async def login(self, site_name: Optional[str] = None) -> str:
        await self.browser.ensure_started()
        site = site_name or self._page.url
        return await auto_login(self._page, site)

    # ── Survey ─────────────────────────────────────────────────
    async def survey(self) -> Dict[str, Any]:
        await self.browser.ensure_started()
        data = await survey_page(self._page)
        self._print_survey(data)
        return data

    def _print_survey(self, d: Dict[str, Any]):
        tf = d.get("tab_fields", [])
        print(f"\n{'═'*64}")
        print(f"  📄 PAGE SURVEY")
        print(f"  Title    : {d['title']}")
        print(f"  URL      : {d['url']}")
        print(f"  Headings : {d['headings'][:5]}")
        print(f"  Buttons  : {d['buttons'][:8]}")
        print(f"  Links    : {len(d['links'])} found")
        print(f"  Forms    : {len(d['forms'])} found")
        print(f"  Tables   : {len(d['tables'])} found")
        print(f"  Tab fields ({len(tf)} interactive elements):")
        for el in tf[:20]:
            label = (
                el.get("placeholder") or el.get("ariaLabel") or
                el.get("name")        or el.get("text")      or
                el.get("id")          or "—"
            )
            print(f"    [{el['tag']:8s}] type={el.get('type','-'):<12} → {label[:45]}")
        print(f"{'═'*64}\n")

    # ── Tab field scan only ────────────────────────────────────
    async def tab_scan(self) -> List[Dict[str, Any]]:
        await self.browser.ensure_started()
        nav    = TabNavigator(self._page)
        fields = await nav.get_all_focusable()
        print(f"\n[Tab Scan] {len(fields)} focusable element(s):")
        for i, el in enumerate(fields, 1):
            label = (
                el.get("placeholder") or el.get("ariaLabel") or
                el.get("name")        or el.get("text")      or
                el.get("id")          or "—"
            )
            print(f"  {i:02d}. [{el['tag']:8s}] type={el.get('type','-'):<12} → {label[:50]}")
        return fields

    # ── Extraction ─────────────────────────────────────────────
    async def extract_info(self, what: str = "text") -> Any:
        await self.browser.ensure_started()
        if what == "links":
            return await self.browser.extract_links()
        if what == "tables":
            return await self.browser.extract_table()
        if what == "survey":
            return await self.survey()
        return await self.browser.extract_text("body")

    # ── Search (Tab-first, CSS fallback) ───────────────────────
    async def search(self, term: str) -> str:
        await self.browser.ensure_started()
        nav = TabNavigator(self._page)

        for hint in ["search", "query", "q", "find", "keyword"]:
            found = await nav.tab_to_field(hint)
            if found:
                await nav.type_in_focused(term)
                await asyncio.sleep(0.3)
                await self._page.keyboard.press("Enter")
                try:
                    await self._page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:
                    await asyncio.sleep(2)
                return f"✅ Searched for '{term}' (Tab)"

        # CSS fallback
        for sel in [
            "input[name='q']", "input[type='search']",
            "input[name='search']", "input[placeholder*='Search' i]",
            "#search", ".search-input", "input[role='searchbox']",
        ]:
            try:
                el = await self._page.query_selector(sel)
                if el and await el.is_visible():
                    await self._page.fill(sel, term)
                    await self._page.press(sel, "Enter")
                    return f"✅ Searched for '{term}' (CSS)"
            except Exception:
                continue

        return f"❌ Could not find search box for: '{term}'"

    # ── Smart click (Tab → Enter, then text fallback) ──────────
    async def smart_click(self, target: str) -> str:
        await self.browser.ensure_started()
        nav = TabNavigator(self._page)

        found = await nav.tab_to_field(target.lower())
        if found:
            await self._page.keyboard.press("Enter")
            return f"✅ Tab-clicked: '{target}'"

        for method in [f"text={target}", f"button:has-text('{target}')", f"a:has-text('{target}')"]:
            try:
                await self._page.click(method)
                return f"✅ Clicked: '{target}'"
            except Exception:
                continue

        return f"❌ Could not click: '{target}'"

    # ── Smart fill (Tab-based) ─────────────────────────────────
    async def smart_fill(self, target: str, value: str) -> str:
        await self.browser.ensure_started()
        nav = TabNavigator(self._page)
        return await nav.fill_by_tab(target, value)

    # ── Drag ───────────────────────────────────────────────────
    async def drag(self, source: str, target: str) -> str:
        await self.browser.ensure_started()
        try:
            src = await self._page.query_selector(source)
            tgt = await self._page.query_selector(target)
            if not src or not tgt:
                return "❌ Source or target element not found"
            sb = await src.bounding_box()
            tb = await tgt.bounding_box()
            await self._page.mouse.move(sb["x"]+sb["width"]/2, sb["y"]+sb["height"]/2)
            await self._page.mouse.down()
            await asyncio.sleep(0.3)
            await self._page.mouse.move(tb["x"]+tb["width"]/2, tb["y"]+tb["height"]/2, steps=25)
            await asyncio.sleep(0.2)
            await self._page.mouse.up()
            return f"✅ Dragged '{source}' → '{target}'"
        except Exception as e:
            return f"❌ Drag failed: {e}"

    # ── Scroll ─────────────────────────────────────────────────
    async def scroll(self, direction: str = "bottom", target: Optional[str] = None) -> str:
        await self.browser.ensure_started()
        if target:
            return await self.browser.scroll_to_element(target)
        if direction == "bottom":
            return await self.browser.scroll_to_bottom()
        if direction == "top":
            await self._page.evaluate("window.scrollTo(0,0)")
            return "✅ Scrolled to top"
        return f"⚠️ Unknown scroll direction: {direction}"

    # ── Page change monitor ────────────────────────────────────
    async def watch_page(self, callback: Optional[Callable] = None, interval: float = 1.0) -> str:
        await self.browser.ensure_started()
        self.monitor = PageChangeMonitor(self._page, on_change=callback)
        await self.monitor.start(interval)
        return "✅ Page monitor started"

    def stop_watching(self) -> str:
        if self.monitor:
            self.monitor.stop()
        return "✅ Page monitor stopped"

    # ── Step executor ──────────────────────────────────────────
    async def _execute_step(self, step: Dict[str, Any]) -> str:
        action = step.get("action", "")

        if action == "navigate":
            result = await self.browser.navigate(step["url"])
            await asyncio.sleep(2)
            await bypass_overlays(self._page)
            return result

        elif action == "bypass_overlays":
            return await self.dismiss_overlays()

        elif action == "login":
            return await self.login(step.get("site"))

        elif action == "search":
            return await self.search(step["term"])

        elif action == "click":
            return await self.smart_click(step["target"])

        elif action == "fill":
            return await self.smart_fill(step["target"], step.get("value", ""))

        elif action == "scroll":
            return await self.scroll(step.get("direction", "bottom"), step.get("target"))

        elif action == "wait":
            secs = float(step.get("seconds", 2))
            await asyncio.sleep(secs)
            return f"✅ Waited {secs}s"

        elif action == "extract":
            what   = step.get("what", "text")
            result = await self.extract_info(what)
            print(f"[Extract:{what}] {str(result)[:500]}")
            return f"✅ Extracted {what}"

        elif action == "screenshot":
            return await self.browser.screenshot(path=step.get("path"))

        elif action == "survey":
            await self.survey()
            return "✅ Survey complete"

        elif action == "tab_scan":
            await self.tab_scan()
            return "✅ Tab scan complete"

        elif action == "drag":
            return await self.drag(step.get("source", ""), step.get("target", ""))

        elif action == "back":
            return await self.browser.go_back()

        elif action == "forward":
            return await self.browser.go_forward()

        elif action == "refresh":
            return await self.browser.refresh()

        else:
            return f"⚠️ Unknown action: {action}"

    # ── MAIN ENTRY POINT ───────────────────────────────────────
    async def perform_action(self, instruction: str) -> List[str]:
        """
        Execute a natural language instruction end-to-end.

        Pipeline:
          1. Parse instruction with free heuristic parser
          2. Execute each step with 3x retry
          3. Auto-detect login walls and handle them
          4. Return list of result strings
        """
        await self.browser.ensure_started()
        print(f"\n[Agent] ▶ {instruction}")

        steps = parse_instruction(instruction)

        if not steps:
            print(f"[Agent] ⚠️ Could not parse: '{instruction}'")
            print("[Agent] Supported: go to <url> | search for <x> | click <x>")
            print("                   fill <field> with <value> | login | survey")
            print("                   screenshot | scroll down/up | extract tables/links")
            print("                   wait 2 seconds | tab fields | drag <a> to <b>")
            return [f"⚠️ Unrecognised instruction: '{instruction}'"]

        results = []
        for i, step in enumerate(steps, 1):
            print(f"[Step {i}/{len(steps)}] {step}")
            try:
                result = await with_retry(
                    lambda s=step: self._execute_step(s),
                    retries=3,
                    delay=1.0,
                )
                results.append(result)
                print(f"  → {result}")

                # Auto-detect login wall mid-task
                try:
                    pw = await self._page.query_selector("input[type='password']")
                    if pw and await pw.is_visible():
                        print("[Agent] 🔐 Login wall detected — initiating auto-login")
                        lr = await self.login()
                        results.append(lr)
                        await self.dismiss_overlays()
                except Exception:
                    pass

            except Exception as e:
                err = f"❌ Step failed after retries: {e}"
                results.append(err)
                print(f"  → {err}")

        return results

    # ── Smart Web Query (Ephemeral Playwright Chromium) ───────
    async def smart_web_query(
        self,
        url: str,
        search_term: Optional[str] = None,
        click_first_result: bool = False,
        browser_pref: Optional[str] = None,
    ) -> str:
        """
        Full real-browser automation via a fresh Playwright Chromium instance.

        Uses its own ephemeral browser (headless=False, visible on screen) so it
        NEVER conflicts with the user's running Chrome (no profile lock issues).

        Flow:
          1. Launch bundled Playwright Chromium (visible window, fresh temp profile)
          2. Navigate to URL
          3. Dismiss cookie / notification overlays
          4. Find search box: site-specific CSS selectors → generic CSS → Tab-navigator
          5. Click search box → type search_term → press Enter
          6. Wait for results page
          7. Optionally click first visible result element
          8. Close browser, return descriptive result string
        """
        # ── Site-specific search box selectors (priority order) ──
        SEARCH_SELECTORS = [
            "input#twotabsearchtextbox",           # Amazon
            "input[name='q'][class*='search']",    # Flipkart
            "textarea[name='q']",                  # Google
            "input#search",                        # YouTube
            "input[name='search_query']",          # YouTube alt
            "input#searchInput",                   # Wikipedia
            "input[name='search']",                # Wikipedia alt
            "input[type='search']",                # Generic HTML5
            "input[type='text'][name='q']",        # Generic q
            "input[placeholder*='Search' i]",      # Placeholder hints
            "input[placeholder*='search' i]",
            "input[aria-label*='Search' i]",
            "[role='searchbox']",
            "input[name='keyword']",
            "input[type='text']:visible",          # Last resort: first visible text input
        ]

        # ── Site-specific first-result selectors ──
        FIRST_RESULT_SELECTORS = [
            ".s-result-item:not(.AdHolder) h2 a",  # Amazon
            ".s-search-results .s-result-item h2 a",
            "._1AtVbE ._30jeq3",                    # Flipkart
            "a._1fQZEK",
            "#search .g a:has(h3)",                 # Google
            "#contents ytd-video-renderer h3 a",    # YouTube
            "ytd-video-renderer #video-title",
            "article a",
            ".product a",
            "h2 a",
            "h3 a",
        ]

        log_prefix = "[SmartWebQuery]"
        steps_done: List[str] = []

        if not url.startswith("http"):
            url = "https://" + url

        print(f"{log_prefix} Starting browser → {url}")

        # ── Launch a fresh Playwright browser instance ──
        from playwright.async_api import async_playwright
        import os as _os

        pw = await async_playwright().start()
        browser = None
        try:
            LAUNCH_ARGS = [
                "--start-maximized",
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ]

            pref = (browser_pref or "chrome").lower().strip()
            local_app_data = _os.environ.get("LOCALAPPDATA", _os.path.join(_os.path.expanduser("~"), "AppData", "Local"))

            # ── Brave: must use executable_path (not channel) ──
            if pref == "brave":
                brave_candidates = [
                    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                    r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
                    _os.path.join(local_app_data, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
                ]
                brave_exe = next((p for p in brave_candidates if _os.path.exists(p)), None)
                if brave_exe:
                    print(f"{log_prefix} 🦁 Launching Brave: {brave_exe}")
                    browser = await pw.chromium.launch(
                        headless=False,
                        executable_path=brave_exe,
                        args=LAUNCH_ARGS,
                    )
                else:
                    print(f"{log_prefix} ⚠️ Brave not found, falling back to Chrome")
                    pref = "chrome"

            # ── Edge ──
            if pref in ("edge", "msedge") and browser is None:
                try:
                    browser = await pw.chromium.launch(headless=False, channel="msedge", args=LAUNCH_ARGS)
                    print(f"{log_prefix} 🌐 Launched: Microsoft Edge")
                except Exception as e:
                    print(f"{log_prefix} ⚠️ Edge failed ({e}), falling back to Chrome")
                    pref = "chrome"

            # ── Chrome (default) ──
            if pref == "chrome" and browser is None:
                try:
                    browser = await pw.chromium.launch(headless=False, channel="chrome", args=LAUNCH_ARGS)
                    print(f"{log_prefix} 🌐 Launched: Google Chrome")
                except Exception as e:
                    print(f"{log_prefix} ⚠️ Chrome failed ({e}), using bundled Chromium")
                    browser = await pw.chromium.launch(headless=False, args=LAUNCH_ARGS)
                    print(f"{log_prefix} Launched: bundled Chromium (fallback)")

            ctx  = await browser.new_context(viewport={"width": 1366, "height": 768})
            page = await ctx.new_page()
            page.set_default_timeout(20_000)

            # ── 1. Navigate ──
            print(f"{log_prefix} Navigating to {url}")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=25_000)
            except Exception as nav_err:
                print(f"{log_prefix} goto warning: {nav_err}")
            await asyncio.sleep(2)

            steps_done.append(f"✅ Opened {url}")

            # ── 2. Dismiss overlays ──
            await bypass_overlays(page)
            await asyncio.sleep(0.8)

            if not search_term:
                # Just navigate — keep browser open a moment so user sees it
                await asyncio.sleep(3)
                return " | ".join(steps_done)

            # ── 3. Find search box ──
            search_box = None
            used_selector = None

            # Broader and more generic selectors
            EXTENDED_SEARCH_SELECTORS = SEARCH_SELECTORS + [
                "input[name*='search' i]",
                "input[id*='search' i]",
                "input[class*='search' i]",
                "div[role='search'] input",
                "form[action*='search' i] input",
                "input[placeholder*='find' i]",
                "input[aria-label*='find' i]",
                "nav input",
                "header input",
            ]

            for sel in EXTENDED_SEARCH_SELECTORS:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        # Additional check: ensure it's not a button
                        tag = await el.evaluate("node => node.tagName.toLowerCase()")
                        if tag in ["input", "textarea"]:
                            search_box = el
                            used_selector = sel
                            print(f"{log_prefix} Search box found: {sel}")
                            break
                except Exception:
                    continue

            # Dynamic Click Recovery: 
            # Some sites require clicking a search icon first to show the input
            if not search_box:
                SEARCH_ICONS = [
                    "button[aria-label*='search' i]",
                    "a[aria-label*='search' i]",
                    "svg[class*='search' i]",
                    ".search-icon",
                    "#search-icon",
                    "button:has(svg[class*='search' i])",
                ]
                for icon_sel in SEARCH_ICONS:
                    try:
                        icon = await page.query_selector(icon_sel)
                        if icon and await icon.is_visible():
                            print(f"{log_prefix} Search icon found, clicking to reveal bar: {icon_sel}")
                            await icon.click()
                            await asyncio.sleep(0.8)
                            # Retry basic selectors
                            for sel in SEARCH_SELECTORS[:5]: 
                                el = await page.query_selector(sel)
                                if el and await el.is_visible():
                                    search_box = el
                                    used_selector = f"{icon_sel} -> {sel}"
                                    break
                            if search_box: break
                    except Exception:
                        continue

            # Tab-navigator fallback
            if not search_box:
                print(f"{log_prefix} CSS lookup failed → Tab-navigator scan")
                nav = TabNavigator(page)
                for hint in ["search", "query", "q", "find", "keyword"]:
                    found = await nav.tab_to_field(hint)
                    if found:
                        await page.keyboard.press("Control+a")
                        await asyncio.sleep(0.1)
                        await page.keyboard.type(search_term, delay=60)
                        await asyncio.sleep(0.3)
                        await page.keyboard.press("Enter")
                        steps_done.append(
                            f"✅ Typed '{search_term}' via Tab-navigator (hint: {hint})"
                        )
                        search_box = "TAB_DONE"
                        break

            # Interact with CSS-found search box
            if search_box and search_box != "TAB_DONE":
                try:
                    await search_box.scroll_into_view_if_needed()
                    await search_box.click()
                    await asyncio.sleep(0.4)
                    await page.keyboard.press("Control+a")
                    await asyncio.sleep(0.1)
                    await search_box.type(search_term, delay=55)
                    await asyncio.sleep(0.3)
                    await page.keyboard.press("Enter")
                    steps_done.append(
                        f"✅ Typed '{search_term}' in search box [{used_selector}]"
                    )
                    print(f"{log_prefix} Typed '{search_term}' → Enter")
                except Exception as e:
                    steps_done.append(f"⚠️ Search box interaction failed: {e}")

            elif not search_box:
                steps_done.append(f"❌ No search box found on {url}")
                await asyncio.sleep(2)
                return " | ".join(steps_done)

            # ── 4. Wait for results ──
            try:
                await page.wait_for_load_state("networkidle", timeout=12_000)
            except Exception:
                await asyncio.sleep(3)
            print(f"{log_prefix} Results page: {page.url}")

            if not click_first_result:
                # Keep browser open so user can see results
                await asyncio.sleep(5)
                return " | ".join(steps_done)

            # ── 5. Click first result ──
            await asyncio.sleep(0.8)
            clicked = False

            for sel in FIRST_RESULT_SELECTORS:
                try:
                    elements = await page.query_selector_all(sel)
                    for el in elements:
                        if await el.is_visible():
                            await el.scroll_into_view_if_needed()
                            await asyncio.sleep(0.3)
                            await el.click()
                            clicked = True
                            steps_done.append(f"✅ Clicked first result [{sel}]")
                            print(f"{log_prefix} Clicked first result: {sel}")
                            break
                    if clicked:
                        break
                except Exception:
                    continue

            # Generic link fallback
            if not clicked:
                try:
                    for link in await page.query_selector_all("a[href]"):
                        if not await link.is_visible():
                            continue
                        href = (await link.get_attribute("href") or "").strip()
                        if not href or href.startswith(("#", "javascript:", "/")):
                            continue
                        text = (await link.inner_text() or "").strip()
                        if len(text) > 5:
                            await link.scroll_into_view_if_needed()
                            await asyncio.sleep(0.3)
                            await link.click()
                            steps_done.append(
                                f"✅ Clicked first link (generic): '{text[:50]}'"
                            )
                            clicked = True
                            break
                except Exception as e:
                    print(f"{log_prefix} Generic link click failed: {e}")

            if not clicked:
                steps_done.append("⚠️ Could not click any result link")

            # Wait on the result page so user can see it
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=10_000)
            except Exception:
                await asyncio.sleep(2)

            final_url = page.url
            print(f"{log_prefix} Final URL: {final_url}")

            # ── 6. Scrape product/result page for rich structured data ──
            product_data: Dict[str, Any] = {}
            try:
                html = await page.content()
                from bs4 import BeautifulSoup as _BS
                soup = _BS(html, "html.parser")

                def _txt(sel: str) -> str:
                    el = soup.select_one(sel)
                    return el.get_text(strip=True) if el else ""

                # ── Title ──
                title = (
                    _txt("#productTitle") or
                    _txt("h1.product-title") or
                    _txt("h1") or
                    await page.title()
                )

                # ── Price ──
                price = (
                    _txt(".a-price .a-offscreen") or
                    _txt(".a-price-whole") or
                    _txt("[data-asin-price]") or
                    _txt(".price") or ""
                )
                if not price:
                    # Try JS price span
                    price_el = soup.select_one("span.a-price")
                    if price_el:
                        price = price_el.get_text(strip=True).replace("\n", "")

                # ── Rating ──
                rating = (
                    _txt("#acrPopover .a-size-base.a-color-base") or
                    _txt("span.a-icon-alt") or
                    _txt("[data-hook='rating-out-of-text']") or ""
                )
                if rating and " out of" in rating:
                    rating = rating.split(" out of")[0].strip()

                # ── Review count ──
                reviews = (
                    _txt("#acrCustomerReviewText") or
                    _txt("[data-hook='total-review-count']") or ""
                )

                # ── Product image ──
                img_url = ""
                img_el = soup.select_one("#landingImage, #imgBlkFront, .product-image img")
                if img_el:
                    img_url = img_el.get("data-old-hires") or img_el.get("src") or ""

                # ── Key bullet specs (first 5) ──
                specs: List[str] = []
                for li in soup.select("#feature-bullets li span.a-list-item")[:6]:
                    t = li.get_text(strip=True)
                    if t and len(t) > 5:
                        specs.append(t)

                # ── Badge (e.g. "Overall Pick") ──
                badge = (
                    _txt(".ac-badge-wrapper .ac-badge-label") or
                    _txt("[data-cel-widget='acb_product_status_badge_label']") or ""
                )

                product_data = {
                    "title":   title,
                    "price":   price,
                    "rating":  rating,
                    "reviews": reviews,
                    "image":   img_url,
                    "specs":   specs,
                    "badge":   badge,
                    "url":     final_url,
                }
                print(f"{log_prefix} Scraped product: {title[:60]}")
            except Exception as scrape_err:
                print(f"{log_prefix} Scrape warning: {scrape_err}")

            await asyncio.sleep(5)   # Keep window visible for 5 s

        finally:
            try:
                if browser:
                    await browser.close()
            except Exception:
                pass

        # Return structured result so the frontend can render a rich card
        summary_text = " | ".join(steps_done) if steps_done else "✅ Done"
        if product_data:
            return {
                "summary": summary_text,
                "product": product_data,
                "url":     product_data.get("url", url),
            }
        return summary_text


    # ── Convenience helpers ────────────────────────────────────
    async def visit_and_survey(self, url: str) -> Dict[str, Any]:
        """Navigate → bypass overlays → full survey in one call."""
        await self.browser.navigate(url)
        await asyncio.sleep(2)
        await self.dismiss_overlays()
        await asyncio.sleep(1)
        return await self.survey()

    async def run_sequence(self, instructions: List[str]) -> Dict[str, List[str]]:
        """Run multiple natural language instructions in order."""
        results = {}
        for instr in instructions:
            results[instr] = await self.perform_action(instr)
        return results


# ══════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ══════════════════════════════════════════════════════════════

web_automation = IntelligentWebAutomation(browser_agent)
