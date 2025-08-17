"""
DShield client for threat intelligence and IP reputation lookup.

This module provides a client for interacting with the DShield threat intelligence API.
It supports IP reputation lookups, attack summaries, batch enrichment, and detailed
IP information retrieval. The client handles authentication, rate limiting, caching,
and error handling for robust integration with DShield services.

Features:
- IP reputation and details lookup
- Attack summary retrieval
- Batch enrichment of IPs
- Caching and rate limiting
- Async context management

Example:
    >>> from src.dshield_client import DShieldClient
    >>> async with DShieldClient() as client:
    ...     rep = await client.get_ip_reputation("8.8.8.8")
    ...     print(rep)
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import aiohttp
import structlog
from dotenv import load_dotenv

from .models import ThreatIntelligence
from .config_loader import get_config, ConfigError
from .op_secrets import OnePasswordSecrets
from .user_config import get_user_config

# Load environment variables
load_dotenv()

logger = structlog.get_logger(__name__)


class DShieldClient:
    """Client for interacting with DShield threat intelligence API.
    
    This class provides methods to query DShield for IP reputation, details,
    attack summaries, and batch enrichment. It manages authentication, rate
    limiting, caching, and session lifecycle for efficient API usage.
    
    Attributes:
        api_key: API key for DShield authentication
        base_url: Base URL for DShield API
        session: aiohttp.ClientSession for HTTP requests
        rate_limit_requests: Max requests per minute
        rate_limit_window: Time window for rate limiting (seconds)
        request_times: List of request timestamps for rate limiting
        cache: In-memory cache for API responses
        cache_ttl: Time-to-live for cache entries (seconds)
        enable_caching: Whether caching is enabled
        max_cache_size: Maximum cache size
        request_timeout: Timeout for API requests (seconds)
        enable_performance_logging: Whether to log performance metrics
        headers: HTTP headers for API requests
        batch_size: Maximum batch size for IP enrichment
    
    Example:
        >>> async with DShieldClient() as client:
        ...     rep = await client.get_ip_reputation("8.8.8.8")
        ...     print(rep)
    """
    
    def __init__(self) -> None:
        """Initialize the DShield client.
        
        Loads configuration, resolves secrets, sets up rate limiting,
        caching, and prepares HTTP headers for API requests.
        
        Raises:
            RuntimeError: If configuration or secret resolution fails
        """
        try:
            config = get_config()
            secrets_config = config.get("secrets", {})
            dshield_api_key = secrets_config.get("dshield_api_key")
            dshield_api_url = secrets_config.get("dshield_api_url", "https://dshield.org/api")
            rate_limit = secrets_config.get("rate_limit_requests_per_minute", 60)
            cache_ttl = secrets_config.get("cache_ttl_seconds", 300)
            batch_size = secrets_config.get("max_ip_enrichment_batch_size", 100)
        except Exception as e:
            raise RuntimeError(f"Failed to load DShield config: {e}")

        # 1Password resolution if needed
        op = OnePasswordSecrets()
        self.api_key = op.resolve_environment_variable(dshield_api_key) if dshield_api_key else None
        self.base_url = dshield_api_url
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiting
        self.rate_limit_requests = int(rate_limit)
        self.rate_limit_window = 60  # seconds
        self.request_times: List[float] = []
        
        # Cache for IP reputation data
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = int(cache_ttl)
        
        # Load user configuration
        user_config = get_user_config()
        self.enable_caching = user_config.get_setting("performance", "enable_caching")
        self.max_cache_size = user_config.get_setting("performance", "max_cache_size")
        self.request_timeout = user_config.get_setting("performance", "request_timeout_seconds")
        self.enable_performance_logging = user_config.get_setting("logging", "enable_performance_logging")
        
        # Headers for API requests
        self.headers = {
            "User-Agent": "DShield-MCP/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
        
        self.batch_size = int(batch_size)
    
    async def __aenter__(self) -> "DShieldClient":
        """Async context manager entry.
        
        Returns:
            DShieldClient: The initialized client instance
        """
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit.
        
        Closes the HTTP session on exit.
        """
        await self.close()
    
    async def connect(self) -> None:
        """Initialize HTTP session.
        
        Creates an aiohttp.ClientSession for making API requests.
        Logs session initialization.
        """
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=self.headers
            )
            logger.info("DShield client session initialized")
    
    async def close(self) -> None:
        """Close HTTP session.
        
        Closes the aiohttp.ClientSession and releases resources.
        Logs session closure.
        """
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("DShield client session closed")
    
    async def get_ip_reputation(self, ip_address: str) -> Dict[str, Any]:
        """Get IP reputation from DShield.
        
        Looks up the reputation of a given IP address using the DShield API.
        Utilizes caching and rate limiting for efficiency.
        
        Args:
            ip_address: The IP address to look up
        
        Returns:
            Dictionary containing reputation data for the IP
        """
        
        # Check cache first
        cache_key = f"reputation_{ip_address}"
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            logger.debug("Returning cached IP reputation", ip_address=ip_address)
            return cached_data
        
        # Rate limiting
        await self._check_rate_limit()
        
        try:
            await self.connect()
            
            # DShield IP reputation endpoint
            url = urljoin(self.base_url, f"ip/{ip_address}")
            
            logger.info("Querying DShield IP reputation", ip_address=ip_address)
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    reputation_data = self._parse_ip_reputation(data, ip_address)
                    
                    # Cache the result
                    self._cache_data(cache_key, reputation_data)
                    
                    logger.info("IP reputation retrieved successfully", 
                               ip_address=ip_address,
                               reputation_score=reputation_data.get('reputation_score'))
                    
                    return reputation_data
                    
                elif response.status == 404:
                    # IP not found in DShield database
                    reputation_data = self._create_default_reputation(ip_address)
                    self._cache_data(cache_key, reputation_data)
                    return reputation_data
                    
                else:
                    logger.warning("DShield API returned non-200 status", 
                                  ip_address=ip_address,
                                  status=response.status)
                    return self._create_default_reputation(ip_address)
                    
        except aiohttp.ClientError as e:
            logger.error("HTTP error during IP reputation lookup", 
                        ip_address=ip_address, error=str(e))
            return self._create_default_reputation(ip_address)
            
        except Exception as e:
            logger.error("Unexpected error during IP reputation lookup", 
                        ip_address=ip_address, error=str(e))
            return self._create_default_reputation(ip_address)
    
    async def get_ip_details(self, ip_address: str) -> Dict[str, Any]:
        """Get detailed IP information from DShield.
        
        Retrieves detailed information for a given IP address from the DShield API.
        Utilizes caching and rate limiting for efficiency.
        
        Args:
            ip_address: The IP address to look up
        
        Returns:
            Dictionary containing detailed data for the IP
        """
        
        # Check cache first
        cache_key = f"details_{ip_address}"
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
        
        # Rate limiting
        await self._check_rate_limit()
        
        try:
            await self.connect()
            
            # DShield IP details endpoint
            url = urljoin(self.base_url, f"ip/{ip_address}/details")
            
            logger.info("Querying DShield IP details", ip_address=ip_address)
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    details_data = self._parse_ip_details(data, ip_address)
                    
                    # Cache the result
                    self._cache_data(cache_key, details_data)
                    
                    return details_data
                    
                else:
                    logger.warning("DShield details API returned non-200 status", 
                                  ip_address=ip_address,
                                  status=response.status)
                    return self._create_default_details(ip_address)
                    
        except Exception as e:
            logger.error("Error during IP details lookup", 
                        ip_address=ip_address, error=str(e))
            return self._create_default_details(ip_address)
    
    async def get_top_attackers(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get top attackers from DShield."""
        
        # Rate limiting
        await self._check_rate_limit()
        
        try:
            await self.connect()
            
            # DShield top attackers endpoint
            url = urljoin(self.base_url, f"topattackers/{hours}")
            
            logger.info("Querying DShield top attackers", hours=hours)
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_top_attackers(data)
                    
                else:
                    logger.warning("DShield top attackers API returned non-200 status", 
                                  status=response.status)
                    return []
                    
        except Exception as e:
            logger.error("Error during top attackers lookup", error=str(e))
            return []
    
    async def get_attack_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get attack summary from DShield."""
        
        # Rate limiting
        await self._check_rate_limit()
        
        try:
            await self.connect()
            
            # DShield attack summary endpoint
            url = urljoin(self.base_url, f"summary/{hours}")
            
            logger.info("Querying DShield attack summary", hours=hours)
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_attack_summary(data)
                    
                else:
                    logger.warning("DShield summary API returned non-200 status", 
                                  status=response.status)
                    return self._create_default_summary()
                    
        except Exception as e:
            logger.error("Error during attack summary lookup", error=str(e))
            return self._create_default_summary()
    
    async def enrich_ips_batch(self, ip_addresses: List[str]) -> Dict[str, Dict[str, Any]]:
        """Enrich multiple IP addresses with threat intelligence."""
        
        results = {}
        
        batch_size = self.batch_size
        for i in range(0, len(ip_addresses), batch_size):
            batch = ip_addresses[i:i + batch_size]
            
            # Process batch concurrently
            tasks = [self.get_ip_reputation(ip) for ip in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Store results
            for ip, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.warning("Failed to enrich IP", ip=ip, error=str(result))
                    results[ip] = self._create_default_reputation(ip)
                else:
                    results[ip] = result
            
            # Small delay between batches
            if i + batch_size < len(ip_addresses):
                await asyncio.sleep(1)
        
        return results
    
    async def health_check(self) -> bool:
        """Check DShield API connectivity and authentication (placeholder)."""
        # TODO: Implement actual connectivity check
        await asyncio.sleep(0.01)
        return True
    
    def _parse_ip_reputation(self, data: Dict[str, Any], ip_address: str) -> Dict[str, Any]:
        """Parse DShield IP reputation response."""
        
        reputation_data = {
            'ip_address': ip_address,
            'reputation_score': None,
            'threat_level': 'unknown',
            'country': None,
            'asn': None,
            'organization': None,
            'first_seen': None,
            'last_seen': None,
            'attack_types': [],
            'tags': [],
            'raw_data': data
        }
        
        try:
            # Extract reputation score
            if 'reputation' in data:
                reputation_data['reputation_score'] = float(data['reputation'])
                
                # Determine threat level based on reputation score
                if reputation_data['reputation_score'] >= 80:
                    reputation_data['threat_level'] = 'high'
                elif reputation_data['reputation_score'] >= 50:
                    reputation_data['threat_level'] = 'medium'
                else:
                    reputation_data['threat_level'] = 'low'
            
            # Extract geographic information
            if 'country' in data:
                reputation_data['country'] = data['country']
            
            # Extract ASN information
            if 'as' in data:
                reputation_data['asn'] = data['as']
            
            # Extract organization
            if 'org' in data:
                reputation_data['organization'] = data['org']
            
            # Extract timestamps
            if 'firstseen' in data:
                reputation_data['first_seen'] = data['firstseen']
            
            if 'lastseen' in data:
                reputation_data['last_seen'] = data['lastseen']
            
            # Extract attack types
            if 'attacks' in data:
                reputation_data['attack_types'] = data['attacks']
            
            # Extract tags
            if 'tags' in data:
                reputation_data['tags'] = data['tags']
            
        except Exception as e:
            logger.warning("Failed to parse IP reputation data", 
                          ip_address=ip_address, error=str(e))
        
        return reputation_data
    
    def _parse_ip_details(self, data: Dict[str, Any], ip_address: str) -> Dict[str, Any]:
        """Parse DShield IP details response."""
        
        details_data = {
            'ip_address': ip_address,
            'raw_data': data
        }
        
        try:
            # Extract additional details from the response
            for key, value in data.items():
                if key not in ['raw_data']:
                    details_data[key] = value
                    
        except Exception as e:
            logger.warning("Failed to parse IP details data", 
                          ip_address=ip_address, error=str(e))
        
        return details_data
    
    def _parse_top_attackers(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse DShield top attackers response."""
        
        attackers = []
        
        try:
            for attacker in data:
                attacker_info = {
                    'ip_address': attacker.get('ip'),
                    'attack_count': attacker.get('count', 0),
                    'country': attacker.get('country'),
                    'asn': attacker.get('as'),
                    'organization': attacker.get('org')
                }
                attackers.append(attacker_info)
                
        except Exception as e:
            logger.warning("Failed to parse top attackers data", error=str(e))
        
        return attackers
    
    def _parse_attack_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse DShield attack summary response."""
        
        summary = {
            'total_attacks': 0,
            'unique_attackers': 0,
            'top_countries': [],
            'top_ports': [],
            'raw_data': data
        }
        
        try:
            # Extract summary statistics
            if 'total' in data:
                summary['total_attacks'] = data['total']
            
            if 'unique' in data:
                summary['unique_attackers'] = data['unique']
            
            if 'countries' in data:
                summary['top_countries'] = data['countries']
            
            if 'ports' in data:
                summary['top_ports'] = data['ports']
                
        except Exception as e:
            logger.warning("Failed to parse attack summary data", error=str(e))
        
        return summary
    
    def _create_default_reputation(self, ip_address: str) -> Dict[str, Any]:
        """Create default reputation data for IP."""
        return {
            'ip_address': ip_address,
            'reputation_score': None,
            'threat_level': 'unknown',
            'country': None,
            'asn': None,
            'organization': None,
            'first_seen': None,
            'last_seen': None,
            'attack_types': [],
            'tags': [],
            'raw_data': {}
        }
    
    def _create_default_details(self, ip_address: str) -> Dict[str, Any]:
        """Create default details data for IP."""
        return {
            'ip_address': ip_address,
            'raw_data': {}
        }
    
    def _create_default_summary(self) -> Dict[str, Any]:
        """Create default attack summary."""
        return {
            'total_attacks': 0,
            'unique_attackers': 0,
            'top_countries': [],
            'top_ports': [],
            'raw_data': {}
        }
    
    def _get_cached_data(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get data from cache if not expired."""
        if cache_key in self.cache:
            cached_item = self.cache[cache_key]
            if time.time() - cached_item['timestamp'] < self.cache_ttl:
                return cached_item['data']
            else:
                # Remove expired cache entry
                del self.cache[cache_key]
        return None
    
    def _cache_data(self, cache_key: str, data: Dict[str, Any]):
        """Cache data with timestamp."""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    async def check_health(self) -> bool:
        """Check DShield API connectivity and authentication.
        
        Returns:
            bool: True if DShield API is healthy and accessible, False otherwise
        """
        try:
            # Check if we have valid configuration
            if not self.base_url:
                logger.error("DShield API base URL not configured")
                return False
            
            if not self.api_key:
                logger.warning("DShield API key not configured - some endpoints may not work")
                # Continue with health check but note the limitation
            
            # Try to connect and make a simple test request
            await self.connect()
            
            if not self.session:
                logger.error("Failed to create DShield client session")
                return False
            
            # Make a simple health check request to test connectivity
            # Use a simple endpoint that doesn't require authentication
            try:
                # Try to access the base URL to test connectivity
                test_url = self.base_url
                
                async with self.session.get(test_url, timeout=10) as response:
                    if response.status in [200, 401, 403, 404]:  # 404 means API is reachable but endpoint not found
                        logger.debug("DShield API connectivity test passed", 
                                   status=response.status, 
                                   url=test_url)
                        return True
                    else:
                        logger.warning("DShield API returned unexpected status", 
                                     status=response.status, 
                                     url=test_url)
                        return False
                        
            except aiohttp.ClientError as e:
                logger.error("DShield API connectivity test failed", error=str(e))
                return False
            except asyncio.TimeoutError:
                logger.error("DShield API connectivity test timed out")
                return False
                
        except Exception as e:
            logger.error("DShield API health check failed", error=str(e))
            return False

    async def _check_rate_limit(self):
        """Check and enforce rate limiting."""
        current_time = time.time()
        
        # Remove old request times outside the window
        self.request_times = [t for t in self.request_times 
                            if current_time - t < self.rate_limit_window]
        
        # Check if we're at the rate limit
        if len(self.request_times) >= self.rate_limit_requests:
            # Calculate wait time
            oldest_request = min(self.request_times)
            wait_time = self.rate_limit_window - (current_time - oldest_request)
            
            if wait_time > 0:
                logger.info("Rate limit reached, waiting", wait_time=wait_time)
                await asyncio.sleep(wait_time)
        
        # Add current request time
        self.request_times.append(current_time) 