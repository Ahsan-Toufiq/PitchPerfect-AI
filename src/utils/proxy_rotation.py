"""Proxy and User-Agent rotation utilities for robust scraping."""

import requests
import random
import time
from typing import List, Optional, Dict, Any
from ..utils import get_logger

logger = get_logger(__name__)


class ProxyRotator:
    """Free proxy rotation utility."""
    
    def __init__(self):
        self.proxies = []
        self.last_update = 0
        self.update_interval = 3600  # Update every hour
        self._load_proxies()
    
    def _load_proxies(self):
        """Load free proxies from public lists."""
        try:
            # Free proxy sources
            proxy_sources = [
                "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
                "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
                "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt"
            ]
            
            all_proxies = []
            for source in proxy_sources:
                try:
                    response = requests.get(source, timeout=10)
                    if response.status_code == 200:
                        proxies = response.text.strip().split('\n')
                        all_proxies.extend([p.strip() for p in proxies if p.strip()])
                        logger.info(f"Loaded {len(proxies)} proxies from {source}")
                except Exception as e:
                    logger.warning(f"Failed to load proxies from {source}: {e}")
            
            # Filter and format proxies
            self.proxies = []
            for proxy in all_proxies:
                if ':' in proxy and len(proxy.split(':')) == 2:
                    host, port = proxy.split(':')
                    if port.isdigit():
                        self.proxies.append(f"http://{proxy}")
            
            logger.info(f"Loaded {len(self.proxies)} valid proxies")
            
        except Exception as e:
            logger.error(f"Failed to load proxies: {e}")
            self.proxies = []
    
    def get_proxy(self) -> Optional[str]:
        """Get a random proxy."""
        if not self.proxies:
            self._load_proxies()
        
        if self.proxies:
            return random.choice(self.proxies)
        return None
    
    def test_proxy(self, proxy: str) -> bool:
        """Test if a proxy is working."""
        try:
            response = requests.get(
                "http://httpbin.org/ip",
                proxies={"http": proxy, "https": proxy},
                timeout=10
            )
            return response.status_code == 200
        except:
            return False
    
    def get_working_proxy(self) -> Optional[str]:
        """Get a working proxy."""
        if not self.proxies:
            self._load_proxies()
        
        # Test up to 10 random proxies
        tested_proxies = random.sample(self.proxies, min(10, len(self.proxies)))
        
        for proxy in tested_proxies:
            if self.test_proxy(proxy):
                logger.info(f"Found working proxy: {proxy}")
                return proxy
        
        logger.warning("No working proxies found")
        return None


class UserAgentRotator:
    """User-Agent rotation utility."""
    
    def __init__(self):
        self.user_agents = [
            # Chrome
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # Firefox
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
            # Safari
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            # Edge
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            # Mobile
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 14; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        ]
    
    def get_user_agent(self) -> str:
        """Get a random user agent."""
        return random.choice(self.user_agents)


class StealthHeaders:
    """Stealth headers for avoiding detection."""
    
    def __init__(self):
        self.ua_rotator = UserAgentRotator()
    
    def get_headers(self) -> Dict[str, str]:
        """Get stealth headers."""
        return {
            "User-Agent": self.ua_rotator.get_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0"
        }


# Global instances
proxy_rotator = ProxyRotator()
ua_rotator = UserAgentRotator()
stealth_headers = StealthHeaders()


def get_random_delay(min_delay: float = 1.0, max_delay: float = 3.0) -> float:
    """Get a random delay for human-like behavior."""
    return random.uniform(min_delay, max_delay)


def human_delay():
    """Add a human-like delay."""
    time.sleep(get_random_delay()) 