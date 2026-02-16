import sys
import os
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

# Add backend to path
current_dir = os.getcwd()
backend_path = os.path.join(current_dir, 'backend')
if backend_path not in sys.path:
    sys.path.append(backend_path)

# Mock playwright and pandas before importing browser
with patch.dict('sys.modules', {'playwright.sync_api': MagicMock(), 'pandas': MagicMock()}):
    from backend.capabilities import browser

class TestSmartScrape(unittest.TestCase):
    def setUp(self):
        # Setup mocks
        self.mock_playwright = MagicMock()
        self.mock_browser = MagicMock()
        self.mock_context = MagicMock()
        self.mock_page = MagicMock()
        
        self.mock_playwright.chromium.launch.return_value = self.mock_browser
        self.mock_browser.new_context.return_value = self.mock_context
        self.mock_context.new_page.return_value = self.mock_page
        
        # Patch sync_playwright in browser module
        self.playwright_patcher = patch('backend.capabilities.browser.sync_playwright', return_value=MagicMock(__enter__=lambda x: self.mock_playwright))
        self.playwright_patcher.start()
        
        # Patch pandas
        self.pd_patcher = patch('backend.capabilities.browser.pd')
        self.mock_pd = self.pd_patcher.start()

    def tearDown(self):
        self.playwright_patcher.stop()
        self.pd_patcher.stop()

    def test_smart_scrape_navigation(self):
        # Test that smart_scrape attempts to find historical links
        
        # Mock locator for "Historical Data"
        mock_loc = MagicMock()
        mock_loc.count.return_value = 1
        mock_loc.first.is_visible.return_value = True
        
        self.mock_page.get_by_text.return_value = mock_loc
        
        # Call private sync method directly to avoid async complexity in test
        browser._orchestrate_web_task_sync("http://example.com", "smart_scrape", "10 days history")
        
        # Verify attempt to find link
        self.mock_page.get_by_text.assert_any_call("Historical Data", exact=False)
        # Verify click
        mock_loc.first.click.assert_called_once()

    def test_smart_scrape_filtering(self):
        # Mock no historical link found (stay on page)
        mock_loc = MagicMock()
        mock_loc.count.return_value = 0
        self.mock_page.get_by_text.return_value = mock_loc
        
        # Mock dataframe return
        mock_df = MagicMock()
        mock_df.size = 100
        mock_df.to_string.return_value = "date close price"
        mock_df.fillna.return_value = mock_df
        
        # Create 20 records
        records = [{"date": i, "close": 100} for i in range(20)]
        mock_df.to_dict.return_value = records
        
        self.mock_pd.read_html.return_value = [mock_df]
        
        # Run with "10 days" limit
        result = browser._orchestrate_web_task_sync("http://example.com", "smart_scrape", "10 days history")
        
        # Verify filtering to 10 records
        self.assertIn("Scraped 10 records", result["status"])

if __name__ == '__main__':
    unittest.main()
