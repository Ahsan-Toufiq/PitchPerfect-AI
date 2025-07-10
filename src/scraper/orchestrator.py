"""Scraper orchestrator for PitchPerfect AI."""

import time
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from .gmaps_scraper import GoogleMapsScraper
from .base_scraper import ScrapingError, ScrapingResult
from ..utils.logger import get_logger


class ScraperOrchestrator:
    """Orchestrates multiple scrapers for lead generation."""
    
    def __init__(self):
        """Initialize scraper orchestrator."""
        self.logger = get_logger(__name__)
        self.scrapers = {
            'google_maps': GoogleMapsScraper,
        }
        self.logger.info("Initialized scraper orchestrator")
    
    def scrape_leads(self, search_term: str, max_results: int = 50, 
                     sources: Optional[List[str]] = None, 
                     save_to_db: bool = True) -> Dict[str, ScrapingResult]:
        """Scrape leads from multiple sources.
        
        Args:
            search_term: Search query
            max_results: Maximum results per source
            sources: List of sources to use (default: all)
            save_to_db: Whether to save results to database
            
        Returns:
            Dictionary of scraping results by source
        """
        if sources is None:
            sources = list(self.scrapers.keys())
        
        self.logger.info(f"Starting lead scraping for: '{search_term}' from sources: {sources}")
        
        results = {}
        
        # Try sources sequentially until one works
        for source_name in sources:
            if source_name not in self.scrapers:
                self.logger.warning(f"Unknown source: {source_name}")
                continue
            
            try:
                self.logger.info(f"Trying source: {source_name}")
                scraper_class = self.scrapers[source_name]
                scraper = scraper_class()
                
                # Run scraping
                leads = list(scraper.scrape_leads(search_term, max_results, save_to_db))
                
                # Create result
                result = ScrapingResult(source_name)
                for lead in leads:
                    result.add_lead(lead)
                result.finish(success=True)
                
                results[source_name] = result
                
                self.logger.info(f"✅ {source_name} successful: {len(leads)} leads")
                
                # If we got some leads, we can stop here
                if len(leads) > 0:
                    self.logger.info(f"Found working source: {source_name}")
                    break
                
            except Exception as e:
                self.logger.error(f"❌ {source_name} failed: {e}")
                result = ScrapingResult(source_name)
                result.add_error(str(e))
                result.finish(success=False)
                results[source_name] = result
                continue
        
        # Log summary
        total_leads = sum(len(result.leads) for result in results.values())
        self.logger.info(f"Scraping completed. Total leads: {total_leads}")
        
        return results
    
    def scrape_leads_parallel(self, search_term: str, max_results: int = 50,
                             sources: Optional[List[str]] = None,
                             save_to_db: bool = True) -> Dict[str, ScrapingResult]:
        """Scrape leads from multiple sources in parallel.
        
        Args:
            search_term: Search query
            max_results: Maximum results per source
            sources: List of sources to use (default: all)
            save_to_db: Whether to save results to database
            
        Returns:
            Dictionary of scraping results by source
        """
        if sources is None:
            sources = list(self.scrapers.keys())
        
        self.logger.info(f"Starting parallel lead scraping for: '{search_term}' from sources: {sources}")
        
        results = {}
        
        def scrape_source(source_name: str) -> tuple[str, ScrapingResult]:
            """Scrape from a single source."""
            try:
                self.logger.info(f"Starting {source_name} scraper")
                scraper_class = self.scrapers[source_name]
                scraper = scraper_class()
                
                # Run scraping
                leads = list(scraper.scrape_leads(search_term, max_results, save_to_db))
                
                # Create result
                result = ScrapingResult(source_name)
                for lead in leads:
                    result.add_lead(lead)
                result.finish(success=True)
            
                self.logger.info(f"✅ {source_name} completed: {len(leads)} leads")
                return source_name, result
            
            except Exception as e:
                self.logger.error(f"❌ {source_name} failed: {e}")
                result = ScrapingResult(source_name)
                result.add_error(str(e))
                result.finish(success=False)
                return source_name, result
        
        # Run scrapers in parallel
        with ThreadPoolExecutor(max_workers=len(sources)) as executor:
            future_to_source = {
                executor.submit(scrape_source, source_name): source_name 
                for source_name in sources
            }
            
            for future in as_completed(future_to_source):
                source_name, result = future.result()
                results[source_name] = result
        
        # Log summary
        total_leads = sum(len(result.leads) for result in results.values())
        self.logger.info(f"Parallel scraping completed. Total leads: {total_leads}")
        
        return results
    
    def get_available_sources(self) -> List[str]:
        """Get list of available scraping sources."""
        return list(self.scrapers.keys())
    
    def test_source(self, source_name: str) -> bool:
        """Test if a source is working.
        
        Args:
            source_name: Name of the source to test
            
        Returns:
            True if source is working
        """
        if source_name not in self.scrapers:
            self.logger.warning(f"Unknown source: {source_name}")
            return False
        
        try:
            scraper_class = self.scrapers[source_name]
            scraper = scraper_class()
            
            # Test with a simple search
            test_results = list(scraper.scrape_leads("test", 1, save_to_db=False))
            
            is_working = len(test_results) > 0
            self.logger.info(f"Source {source_name} test: {'✅ Working' if is_working else '❌ Failed'}")
            
            return is_working
            
        except Exception as e:
            self.logger.error(f"Source {source_name} test failed: {e}")
            return False
    
    def test_all_sources(self) -> Dict[str, bool]:
        """Test all available sources.
            
        Returns:
            Dictionary mapping source names to working status
        """
        results = {}
        for source_name in self.get_available_sources():
            results[source_name] = self.test_source(source_name)
        return results 