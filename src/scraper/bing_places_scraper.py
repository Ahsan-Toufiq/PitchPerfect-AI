"""Bing Places scraper for PitchPerfect AI."""

import time
import re
from typing import Dict, Any, Iterator, Optional
from urllib.parse import quote_plus

from .base_scraper import BaseScraper, ScrapingError
from ..utils.proxy_rotation import human_delay


class BingPlacesScraper(BaseScraper):
    """Bing Places scraper using Playwright for stealth scraping."""
    
    def __init__(self):
        """Initialize Bing Places scraper."""
        super().__init__()
        self.base_url = "https://www.bing.com/maps"
        self.search_url_template = "https://www.bing.com/maps?q={}"
        self.max_pages = 3
        self.results_per_page = 20
    
    def get_search_url(self, search_term: str, page: int = 1) -> str:
        """Get Bing Places search URL."""
        return self.search_url_template.format(quote_plus(search_term))
    
    def search_businesses(self, search_term: str, max_results: int = 50) -> Iterator[Dict[str, Any]]:
        """Search for businesses on Bing Places."""
        self.logger.info(f"Starting Bing Places search for: {search_term}")
        page = None
        screenshot_taken = False
        try:
            page = self._setup_playwright()
            scraped_count = 0
            search_url = self.get_search_url(search_term)
            self.logger.info(f"Navigating to: {search_url}")
            try:
                # Navigate to search page
                page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                human_delay()
                
                # Always take a screenshot after navigation
                try:
                    page.screenshot(path="debug_bing_search.png")
                    self.logger.info("Saved debug screenshot as debug_bing_search.png")
                    screenshot_taken = True
                except Exception as ss_e:
                    self.logger.warning(f"Could not take debug screenshot: {ss_e}")
                
                # Wait for page to load and try multiple selectors
                business_elements = self._wait_for_business_elements(page)
                
                if not business_elements:
                    self.logger.warning("No business elements found with any selector")
                    return
                
                self.logger.info(f"Found {len(business_elements)} business elements")
                
                # Scroll to load more results
                self._scroll_to_load_results(page, max_results)
                
                # Re-extract elements after scrolling
                business_elements = self._get_business_elements(page)
                self.logger.info(f"After scrolling: {len(business_elements)} business elements")
                
                for element in business_elements:
                    if scraped_count >= max_results:
                        break
                    try:
                        business_data = self._extract_business_info(element)
                        if business_data:
                            clean_data = self._clean_extracted_data(business_data)
                            if clean_data:
                                lead_id = self._save_lead_to_database(clean_data)
                                if lead_id:
                                    scraped_count += 1
                                    self.scraped_count += 1
                                    yield clean_data
                                    self.logger.debug(f"Scraped business: {clean_data.get('name', 'Unknown')}")
                    except Exception as e:
                        self.logger.warning(f"Error extracting business from element: {e}")
                        continue
                
                self.logger.info(f"Bing Places scraping completed. Total scraped: {scraped_count}")
                
            except Exception as e:
                self.logger.error(f"Error during Bing Places scraping: {e}")
                if page and not screenshot_taken:
                    try:
                        page.screenshot(path="debug_bing_search.png")
                        self.logger.info("Saved debug screenshot as debug_bing_search.png (on error)")
                    except Exception as ss_e:
                        self.logger.warning(f"Could not take debug screenshot (on error): {ss_e}")
                self._handle_request_error(e, search_url)
        except Exception as e:
            self.logger.error(f"Bing Places scraping failed: {e}")
            raise ScrapingError(f"Bing Places scraping failed: {e}")
        finally:
            self.cleanup()
    
    def _wait_for_business_elements(self, page) -> list:
        """Wait for business elements using multiple selectors."""
        selectors = [
            "div[class*='result']",
            "div[class*='listing']",
            "div[class*='business']",
            "div[class*='place']",
            "div[class*='item']",
            "div[role='listitem']",
            "div[class*='card']",
            "div[class*='entity']"
        ]
        
        for selector in selectors:
            try:
                self.logger.info(f"Trying selector: {selector}")
                page.wait_for_selector(selector, timeout=10000)
                elements = page.query_selector_all(selector)
                if elements:
                    self.logger.info(f"Found {len(elements)} elements with selector: {selector}")
                    return elements
            except Exception as e:
                self.logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        # If no specific selector works, try to get any div elements
        try:
            self.logger.info("Trying fallback: all div elements")
            elements = page.query_selector_all("div")
            # Filter for likely business elements (those with text content)
            business_elements = []
            for element in elements:
                try:
                    text = element.text_content().strip()
                    if text and len(text) > 10 and len(text) < 500:  # Reasonable text length
                        business_elements.append(element)
                except:
                    continue
            if business_elements:
                self.logger.info(f"Found {len(business_elements)} potential business elements with fallback")
                return business_elements
        except Exception as e:
            self.logger.warning(f"Fallback selector failed: {e}")
        
        return []
    
    def _get_business_elements(self, page) -> list:
        """Get business elements using multiple selectors."""
        selectors = [
            "div[class*='result']",
            "div[class*='listing']",
            "div[class*='business']",
            "div[class*='place']",
            "div[class*='item']",
            "div[role='listitem']",
            "div[class*='card']",
            "div[class*='entity']"
        ]
        
        for selector in selectors:
            try:
                elements = page.query_selector_all(selector)
                if elements:
                    return elements
            except Exception:
                continue
        
        # Fallback
        try:
            elements = page.query_selector_all("div")
            business_elements = []
            for element in elements:
                try:
                    text = element.text_content().strip()
                    if text and len(text) > 10 and len(text) < 500:
                        business_elements.append(element)
                except:
                    continue
            return business_elements
        except Exception:
            return []
    
    def _scroll_to_load_results(self, page, max_results: int):
        """Scroll to load more results."""
        last_height = page.evaluate("document.body.scrollHeight")
        loaded_count = 0
        scroll_attempts = 0
        max_scroll_attempts = 5
        
        while loaded_count < max_results and scroll_attempts < max_scroll_attempts:
            # Scroll down
            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            human_delay()
            
            # Wait for new content to load
            time.sleep(2)
            
            # Check if new content loaded
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                scroll_attempts += 1
            
            # Count current results
            current_elements = self._get_business_elements(page)
            loaded_count = len(current_elements)
            
            if loaded_count >= max_results:
                break
            
            last_height = new_height
            scroll_attempts += 1
    
    def _extract_business_info(self, element) -> Optional[Dict[str, Any]]:
        """Extract business information from Bing Places listing element."""
        try:
            business_data = {}
            
            # Get all text content for debugging
            all_text = element.text_content().strip()
            if not all_text or len(all_text) < 5:
                return None
            
            # Extract business name - try multiple selectors
            name_selectors = [
                "h3", "h4", "[role='heading']", 
                "div[class*='title']", "div[class*='name']",
                "span[class*='title']", "span[class*='name']"
            ]
            
            name_found = False
            for selector in name_selectors:
                try:
                    name_element = element.query_selector(selector)
                    if name_element:
                        name_text = name_element.text_content().strip()
                        if name_text and len(name_text) > 2:
                            business_data['name'] = name_text
                            name_found = True
                            break
                except Exception:
                    continue
            
            # If no name found with selectors, try to extract from all text
            if not name_found:
                lines = all_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and len(line) > 2 and len(line) < 100:
                        # Skip common non-name patterns
                        if not any(skip in line.lower() for skip in ['rating', 'review', 'phone', 'website', 'address']):
                            business_data['name'] = line
                            break
            
            if not business_data.get('name'):
                return None
            
            # Extract business URL/website
            try:
                website_elements = element.query_selector_all("a[href*='http']")
                for link in website_elements:
                    href = link.get_attribute('href')
                    if href and not any(domain in href for domain in ['bing.com', 'microsoft.com']):
                        business_data['website'] = href
                        break
            except Exception:
                pass
            
            # Extract phone number
            try:
                phone_elements = element.query_selector_all("a[href^='tel:'], span")
                for phone_elem in phone_elements:
                    phone_text = phone_elem.text_content().strip()
                    if phone_text and re.match(r'[\d\-\+\(\)\s]+', phone_text):
                        business_data['phone'] = self._clean_phone(phone_text)
                        break
            except Exception:
                pass
            
            # Extract address
            try:
                address_elements = element.query_selector_all("span, div")
                for addr_elem in address_elements:
                    addr_text = addr_elem.text_content().strip()
                    if addr_text and any(word in addr_text.lower() for word in ['street', 'avenue', 'road', 'drive', 'lane', 'st.', 'ave.', 'rd.']):
                        business_data['address'] = addr_text
                        break
            except Exception:
                pass
            
            # Extract rating
            try:
                rating_elements = element.query_selector_all("span[aria-label*='star'], span")
                for rating_elem in rating_elements:
                    rating_text = rating_elem.text_content().strip()
                    if rating_text and re.match(r'\d+(\.\d+)?', rating_text):
                        business_data['rating'] = float(rating_text)
                        break
            except (ValueError, Exception):
                pass
            
            # Extract review count
            try:
                review_elements = element.query_selector_all("span")
                for review_elem in review_elements:
                    review_text = review_elem.text_content().strip()
                    if review_text and '(' in review_text and ')' in review_text:
                        review_match = re.search(r'\((\d+)\)', review_text)
                        if review_match:
                            business_data['review_count'] = int(review_match.group(1))
                            break
            except Exception:
                pass
            
            # Extract categories/tags
            try:
                category_elements = element.query_selector_all("span, div")
                categories = []
                for cat_elem in category_elements:
                    cat_text = cat_elem.text_content().strip()
                    if cat_text and len(cat_text) < 50:  # Likely category tags are short
                        categories.append(cat_text)
                if categories:
                    business_data['categories'] = categories[:5]  # Limit to 5 categories
            except Exception:
                pass
            
            return business_data if business_data.get('name') else None
            
        except Exception as e:
            self.logger.warning(f"Error extracting business info: {e}")
            return None
    
    def _clean_phone(self, phone_text: str) -> str:
        """Clean phone number text."""
        # Remove non-digit characters except + and -
        cleaned = re.sub(r'[^\d+\-\(\)\s]', '', phone_text)
        return cleaned.strip() 