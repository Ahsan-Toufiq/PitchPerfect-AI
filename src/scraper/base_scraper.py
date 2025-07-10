"""Base scraper class for PitchPerfect AI."""

import csv
import time
import requests
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Iterator, Optional, List
from datetime import datetime

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from ..utils import get_logger, LoggerMixin, validate_business_data, validate_url, validate_phone
from ..database.operations import LeadOperations
from ..utils.proxy_rotation import proxy_rotator, ua_rotator, stealth_headers, human_delay


class ScrapingError(Exception):
    """Custom exception for scraping errors."""
    pass


class BaseScraper(ABC, LoggerMixin):
    """Base class for all scrapers."""
    
    def __init__(self):
        """Initialize base scraper."""
        self.settings = self._get_settings()
        self.source_name = self.__class__.__name__.replace('Scraper', '').lower()
        self.scraped_count = 0
        self.consecutive_failures = 0
        self.max_failures = 3
        
        # Initialize stealth components
        self.session = None
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.proxy = None
        self.user_agent = None
        
        self.logger.info(f"Initialized {self.source_name} scraper")
    
    def _get_settings(self):
        """Get settings (to be implemented by subclasses)."""
        from ..config import get_settings
        return get_settings()
    
    def _setup_session(self):
        """Setup requests session with stealth headers."""
        if not self.session:
            self.session = requests.Session()
            self.user_agent = ua_rotator.get_user_agent()
            self.session.headers.update(stealth_headers.get_headers())
            self.session.headers.update({"User-Agent": self.user_agent})
            # Try to get a working proxy
            self.proxy = proxy_rotator.get_working_proxy()
            if self.proxy:
                self.session.proxies = {"http": self.proxy, "https": self.proxy}
                self.logger.info(f"Using proxy: {self.proxy}")
    
    def _setup_playwright(self) -> Page:
        """Setup Playwright browser for stealth scraping."""
        if not self.page:
            try:
                # Get a working proxy for the browser
                proxy = proxy_rotator.get_working_proxy()
                user_agent = ua_rotator.get_user_agent()
                # Start Playwright
                self.playwright = sync_playwright().start()
                # Configure browser options
                browser_args = [
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-images",
                    # JavaScript must be enabled for Google Maps
                    # "--disable-javascript",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--allow-running-insecure-content",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-ipc-flooding-protection",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-field-trial-config",
                    "--disable-back-forward-cache",
                    "--disable-ipc-flooding-protection",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-default-apps",
                    "--disable-sync",
                    "--disable-translate",
                    "--hide-scrollbars",
                    "--mute-audio",
                    "--no-zygote",
                    "--disable-logging",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-background-networking",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-features=TranslateUI",
                    "--disable-ipc-flooding-protection",
                    "--disable-client-side-phishing-detection",
                    "--disable-component-extensions-with-background-pages",
                    "--disable-default-apps",
                    "--disable-extensions",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-ipc-flooding-protection",
                    "--disable-sync",
                    "--force-color-profile=srgb",
                    "--metrics-recording-only",
                    "--no-first-run",
                    "--password-store=basic",
                    "--use-mock-keychain",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-features=TranslateUI",
                    "--disable-ipc-flooding-protection",
                    "--disable-client-side-phishing-detection",
                    "--disable-component-extensions-with-background-pages",
                    "--disable-default-apps",
                    "--disable-extensions",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-ipc-flooding-protection",
                    "--disable-sync",
                    "--force-color-profile=srgb",
                    "--metrics-recording-only",
                    "--no-first-run",
                    "--password-store=basic",
                    "--use-mock-keychain"
                ]
                # Launch browser in non-headless mode for better stealth
                self.browser = self.playwright.chromium.launch(
                    headless=False,  # Use visible browser
                    args=browser_args
                )
                # Create context with stealth settings
                context_options = {
                    "user_agent": user_agent,
                    "viewport": {"width": 1920, "height": 1080},
                    "ignore_https_errors": True,
                    "java_script_enabled": True,
                    "locale": "en-US",
                    "timezone_id": "America/New_York",
                    "permissions": ["geolocation"],
                    "geolocation": {"latitude": 40.7128, "longitude": -74.0060},  # NYC coordinates
                    "color_scheme": "light"
                }
                # Try with proxy first, then without if it fails
                proxy_tried = False
                if proxy:
                    try:
                        context_options["proxy"] = {"server": proxy}
                        self.context = self.browser.new_context(**context_options)
                        self.logger.info(f"Setup Playwright browser with proxy: {proxy}")
                        proxy_tried = True
                    except Exception as proxy_error:
                        self.logger.warning(f"Proxy failed, trying without proxy: {proxy_error}")
                        # Remove proxy and try again
                        context_options.pop("proxy", None)
                        self.context = self.browser.new_context(**context_options)
                        self.logger.info("Setup Playwright browser without proxy")
                else:
                    self.context = self.browser.new_context(**context_options)
                    self.logger.info("Setup Playwright browser without proxy")
                # Create page
                self.page = self.context.new_page()
                # Execute stealth scripts
                self.page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                self.page.add_init_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
                self.page.add_init_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
                self.page.add_init_script("Object.defineProperty(navigator, 'platform', {get: () => 'Win32'})")
                self.page.add_init_script("window.chrome = {runtime: {}}")
                self.page.add_init_script("Object.defineProperty(navigator, 'permissions', {get: () => ({query: () => Promise.resolve({state: 'granted'})})})")
                # --- DEBUG: Take screenshot after loading Google Maps search page ---
                try:
                    if hasattr(self, 'source_name') and self.source_name in ['google', 'gmaps']:
                        self.page.goto("https://www.google.com/maps/search/restaurants", wait_until="networkidle", timeout=15000)
                        self.page.screenshot(path="debug_gmaps_search.png")
                        self.logger.info("Saved debug screenshot as debug_gmaps_search.png")
                except Exception as debug_e:
                    self.logger.warning(f"Could not take debug screenshot: {debug_e}")
                # --- END DEBUG ---
            except Exception as e:
                self.logger.error(f"Failed to setup Playwright browser: {e}")
                raise ScrapingError(f"Playwright browser setup failed: {e}")
        return self.page
    
    def _handle_rate_limiting(self):
        """Handle rate limiting with human-like delays."""
        human_delay()
    
    def _extract_business_info(self, element) -> Dict[str, Any]:
        """Extract business information from element (to be implemented by subclasses)."""
        pass
    
    def _clean_extracted_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Clean and validate extracted data."""
        if not data or not data.get('name'):
            return None
        
        # Clean the data
        clean_data = {}
        for key, value in data.items():
            if isinstance(value, str):
                clean_data[key] = value.strip()
            else:
                clean_data[key] = value
        
        # Add metadata
        clean_data['source'] = self.source_name
        clean_data['scraped_at'] = datetime.now().isoformat()
        return clean_data
    
    def _save_lead_to_database(self, lead_data: Dict[str, Any]) -> Optional[int]:
        """Save lead to database."""
        try:
            lead_id = LeadOperations.create_lead(lead_data)
            self.logger.debug(f"Saved lead {lead_id}: {lead_data.get('name', 'Unknown')}")
            return lead_id
        except Exception as e:
            self.logger.error(f"Failed to save lead to database: {e}")
            return None
    
    def _handle_request_error(self, error: Exception, url: str):
        """Handle request errors."""
        self.consecutive_failures += 1
        self.logger.warning(f"Request failed for {url}: {error}")
        
        if self.consecutive_failures >= self.max_failures:
            raise ScrapingError(f"Too many consecutive failures: {error}")
    
    def _handle_request_success(self, url: str):
        """Handle successful request."""
        self.consecutive_failures = 0
        self.logger.debug(f"Successfully fetched: {url}")
    
    @abstractmethod
    def search_businesses(self, search_term: str, max_results: int = 50) -> Iterator[Dict[str, Any]]:
        """Search for businesses (to be implemented by subclasses)."""
        pass
    
    @abstractmethod
    def get_search_url(self, search_term: str, page: int = 1) -> str:
        """Get search URL (to be implemented by subclasses)."""
        pass
    
    def scrape_leads(self, search_term: str, max_results: int = 50, save_to_db: bool = True) -> List[Dict[str, Any]]:
        """Main scraping method.
        
        Args:
            search_term: Search query
            max_results: Maximum results to scrape
            save_to_db: Whether to save results to database
            
        Returns:
            List of scraped business data
        """
        self.logger.info(f"Starting {self.source_name} scraping for: '{search_term}'")
        start_time = time.time()
        
        leads = []
        self.scraped_count = 0
        
        try:
            for business_data in self.search_businesses(search_term, max_results):
                # Clean and validate data
                clean_data = self._clean_extracted_data(business_data)
                
                if clean_data:
                    # Save to database if requested
                    if save_to_db:
                        lead_id = self._save_lead_to_database(clean_data)
                        if lead_id:
                            clean_data['id'] = lead_id
                    
                    leads.append(clean_data)
                    self.scraped_count += 1
                    
                    # Log progress
                    if self.scraped_count % 10 == 0:
                        self.logger.info(f"Scraped {self.scraped_count} leads so far...")
                
                # Check if we've reached the limit
                if self.scraped_count >= max_results:
                    break
                
                # Rate limiting
                self._handle_rate_limiting()
            
            duration = time.time() - start_time
            self.logger.info(f"Scraping completed: {len(leads)} leads in {duration:.1f}s")
            
            return leads
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Scraping failed after {duration:.1f}s: {e}")
            raise ScrapingError(f"Scraping failed: {e}")
        
        finally:
            self.cleanup()
    
    def export_to_csv(self, leads: List[Dict[str, Any]], filename: str):
        """Export leads to CSV file.
        
        Args:
            leads: List of lead data
            filename: Output filename
        """
        if not leads:
            self.logger.warning("No leads to export")
            return
        
        # Ensure output directory exists
        output_path = Path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get all possible fieldnames
        fieldnames = set()
        for lead in leads:
            fieldnames.update(lead.keys())
        
        fieldnames = sorted(list(fieldnames))
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(leads)
            
            self.logger.info(f"Exported {len(leads)} leads to {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to export CSV: {e}")
            raise ScrapingError(f"CSV export failed: {e}")
    
    def test_connection(self) -> bool:
        """Test if the scraper can connect to the target site.
        
        Returns:
            True if connection successful
        """
        try:
            test_url = self.get_search_url("test", 1)
            response = self.session.get(test_url, timeout=10)
            
            if response.status_code == 200:
                self.logger.info(f"Connection test successful for {self.source_name}")
                return True
            else:
                self.logger.warning(f"Connection test failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scraper statistics.
        
        Returns:
            Dictionary with scraper stats
        """
        return {
            'source': self.source_name,
            'scraped_count': self.scraped_count,
            'consecutive_failures': self.consecutive_failures,
            'session_active': self.session is not None,
            'playwright_active': self.page is not None
        }
    
    def cleanup(self):
        """Clean up resources."""
        # Clean up Playwright resources
        if self.page:
            try:
                self.page.close()
                self.page = None
                self.logger.debug("Playwright page cleaned up")
            except Exception as e:
                self.logger.warning(f"Error cleaning up Playwright page: {e}")
        
        if self.context:
            try:
                self.context.close()
                self.context = None
                self.logger.debug("Playwright context cleaned up")
            except Exception as e:
                self.logger.warning(f"Error cleaning up Playwright context: {e}")
        
        if self.browser:
            try:
                self.browser.close()
                self.browser = None
                self.logger.debug("Playwright browser cleaned up")
            except Exception as e:
                self.logger.warning(f"Error cleaning up Playwright browser: {e}")
        
        if self.playwright:
            try:
                self.playwright.stop()
                self.playwright = None
                self.logger.debug("Playwright stopped")
            except Exception as e:
                self.logger.warning(f"Error stopping Playwright: {e}")
        
        # Clean up session
        if self.session:
            try:
                self.session.close()
                self.session = None
                self.logger.debug("Session cleaned up")
            except Exception as e:
                self.logger.warning(f"Error cleaning up session: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()


class ScrapingResult:
    """Container for scraping results."""
    
    def __init__(self, source: str):
        """Initialize scraping result.
        
        Args:
            source: Source name (yelp, google, etc.)
        """
        self.source = source
        self.leads: List[Dict[str, Any]] = []
        self.errors: List[str] = []
        self.start_time = time.time()
        self.end_time = None
        self.success = False
    
    def add_lead(self, lead_data: Dict[str, Any]):
        """Add a lead to results."""
        self.leads.append(lead_data)
    
    def add_error(self, error: str):
        """Add an error to results."""
        self.errors.append(error)
    
    def finish(self, success: bool = True):
        """Mark scraping as finished."""
        self.end_time = time.time()
        self.success = success
    
    @property
    def duration(self) -> float:
        """Get scraping duration."""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    @property
    def leads_count(self) -> int:
        """Get number of leads found."""
        return len(self.leads)
    
    @property
    def errors_count(self) -> int:
        """Get number of errors."""
        return len(self.errors)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'source': self.source,
            'leads_count': self.leads_count,
            'errors_count': self.errors_count,
            'duration': self.duration,
            'success': self.success,
            'leads': self.leads,
            'errors': self.errors
        } 