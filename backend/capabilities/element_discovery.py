"""
Element Discovery System
=========================
Advanced element location strategies that don't rely on hardcoded selectors.
Uses multiple approaches: semantic analysis, accessibility tree, visual context, and LLM reasoning.
"""

from typing import Optional, List, Tuple
from playwright.sync_api import Page, Locator
import re


class ElementDiscovery:
    """
    Intelligent element finder using multiple strategies:
    1. Semantic/ARIA-based search (fastest, most reliable)
    2. Text-based proximity search
    3. Common UI pattern matching
    4. LLM-guided selector generation (fallback)
    """
    
    def __init__(self, page: Page):
        self.page = page
        
    def find_search_input(self, wait_for_load: bool = True, timeout: int = 10000) -> Optional[str]:
        """Find search input box using smart heuristics"""
        
        # Wait for page to be ready if requested
        if wait_for_load:
            try:
                self.page.wait_for_load_state("networkidle", timeout=5000)
            except:
                pass  # Continue even if timeout
        
        strategies = [
            # YouTube specific (try first for YouTube)
            'input#search, input[id="search"]',
            'input[name="search_query"]',
            'input[placeholder*="Search" i]',
            
            # 1. Semantic: aria-label or role
            'input[aria-label*="Search" i], input[aria-label*="search" i]',
            'input[role="searchbox"], input[role="combobox"]',
            'textarea[role="searchbox"], textarea[role="combobox"]',
            
            # 2. Type and name attributes
            'input[type="search"]',
            'input[name*="search" i], input[name*="q" i]',
            'input[name="q"], textarea[name="q"]',
            
            # 3. Placeholder text (aggressive)
            'input[placeholder*="Search" i]',
            'input[placeholder*="search" i]',
            'input[placeholder*="Find" i]',
            
            # 4. ID patterns (more variations)
            'input[id*="search" i]',
            '#searchInput, #search, #search-field, #searchbox',
            '#twotabsearchtextbox',  # Amazon
            
            # 5. Class patterns (more aggressive)
            'input[class*="search" i]',
            '.search-input, .searchbox, .search-field',
            
            # 6. Generic text/search inputs (last resort)
            'input[type="text"]:visible',
            'input:not([type]):visible',
        ]
        
        return self._try_selectors(strategies, "search input", timeout=timeout)
    
    def find_button(self, button_type: str) -> Optional[str]:
        """
        Find button by type: 'search', 'submit', 'login', 'add_to_cart', etc.
        
        Args:
            button_type: Type of button to find
        
        Returns:
            CSS selector or None
        """
        button_lower = button_type.lower().replace("_", " ")
        
        strategies = [
            # 1. Exact text match
            f'button:has-text("{button_type}")',
            f'input[type="submit"][value*="{button_type}" i]',
            
            # 2. ARIA label
            f'button[aria-label*="{button_type}" i]',
            f'[role="button"][aria-label*="{button_type}" i]',
            
            # 3. ID or class patterns
            f'button[id*="{button_type}" i], #{button_type}, #{button_type}-btn',
            f'button[class*="{button_type}" i], .{button_type}-button',
            
            # 4. Generic patterns for common types
            '*[type="submit"], button[type="submit"]' if "submit" in button_lower else None,
        ]
        
        strategies = [s for s in strategies if s]  # Remove None values
        return self._try_selectors(strategies, f"button: {button_type}")
    
    def find_first_result(self) -> Optional[str]:
        """Find first search result or product"""
        strategies = [
            # 1. Semantic heading links
            'article a h2, article a h3, [role="article"] a h2',
            'h2 a, h3 a',
            
            # 2. Common result patterns
            '[data-component-type="s-search-result"] a, .search-result a',
            '.result a, .search-item a, .product a',
            
            # 3. Product cards
            '[class*="product" i] a[class*="title" i]',
            '[class*="item" i] a[class*="title" i]',
            
            # 4. Generic first clickable item with heading
            'main a h2, main a h3, #content a h2',
        ]
        
        return self._try_selectors(strategies, "first result")
    
    def find_price(self) -> Optional[str]:
        """Find price element"""
        strategies = [
            # 1. Semantic price attributes
            '[itemprop="price"], [data-price], [class*="price" i]',
            
            # 2. Common price classes
            '.price, .product-price, .sale-price, .current-price',
            
            # 3. Currency symbols (more specific)
            '*:has-text("₹"), *:has-text("$"), span:has-text("₹")',
            
            # 4. ARIA or role
            '[role="text"][aria-label*="price" i]',
        ]
        
        return self._try_selectors(strategies, "price")
    
    def find_rating(self) -> Optional[str]:
        """Find rating/review score"""
        strategies = [
            # 1. Semantic
            '[itemprop="ratingValue"], [data-rating]',
            
            # 2. ARIA
            '[aria-label*="rating" i], [aria-label*="star" i]',
            
            # 3. Class patterns
            '[class*="rating" i], [class*="star" i], [class*="review" i]',
            
            # 4. Star icons
            'span:has-text("★"), span:has-text("⭐")',
        ]
        
        return self._try_selectors(strategies, "rating")
    
    def find_by_text(self, text: str, element_type: str = "*") -> Optional[str]:
        """
        Find element containing specific text.
        
        Args:
            text: Text to search for
            element_type: Tag name filter (*, button, a, span, etc.)
        
        Returns:
            CSS selector with :has-text()
        """
        # Escape special characters in text
        safe_text = text.replace('"', '\\"')
        
        strategies = [
            f'{element_type}:has-text("{safe_text}")',
            f'{element_type}[aria-label*="{safe_text}" i]',
            f'{element_type}[title*="{safe_text}" i]',
        ]
        
        return self._try_selectors(strategies, f"text: {text}")
    
    def find_form_field(self, field_name: str) -> Optional[str]:
        """
        Find form input field by name/type.
        
        Args:
            field_name: Field name like 'email', 'password', 'name', 'phone'
        
        Returns:
            CSS selector or None
        """
        field_lower = field_name.lower()
        
        # Map field names to input types
        type_map = {
            "email": "email",
            "password": "password",
            "phone": "tel",
            "tel": "tel",
            "search": "search",
        }
        
        input_type = type_map.get(field_lower, "text")
        
        strategies = [
            # 1. By type
            f'input[type="{input_type}"]',
            
            # 2. By name attribute
            f'input[name*="{field_lower}" i], input[name="{field_lower}"]',
            
            # 3. By ID
            f'input[id*="{field_lower}" i], #{field_lower}',
            
            # 4. By placeholder
            f'input[placeholder*="{field_name}" i]',
            
            # 5. By label (find label, then associated input)
            f'label:has-text("{field_name}") + input, label:has-text("{field_name}") input',
            
            # 6. Textarea for message/comments
            f'textarea[name*="{field_lower}" i], textarea[placeholder*="{field_name}" i]' if field_lower in ["message", "comment", "description"] else None,
        ]
        
        strategies = [s for s in strategies if s]
        return self._try_selectors(strategies, f"form field: {field_name}")
    
    def find_filter_option(self, filter_text: str) -> Optional[str]:
        """
        Find filter checkbox/option by text.
        
        Args:
            filter_text: Filter label text (e.g., "4 Stars & Up", "Under ₹50,000")
        
        Returns:
            Selector for the filter element
        """
        strategies = [
            # 1. Clickable links with text
            f'a:has-text("{filter_text}")',
            
            # 2. Checkbox labels
            f'label:has-text("{filter_text}")',
            f'input[type="checkbox"] + label:has-text("{filter_text}")',
            
            # 3. Filter buttons
            f'button:has-text("{filter_text}")',
            
            # 4. Div or span that's clickable
            f'div[role="button"]:has-text("{filter_text}")',
            f'span[role="button"]:has-text("{filter_text}")',
            
            # 5. Generic clickable with filter text
            f'*[class*="filter" i]:has-text("{filter_text}")',
        ]
        
        return self._try_selectors(strategies, f"filter: {filter_text}")
    
    def find_add_to_cart_button(self) -> Optional[str]:
        """Find 'Add to Cart' or 'Buy Now' button"""
        strategies = [
            # 1. Exact text matches
            'button:has-text("Add to Cart")',
            'button:has-text("ADD TO CART")',
            'input[type="submit"]:has-text("Add to Cart")',
            
            # 2. ID patterns
            '#add-to-cart-button, #add-to-cart, button[id*="add-to-cart" i]',
            
            # 3. Buy Now as fallback
            'button:has-text("Buy Now")',
            'button:has-text("BUY NOW")',
            
            # 4. ARIA or data attributes
            'button[aria-label*="add to cart" i]',
            'button[data-action*="add-to-cart" i]',
            
            # 5. Class patterns
            'button[class*="add-to-cart" i], .add-to-cart-button',
        ]
        
        return self._try_selectors(strategies, "add to cart button")
    
    def find_by_llm(self, element_description: str) -> Optional[str]:
        """
        Use LLM to analyze page and find element (fallback strategy).
        
        Args:
            element_description: What to find (e.g., "search button", "price")
        
        Returns:
            CSS selector or None
        """
        try:
            from llm.agent_llm import find_element
            
            # Get simplified page HTML
            page_html = self.page.content()
            
            selector = find_element(page_html, element_description)
            
            if selector:
                # Verify selector works
                if self._verify_selector(selector):
                    print(f"[ElementDiscovery] LLM found: {selector} for '{element_description}'")
                    return selector
            
            return None
            
        except Exception as e:
            print(f"[ElementDiscovery] LLM search failed: {e}")
            return None
    
    def _try_selectors(self, selectors: List[str], element_desc: str, timeout: int = 5000) -> Optional[str]:
        """
        Try multiple selectors in order, return first that works.
        
        Args:
            selectors: List of CSS selectors to try
            element_desc: Description for logging
            timeout: Timeout in milliseconds for each selector
        
        Returns:
            First working selector or None
        """
        for i, selector in enumerate(selectors):
            if self._verify_selector(selector, timeout=timeout):
                print(f"[ElementDiscovery] Found {element_desc}: {selector} (strategy {i+1}/{len(selectors)})")
                return selector
        
        print(f"[ElementDiscovery] ❌ Could not find {element_desc} after trying {len(selectors)} strategies")
        return None
    
    def _verify_selector(self, selector: str, timeout: int = 5000) -> bool:
        """Check if selector finds at least one visible and interactable element"""
        try:
            locator = self.page.locator(selector).first
            # Wait for element to be visible
            locator.wait_for(state="visible", timeout=timeout)
            # Check if it's actually visible (double check)
            return locator.is_visible()
        except Exception as e:
            # Silent fail - this is expected for non-matching selectors
            return False


# Helper function for backward compatibility
def create_element_discovery(page: Page) -> ElementDiscovery:
    """Factory function to create ElementDiscovery instance"""
    return ElementDiscovery(page)
