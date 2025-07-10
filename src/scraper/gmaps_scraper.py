#!/usr/bin/env python3
"""
Google Maps Scraper for PitchPerfect AI
"""

import time
import re
import asyncio
from typing import List, Dict, Any, Optional, Callable
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from ..utils.logger import get_logger

logger = get_logger(__name__)

class GoogleMapsScraper:
    """Google Maps scraper using Playwright."""
    
    def __init__(self):
        self.logger = logger
    
    async def scrape_with_progress(
        self, 
        search_term: str, 
        progress_callback: Optional[Callable[[int, int, int, str, dict], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape Google Maps with progress updates.
        
        Args:
            search_term: Search term for Google Maps
            progress_callback: Callback function for progress updates (progress, total, successful, message)
            
        Returns:
            List of scraped business data
        """
        results = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, slow_mo=100)
            page = await browser.new_page()
            
            # Set user agent to avoid detection
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            try:
                # Navigate to Google Maps
                search_url = f"https://www.google.com/maps/search/{search_term.replace(' ', '+')}"
                self.logger.info(f"Navigating to: {search_url}")
                
                if progress_callback:
                    progress_callback(0, 0, 0, "Navigating to Google Maps...")
                
                await page.goto(search_url, wait_until="networkidle", timeout=120000)
                await page.wait_for_timeout(8000)
                
                # Handle cookie consent
                if progress_callback:
                    progress_callback(0, 0, 0, "Handling cookie consent...")
                await self._handle_cookie_consent(page)
                
                # Wait for business listings
                if progress_callback:
                    progress_callback(0, 0, 0, "Waiting for business listings to load...")
                await self._wait_for_listings(page)
                
                # Scroll to load all results
                if progress_callback:
                    progress_callback(0, 0, 0, "Scrolling to load all results...")
                total_listings = await self._scroll_and_load(page, progress_callback)
                
                # Extract data from all listings
                if progress_callback:
                    progress_callback(0, total_listings, 0, f"Starting to extract data from {total_listings} listings...")
                results = await self._extract_all_listings(page, total_listings, progress_callback)
                
                self.logger.info(f"Scraping completed. Found {len(results)} leads")
                
            except Exception as e:
                self.logger.error(f"Error during scraping: {e}")
                raise
            finally:
                await browser.close()
        
        return results
    
    async def _handle_cookie_consent(self, page):
        """Handle cookie consent popup."""
        consent_buttons = [
            "button:has-text('Accept all')",
            "button:has-text('Accept')",
            "button:has-text('I agree')",
            "button:has-text('OK')"
        ]
        
        for button_selector in consent_buttons:
            try:
                if await page.locator(button_selector).count() > 0:
                    await page.locator(button_selector).click(timeout=3000)
                    self.logger.info(f"Clicked consent button: {button_selector}")
                    break
            except PlaywrightTimeoutError:
                continue
    
    async def _wait_for_listings(self, page):
        """Wait for business listings to appear."""
        listing_selectors = [
            "div[class*='Nv2PK']",
            "div[role='article']",
            "div[data-test-id*='place']"
        ]
        
        listings_found = False
        for selector in listing_selectors:
            try:
                if await page.locator(selector).count() > 0:
                    self.logger.info(f"Found listings with selector: {selector}")
                    listings_found = True
                    break
            except:
                continue
        
        if not listings_found:
            raise Exception("No business listings found")
    
    async def _scroll_and_load(self, page, progress_callback) -> int:
        """Scroll to load all results and return total count."""
        self.logger.info("Scrolling to load results...")
        
        previous_count = -1
        same_count_repeats = 0
        scrolls = 0
        max_same_count = 8  # Increased to be more thorough
        consecutive_no_new_results = 0
        max_consecutive_no_new = 10  # Stop after 10 consecutive scrolls with no new results
        
        while True:  # Continue until we reach the bottom
            business_cards = page.locator("div[class*='Nv2PK']")
            current_count = await business_cards.count()
            
            self.logger.info(f"Scroll {scrolls + 1}: Found {current_count} listings")
            
            if progress_callback:
                progress_callback(0, current_count, 0, f"Scroll {scrolls + 1}: Found {current_count} listings (continuing until bottom)")
            
            # Check for loading spinner
            spinner = page.locator("div.lXJj5c.Hk4XGb")
            is_loading = await spinner.count() > 0
            
            if is_loading:
                self.logger.info("Loading spinner detected, waiting for content to load...")
                if progress_callback:
                    progress_callback(0, current_count, 0, "Loading spinner detected, waiting for content to load...")
                try:
                    await spinner.wait_for(state="hidden", timeout=10000)
                    self.logger.info("Loading completed")
                    if progress_callback:
                        progress_callback(0, current_count, 0, "Loading completed")
                    await page.wait_for_timeout(2000)
                except PlaywrightTimeoutError:
                    self.logger.warning("Spinner timeout, continuing anyway")
                    if progress_callback:
                        progress_callback(0, current_count, 0, "Loading timeout, continuing...")
            
            if current_count == previous_count:
                consecutive_no_new_results += 1
                same_count_repeats += 1
                self.logger.info(f"Same count for {same_count_repeats}/{max_same_count} iterations (consecutive no new: {consecutive_no_new_results})")
            else:
                consecutive_no_new_results = 0
                same_count_repeats = 0
                self.logger.info(f"Count increased from {previous_count} to {current_count}")
            
            # Stop if we've had no new results for too many consecutive scrolls
            if consecutive_no_new_results >= max_consecutive_no_new:
                self.logger.info(f"Stopping: No new listings found for {max_consecutive_no_new} consecutive scrolls - likely reached the bottom")
                break
            
            # Also stop if we've had the same count for multiple iterations AND no spinner (backup condition)
            if same_count_repeats >= max_same_count and not is_loading:
                self.logger.info(f"Stopping: No new listings found for {max_same_count} iterations")
                break
            
            previous_count = current_count
            
            try:
                scrollable_div = page.locator("div[role='feed']")
                if await scrollable_div.count() > 0:
                    await scrollable_div.evaluate("el => el.scrollBy(0, el.scrollHeight)")
                else:
                    await page.mouse.wheel(0, 3000)
            except Exception as e:
                self.logger.warning(f"Scroll error: {e}")
            
            await page.wait_for_timeout(2500)
            scrolls += 1
            
            # Safety check: if we've scrolled too many times, stop to prevent infinite loops
            if scrolls > 100:
                self.logger.warning(f"Reached maximum scroll limit of 100 for safety. Found {current_count} listings.")
                break
        
        # Final check for any remaining loading
        final_spinner = page.locator("div.lXJj5c.Hk4XGb")
        if await final_spinner.count() > 0:
            self.logger.info("Waiting for final loading to complete...")
            try:
                await final_spinner.wait_for(state="hidden", timeout=10000)
                await page.wait_for_timeout(2000)
            except PlaywrightTimeoutError:
                self.logger.warning("Final loading timeout, proceeding anyway")
        
        # Get final count
        final_business_cards = page.locator("div[class*='Nv2PK']")
        final_count = await final_business_cards.count()
        self.logger.info(f"Final count after all loading: {final_count} listings")
        
        return final_count
    
    async def _extract_all_listings(self, page, total_listings: int, progress_callback) -> List[Dict[str, Any]]:
        """Extract data from all listings."""
        results = []
        successful_extractions = 0
        
        business_cards = page.locator("div[class*='Nv2PK']")
        
        for index in range(total_listings):
            try:
                self.logger.info(f"Processing listing {index+1}/{total_listings}")
                
                if progress_callback:
                    progress_callback(index + 1, total_listings, successful_extractions, f"Processing listing {index+1}/{total_listings}")
                
                # Click on the listing
                await business_cards.nth(index).click()
                await page.wait_for_timeout(2500)
                
                # Extract business info
                business_details = await self._extract_listing_info(page)
                
                if business_details and business_details.get("name"):
                    # Check if we got any target data
                    has_phone = bool(business_details.get('phone'))
                    has_website = bool(business_details.get('website'))
                    has_email = bool(business_details.get('email'))
                    
                    if has_phone or has_website or has_email:
                        successful_extractions += 1
                        results.append(business_details)
                        self.logger.info(f"✅ SUCCESS: {business_details['name']}")
                        
                        # Pass the new lead to the callback for real-time saving
                        if progress_callback:
                            progress_callback(index + 1, total_listings, successful_extractions, f"Found lead: {business_details['name']}", business_details)
                    else:
                        self.logger.info(f"❌ NO TARGET DATA: {business_details.get('name', 'Unknown')}")
                        if progress_callback:
                            progress_callback(index + 1, total_listings, successful_extractions, f"No target data for: {business_details.get('name', 'Unknown')}")
                else:
                    self.logger.info("❌ FAILED: No details extracted")
                    if progress_callback:
                        progress_callback(index + 1, total_listings, successful_extractions, f"Failed to extract details for listing {index+1}")
                
                # Update progress without new lead
                if progress_callback:
                    progress_callback(index + 1, total_listings, successful_extractions, f"Processed {index + 1}/{total_listings} listings")
                
            except Exception as e:
                self.logger.error(f"❌ ERROR processing listing {index+1}: {e}")
        
        return results
    
    async def _extract_listing_info(self, page) -> Optional[Dict[str, Any]]:
        """Extract business information from the detail panel."""
        try:
            await page.wait_for_timeout(2000)
            
            # === NAME ===
            name = ""
            name_selectors = [
                "h1.DUwDvf.lfPIob",
                "h1[class*='DUwDvf']",
                "h1",
                "div[class*='fontHeadline']"
            ]
            
            for selector in name_selectors:
                name_el = page.locator(selector)
                if await name_el.count() > 0:
                    name = await name_el.first.text_content()
                    if name:
                        name = name.strip()
                        break
            
            # === WEBSITE ===
            website = ""
            website_selectors = [
                "a[href*='http']:not([href*='google.com/maps'])",
                "a[data-item-id*='website']",
                "a[aria-label*='website']",
                "a[aria-label*='Website']",
                "a[href*='.com']",
                "a[href*='.org']",
                "a[href*='.net']"
            ]
            
            for selector in website_selectors:
                website_links = page.locator(selector)
                for i in range(await website_links.count()):
                    href = await website_links.nth(i).get_attribute("href")
                    if href and not href.startswith("https://www.google.com/maps"):
                        website = href
                        break
                if website:
                    break
            
            # === PHONE ===
            phone = ""
            phone_selectors = [
                "button[aria-label*='Call']",
                "a[aria-label*='Call']",
                "a[href*='tel:']",
                "div[class*='Io6YTe']",
                "span[class*='Io6YTe']",
                "div[class*='phone']",
                "span[class*='phone']",
                "div[class*='contact']",
                "span[class*='contact']"
            ]
            
            for selector in phone_selectors:
                phone_elements = page.locator(selector)
                for i in range(await phone_elements.count()):
                    element = phone_elements.nth(i)
                    text = await element.text_content()
                    aria_label = await element.get_attribute("aria-label") or ""
                    
                    # Extract phone from aria-label
                    if "Call" in aria_label:
                        phone_match = re.search(r'Call\s+(.+)', aria_label)
                        if phone_match:
                            phone = phone_match.group(1).strip()
                            if phone and phone != "phone number":
                                break
                    
                    # Extract phone from href
                    href = await element.get_attribute("href")
                    if href and href.startswith("tel:"):
                        phone = href.replace("tel:", "").strip()
                        if phone and phone != "phone number":
                            break
                    
                    # Extract phone from text content
                    if text and self._is_valid_phone(text.strip()) and text.strip() != "phone number":
                        phone = text.strip()
                        break
                
                if phone and phone != "phone number":
                    break
            
            # If no phone found, try to find any text that looks like a phone number
            if not phone or phone == "phone number":
                all_text_elements = page.locator("div, span, button, a")
                for i in range(await all_text_elements.count()):
                    element = all_text_elements.nth(i)
                    text = await element.text_content()
                    if text and self._is_valid_phone(text.strip()) and text.strip() != "phone number":
                        phone = text.strip()
                        break
            
            # === EMAIL ===
            email = ""
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            
            # Check all text content on the page for emails
            page_text = await page.text_content("body")
            email_matches = re.findall(email_pattern, page_text)
            if email_matches:
                email = email_matches[0]
            
            # Also check specific elements that might contain emails
            if not email:
                email_elements = page.locator("div[class*='Io6YTe']")
                for i in range(await email_elements.count()):
                    text = await email_elements.nth(i).text_content()
                    email_match = re.search(email_pattern, text)
                    if email_match:
                        email = email_match.group(0)
                        break
            
            self.logger.info(f"Raw extracted - Name: '{name}', Phone: '{phone}', Website: '{website}', Email: '{email}'")
            
            return {
                "name": name,
                "phone": phone,
                "website": website,
                "email": email
            }
        
        except Exception as e:
            self.logger.error(f"Failed to extract listing info: {e}")
            return None
    
    def _is_valid_phone(self, text: str) -> bool:
        """Check if text looks like a valid phone number."""
        if not text:
            return False
        
        # Remove common separators
        cleaned = re.sub(r'[\s\-\(\)\.]', '', text)
        
        # Check if it contains enough digits
        digits = re.findall(r'\d', cleaned)
        if len(digits) < 7:  # Minimum 7 digits for a phone number
            return False
        
        # Check for common phone patterns
        phone_patterns = [
            r'^\+?[\d\s\-\(\)\.]+$',  # International format
            r'^\(\d{3}\)\s*\d{3}-\d{4}$',  # US format (555) 123-4567
            r'^\d{3}-\d{3}-\d{4}$',  # US format 555-123-4567
            r'^\d{10}$',  # 10 digits
            r'^\d{11}$',  # 11 digits (with country code)
        ]
        
        for pattern in phone_patterns:
            if re.match(pattern, text.strip()):
                return True
        
        return False 