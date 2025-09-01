"""Rate limiting system for API keys and connections.

This module provides comprehensive rate limiting functionality to prevent
abuse and ensure fair resource usage across all API keys and connections.
"""

import asyncio
import time
from collections import defaultdict, deque
from typing import Dict, Optional, Set
import structlog

logger = structlog.get_logger(__name__)


class RateLimiter:
    """Token bucket rate limiter for API keys and connections."""
    
    def __init__(self, requests_per_minute: int = 60, burst_size: Optional[int] = None) -> None:
        """Initialize the rate limiter.
        
        Args:
            requests_per_minute: Maximum requests per minute
            burst_size: Maximum burst size (defaults to requests_per_minute)
        """
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size or requests_per_minute
        self.tokens = self.burst_size
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
    
    async def is_allowed(self) -> bool:
        """Check if a request is allowed under the rate limit.
        
        Returns:
            True if request is allowed, False otherwise
        """
        async with self.lock:
            now = time.time()
            time_passed = now - self.last_refill
            
            # Refill tokens based on time passed
            tokens_to_add = time_passed * (self.requests_per_minute / 60.0)
            self.tokens = min(self.burst_size, self.tokens + tokens_to_add)
            self.last_refill = now
            
            # Check if we have tokens available
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            else:
                return False
    
    async def get_wait_time(self) -> float:
        """Get the time to wait before the next request is allowed.
        
        Returns:
            Time in seconds to wait
        """
        async with self.lock:
            if self.tokens >= 1:
                return 0.0
            
            # Calculate time needed to get one token
            tokens_needed = 1 - self.tokens
            return tokens_needed / (self.requests_per_minute / 60.0)


class SlidingWindowRateLimiter:
    """Sliding window rate limiter for more precise rate limiting."""
    
    def __init__(self, requests_per_minute: int = 60, window_size: int = 60) -> None:
        """Initialize the sliding window rate limiter.
        
        Args:
            requests_per_minute: Maximum requests per minute
            window_size: Window size in seconds
        """
        self.requests_per_minute = requests_per_minute
        self.window_size = window_size
        self.requests = deque()
        self.lock = asyncio.Lock()
    
    async def is_allowed(self) -> bool:
        """Check if a request is allowed under the rate limit.
        
        Returns:
            True if request is allowed, False otherwise
        """
        async with self.lock:
            now = time.time()
            
            # Remove old requests outside the window
            while self.requests and self.requests[0] <= now - self.window_size:
                self.requests.popleft()
            
            # Check if we're under the limit
            if len(self.requests) < self.requests_per_minute:
                self.requests.append(now)
                return True
            else:
                return False
    
    async def get_wait_time(self) -> float:
        """Get the time to wait before the next request is allowed.
        
        Returns:
            Time in seconds to wait
        """
        async with self.lock:
            now = time.time()
            
            # Remove old requests outside the window
            while self.requests and self.requests[0] <= now - self.window_size:
                self.requests.popleft()
            
            if len(self.requests) < self.requests_per_minute:
                return 0.0
            
            # Return time until the oldest request in window expires
            return self.requests[0] + self.window_size - now


class APIKeyRateLimiter:
    """Rate limiter for individual API keys."""
    
    def __init__(self) -> None:
        """Initialize the API key rate limiter."""
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self.blocked_keys: Set[str] = set()
        self.lock = asyncio.Lock()
        self.logger = structlog.get_logger(__name__)
    
    async def create_rate_limiter(self, key_id: str, requests_per_minute: int) -> None:
        """Create a rate limiter for an API key.
        
        Args:
            key_id: The API key ID
            requests_per_minute: Rate limit for this key
        """
        async with self.lock:
            self.rate_limiters[key_id] = RateLimiter(requests_per_minute)
            if key_id in self.blocked_keys:
                self.blocked_keys.remove(key_id)
            self.logger.info("Created rate limiter for API key", 
                           key_id=key_id, 
                           requests_per_minute=requests_per_minute)
    
    async def is_allowed(self, key_id: str) -> bool:
        """Check if a request is allowed for an API key.
        
        Args:
            key_id: The API key ID
            
        Returns:
            True if request is allowed, False otherwise
        """
        # Check if key is blocked
        if key_id in self.blocked_keys:
            self.logger.warning("Request blocked for API key", key_id=key_id)
            return False
        
        # Get or create rate limiter
        async with self.lock:
            if key_id not in self.rate_limiters:
                # Default rate limit for unknown keys
                self.rate_limiters[key_id] = RateLimiter(10)  # Conservative default
        
        rate_limiter = self.rate_limiters[key_id]
        is_allowed = await rate_limiter.is_allowed()
        
        if not is_allowed:
            self.logger.warning("Rate limit exceeded for API key", key_id=key_id)
        
        return is_allowed
    
    async def get_wait_time(self, key_id: str) -> float:
        """Get the time to wait before the next request is allowed.
        
        Args:
            key_id: The API key ID
            
        Returns:
            Time in seconds to wait
        """
        async with self.lock:
            if key_id not in self.rate_limiters:
                return 0.0
        
        rate_limiter = self.rate_limiters[key_id]
        return await rate_limiter.get_wait_time()
    
    async def block_key(self, key_id: str, reason: str = "Manual block") -> None:
        """Block an API key from making requests.
        
        Args:
            key_id: The API key ID to block
            reason: Reason for blocking
        """
        async with self.lock:
            self.blocked_keys.add(key_id)
            self.logger.warning("API key blocked", key_id=key_id, reason=reason)
    
    async def unblock_key(self, key_id: str) -> None:
        """Unblock an API key.
        
        Args:
            key_id: The API key ID to unblock
        """
        async with self.lock:
            self.blocked_keys.discard(key_id)
            self.logger.info("API key unblocked", key_id=key_id)
    
    async def remove_key(self, key_id: str) -> None:
        """Remove an API key's rate limiter.
        
        Args:
            key_id: The API key ID to remove
        """
        async with self.lock:
            self.rate_limiters.pop(key_id, None)
            self.blocked_keys.discard(key_id)
            self.logger.info("Rate limiter removed for API key", key_id=key_id)
    
    async def get_key_stats(self, key_id: str) -> Dict[str, any]:
        """Get rate limiting statistics for an API key.
        
        Args:
            key_id: The API key ID
            
        Returns:
            Dictionary with rate limiting statistics
        """
        async with self.lock:
            if key_id not in self.rate_limiters:
                return {"error": "Key not found"}
            
            rate_limiter = self.rate_limiters[key_id]
            wait_time = await rate_limiter.get_wait_time()
            
            return {
                "key_id": key_id,
                "requests_per_minute": rate_limiter.requests_per_minute,
                "burst_size": rate_limiter.burst_size,
                "current_tokens": rate_limiter.tokens,
                "wait_time": wait_time,
                "is_blocked": key_id in self.blocked_keys
            }


class ConnectionRateLimiter:
    """Rate limiter for individual connections."""
    
    def __init__(self) -> None:
        """Initialize the connection rate limiter."""
        self.rate_limiters: Dict[str, SlidingWindowRateLimiter] = {}
        self.blocked_connections: Set[str] = set()
        self.lock = asyncio.Lock()
        self.logger = structlog.get_logger(__name__)
    
    async def is_allowed(self, connection_id: str) -> bool:
        """Check if a request is allowed for a connection.
        
        Args:
            connection_id: The connection ID
            
        Returns:
            True if request is allowed, False otherwise
        """
        # Check if connection is blocked
        if connection_id in self.blocked_connections:
            self.logger.warning("Request blocked for connection", connection_id=connection_id)
            return False
        
        # Get or create rate limiter
        async with self.lock:
            if connection_id not in self.rate_limiters:
                # Default rate limit for connections
                self.rate_limiters[connection_id] = SlidingWindowRateLimiter(100)  # 100 req/min
        
        rate_limiter = self.rate_limiters[connection_id]
        is_allowed = await rate_limiter.is_allowed()
        
        if not is_allowed:
            self.logger.warning("Rate limit exceeded for connection", connection_id=connection_id)
        
        return is_allowed
    
    async def block_connection(self, connection_id: str, reason: str = "Manual block") -> None:
        """Block a connection from making requests.
        
        Args:
            connection_id: The connection ID to block
            reason: Reason for blocking
        """
        async with self.lock:
            self.blocked_connections.add(connection_id)
            self.logger.warning("Connection blocked", connection_id=connection_id, reason=reason)
    
    async def unblock_connection(self, connection_id: str) -> None:
        """Unblock a connection.
        
        Args:
            connection_id: The connection ID to unblock
        """
        async with self.lock:
            self.blocked_connections.discard(connection_id)
            self.logger.info("Connection unblocked", connection_id=connection_id)
    
    async def remove_connection(self, connection_id: str) -> None:
        """Remove a connection's rate limiter.
        
        Args:
            connection_id: The connection ID to remove
        """
        async with self.lock:
            self.rate_limiters.pop(connection_id, None)
            self.blocked_connections.discard(connection_id)
            self.logger.info("Rate limiter removed for connection", connection_id=connection_id)


class GlobalRateLimiter:
    """Global rate limiter for the entire server."""
    
    def __init__(self, max_requests_per_minute: int = 1000) -> None:
        """Initialize the global rate limiter.
        
        Args:
            max_requests_per_minute: Maximum total requests per minute
        """
        self.rate_limiter = SlidingWindowRateLimiter(max_requests_per_minute)
        self.logger = structlog.get_logger(__name__)
    
    async def is_allowed(self) -> bool:
        """Check if a request is allowed under the global rate limit.
        
        Returns:
            True if request is allowed, False otherwise
        """
        is_allowed = await self.rate_limiter.is_allowed()
        
        if not is_allowed:
            self.logger.warning("Global rate limit exceeded")
        
        return is_allowed
    
    async def get_wait_time(self) -> float:
        """Get the time to wait before the next request is allowed.
        
        Returns:
            Time in seconds to wait
        """
        return await self.rate_limiter.get_wait_time()
