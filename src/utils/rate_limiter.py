"""Rate limiting utilities for PitchPerfect AI."""

import time
import asyncio
import random
from typing import Optional, Callable, Any, Dict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from functools import wraps
from dataclasses import dataclass

from .logger import get_logger, log_rate_limit


logger = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    requests_per_period: int
    period_seconds: int
    burst_size: Optional[int] = None  # Allow burst above rate limit
    backoff_factor: float = 1.5  # Exponential backoff multiplier
    max_backoff: float = 300.0  # Maximum backoff time in seconds
    jitter: bool = True  # Add random jitter to delays


class RateLimiter:
    """Thread-safe rate limiter with multiple strategies."""
    
    def __init__(self, config: RateLimitConfig):
        """Initialize rate limiter.
        
        Args:
            config: Rate limiting configuration
        """
        self.config = config
        self.request_times: deque = deque()
        self.last_request_time = 0.0
        self.consecutive_failures = 0
        self._lock = asyncio.Lock() if asyncio.iscoroutinefunction else None
    
    def can_make_request(self) -> bool:
        """Check if a request can be made without waiting."""
        now = time.time()
        
        # Remove old requests outside the time window
        cutoff = now - self.config.period_seconds
        while self.request_times and self.request_times[0] < cutoff:
            self.request_times.popleft()
        
        # Check if under rate limit
        return len(self.request_times) < self.config.requests_per_period
    
    def get_delay(self) -> float:
        """Get delay needed before next request."""
        if self.can_make_request():
            return 0.0
        
        # Calculate delay based on oldest request in window
        now = time.time()
        oldest_request = self.request_times[0]
        delay = (oldest_request + self.config.period_seconds) - now
        
        # Add exponential backoff for consecutive failures
        if self.consecutive_failures > 0:
            backoff = min(
                self.config.backoff_factor ** self.consecutive_failures,
                self.config.max_backoff
            )
            delay = max(delay, backoff)
        
        # Add jitter to prevent thundering herd
        if self.config.jitter:
            delay += random.uniform(0, delay * 0.1)
        
        return max(0, delay)
    
    def wait_if_needed(self) -> None:
        """Wait if rate limit requires it."""
        delay = self.get_delay()
        if delay > 0:
            log_rate_limit("request", delay)
            time.sleep(delay)
    
    async def async_wait_if_needed(self) -> None:
        """Async version of wait_if_needed."""
        delay = self.get_delay()
        if delay > 0:
            log_rate_limit("async request", delay)
            await asyncio.sleep(delay)
    
    def record_request(self, success: bool = True) -> None:
        """Record that a request was made.
        
        Args:
            success: Whether the request was successful
        """
        now = time.time()
        self.request_times.append(now)
        self.last_request_time = now
        
        if success:
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
            logger.warning(f"Request failed, consecutive failures: {self.consecutive_failures}")
    
    def reset(self) -> None:
        """Reset rate limiter state."""
        self.request_times.clear()
        self.consecutive_failures = 0
        logger.debug("Rate limiter reset")

    def get_stats(self) -> dict:
        """Return statistics for this rate limiter."""
        now = time.time()
        cutoff = now - self.config.period_seconds
        recent_requests = sum(1 for t in self.request_times if t > cutoff)
        return {
            "requests_in_period": recent_requests,
            "max_requests": self.config.requests_per_period,
            "period_seconds": self.config.period_seconds,
            "can_make_request": self.can_make_request(),
            "delay_needed": self.get_delay(),
            "consecutive_failures": self.consecutive_failures,
            "last_request": self.last_request_time
        }


class GlobalRateLimiter:
    """Global rate limiter managing multiple named rate limiters."""
    
    def __init__(self):
        """Initialize global rate limiter."""
        self.limiters: Dict[str, RateLimiter] = {}
        self.default_configs = {
            "scraping": RateLimitConfig(
                requests_per_period=10,
                period_seconds=60,
                burst_size=3,
                backoff_factor=2.0
            ),
            "email": RateLimitConfig(
                requests_per_period=50,
                period_seconds=86400,  # Daily limit
                backoff_factor=1.5
            ),
            "analysis": RateLimitConfig(
                requests_per_period=20,
                period_seconds=60,
                burst_size=5
            ),
            "llm": RateLimitConfig(
                requests_per_period=30,
                period_seconds=60,
                backoff_factor=1.8
            )
        }
    
    def get_limiter(self, name: str, config: Optional[RateLimitConfig] = None) -> RateLimiter:
        """Get or create a rate limiter.
        
        Args:
            name: Rate limiter name
            config: Optional custom configuration
            
        Returns:
            Rate limiter instance
        """
        if name not in self.limiters:
            if config is None:
                config = self.default_configs.get(name)
                if config is None:
                    raise ValueError(f"No default config for '{name}' and none provided")
            
            self.limiters[name] = RateLimiter(config)
            logger.debug(f"Created rate limiter '{name}': {config.requests_per_period}/{config.period_seconds}s")
        
        return self.limiters[name]
    
    def wait_for(self, limiter_name: str) -> None:
        """Wait for rate limiter if needed."""
        limiter = self.get_limiter(limiter_name)
        limiter.wait_if_needed()
    
    async def async_wait_for(self, limiter_name: str) -> None:
        """Async wait for rate limiter if needed."""
        limiter = self.get_limiter(limiter_name)
        await limiter.async_wait_if_needed()
    
    def record_request(self, limiter_name: str, success: bool = True) -> None:
        """Record request for named limiter."""
        limiter = self.get_limiter(limiter_name)
        limiter.record_request(success)
    
    def get_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all rate limiters."""
        status = {}
        for name, limiter in self.limiters.items():
            now = time.time()
            cutoff = now - limiter.config.period_seconds
            
            # Count recent requests
            recent_requests = sum(1 for t in limiter.request_times if t > cutoff)
            
            status[name] = {
                "requests_in_period": recent_requests,
                "max_requests": limiter.config.requests_per_period,
                "period_seconds": limiter.config.period_seconds,
                "can_make_request": limiter.can_make_request(),
                "delay_needed": limiter.get_delay(),
                "consecutive_failures": limiter.consecutive_failures,
                "last_request": limiter.last_request_time
            }
        
        return status


# Global instance
_global_limiter = GlobalRateLimiter()


def get_rate_limiter(name: str, config: Optional[RateLimitConfig] = None) -> RateLimiter:
    """Get a named rate limiter from the global instance."""
    return _global_limiter.get_limiter(name, config)


def rate_limited(limiter_name: str, record_success: bool = True):
    """Decorator for rate limiting function calls.
    
    Args:
        limiter_name: Name of rate limiter to use
        record_success: Whether to record all calls as successful
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter = get_rate_limiter(limiter_name)
            limiter.wait_if_needed()
            
            try:
                result = func(*args, **kwargs)
                limiter.record_request(success=True)
                return result
            except Exception as e:
                limiter.record_request(success=False)
                raise
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            limiter = get_rate_limiter(limiter_name)
            await limiter.async_wait_if_needed()
            
            try:
                result = await func(*args, **kwargs)
                limiter.record_request(success=True)
                return result
            except Exception as e:
                limiter.record_request(success=False)
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper
    
    return decorator


def adaptive_delay(base_delay: float, failure_count: int, max_delay: float = 300.0) -> float:
    """Calculate adaptive delay based on failure count.
    
    Args:
        base_delay: Base delay in seconds
        failure_count: Number of consecutive failures
        max_delay: Maximum delay in seconds
        
    Returns:
        Calculated delay in seconds
    """
    if failure_count == 0:
        return base_delay
    
    # Exponential backoff with jitter
    delay = base_delay * (2 ** min(failure_count, 10))  # Cap at 2^10
    delay = min(delay, max_delay)
    
    # Add jitter (±20%)
    jitter = random.uniform(-0.2, 0.2) * delay
    return max(0, delay + jitter)


def smart_delay(min_delay: float, max_delay: float, success_rate: float = 1.0) -> float:
    """Calculate smart delay based on success rate.
    
    Args:
        min_delay: Minimum delay
        max_delay: Maximum delay  
        success_rate: Recent success rate (0.0 to 1.0)
        
    Returns:
        Calculated delay in seconds
    """
    # More failures = longer delay
    delay_range = max_delay - min_delay
    delay = min_delay + (delay_range * (1.0 - success_rate))
    
    # Add small random component
    jitter = random.uniform(0.8, 1.2)
    return delay * jitter


class SlidingWindowCounter:
    """Sliding window counter for tracking requests over time."""
    
    def __init__(self, window_size: int):
        """Initialize sliding window counter.
        
        Args:
            window_size: Window size in seconds
        """
        self.window_size = window_size
        self.requests = deque()
    
    def add_request(self, timestamp: Optional[float] = None) -> None:
        """Add a request to the counter."""
        if timestamp is None:
            timestamp = time.time()
        
        self.requests.append(timestamp)
        self._cleanup()
    
    def get_count(self) -> int:
        """Get current count in window."""
        self._cleanup()
        return len(self.requests)
    
    def _cleanup(self) -> None:
        """Remove old requests outside window."""
        cutoff = time.time() - self.window_size
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()


# Convenience functions
def wait_for_scraping():
    """Wait for scraping rate limit."""
    _global_limiter.wait_for("scraping")


def wait_for_email():
    """Wait for email rate limit."""
    _global_limiter.wait_for("email")


def wait_for_analysis():
    """Wait for analysis rate limit."""
    _global_limiter.wait_for("analysis")


def record_scraping_request(success: bool = True):
    """Record scraping request."""
    _global_limiter.record_request("scraping", success)


def record_email_request(success: bool = True):
    """Record email request."""
    _global_limiter.record_request("email", success)


def record_analysis_request(success: bool = True):
    """Record analysis request."""
    _global_limiter.record_request("analysis", success)


def get_rate_limit_status() -> Dict[str, Dict[str, Any]]:
    """Get status of all rate limiters."""
    return _global_limiter.get_status() 