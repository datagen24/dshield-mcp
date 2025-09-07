"""Threat Intelligence Manager for DShield MCP.

This module provides a centralized manager for coordinating multiple threat intelligence
sources including DShield, VirusTotal, Shodan, and other security APIs. It handles
source coordination, rate limiting, caching, and result correlation.

Features:
- Multi-source threat intelligence aggregation
- Intelligent correlation and scoring
- Advanced caching with configurable TTL
- Rate limiting and error handling
- Extensible architecture for new sources

Example:
    >>> from src.threat_intelligence_manager import ThreatIntelligenceManager
    >>> async with ThreatIntelligenceManager() as manager:
    ...     result = await manager.enrich_ip_comprehensive("8.8.8.8")
    ...     print(result.overall_threat_score)

"""

import asyncio
import os
import sqlite3
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from .config_loader import get_config
from .dshield_client import DShieldClient
from .models import (
    DomainIntelligence,
    ThreatIntelligenceResult,
    ThreatIntelligenceSource,
)
from .user_config import get_user_config

logger = structlog.get_logger(__name__)


class ThreatIntelligenceManager:
    """Manages multiple threat intelligence sources and correlation.

    This class provides a unified interface for querying multiple threat intelligence
    sources, aggregating results, and providing comprehensive threat assessments.
    It handles rate limiting, caching, error handling, and result correlation.

    Attributes:
        config: Application configuration
        user_config: User-specific configuration
        clients: Dictionary of source clients
        correlation_config: Correlation settings
        confidence_threshold: Minimum confidence threshold
        max_sources: Maximum sources per query
        cache: In-memory cache for results
        cache_ttl: Cache time-to-live
        rate_limit_trackers: Rate limiting trackers per source

    Example:
        >>> async with ThreatIntelligenceManager() as manager:
        ...     result = await manager.enrich_ip_comprehensive("8.8.8.8")
        ...     print(f"Threat score: {result.overall_threat_score}")

    """

    def __init__(self) -> None:
        """Initialize the threat intelligence manager.

        Loads configuration, initializes source clients, and sets up
        correlation and caching parameters.

        Raises:
            RuntimeError: If configuration loading fails

        """
        try:
            self.config = get_config()
            self.user_config = get_user_config()
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration: {e}") from e

        # Initialize source clients
        self.clients: dict[ThreatIntelligenceSource, Any] = {}
        self._initialize_clients()

        # Correlation settings
        threat_intel_config = self.config.get("threat_intelligence", {})
        self.correlation_config = threat_intel_config.get("correlation", {})
        self.confidence_threshold = self.correlation_config.get("confidence_threshold", 0.7)
        self.max_sources = self.correlation_config.get("max_sources_per_query", 3)

        # Cache for aggregated results
        self.cache: dict[str, ThreatIntelligenceResult] = {}
        cache_ttl_hours = threat_intel_config.get("cache_ttl_hours", 1)
        self.cache_ttl = timedelta(hours=cache_ttl_hours)

        # SQLite cache configuration
        self.sqlite_cache_enabled = self.user_config.performance_settings.enable_sqlite_cache
        self.sqlite_cache_path = self.user_config.get_cache_database_path()
        self.sqlite_cache_ttl = timedelta(
            hours=self.user_config.performance_settings.sqlite_cache_ttl_hours
        )

        if self.sqlite_cache_enabled:
            self._initialize_sqlite_cache()

        # Rate limiting trackers and concurrency controls
        self.rate_limit_trackers: dict[ThreatIntelligenceSource, list[float]] = {}
        self.concurrency_semaphores: dict[ThreatIntelligenceSource, asyncio.Semaphore] = {}
        self._initialize_rate_limit_trackers()

        # Elasticsearch client for enrichment writeback
        self.elasticsearch_client = None
        self._initialize_elasticsearch()

        logger.info(
            "Enhanced Threat Intelligence Manager initialized",
            sources=list(self.clients.keys()),
            confidence_threshold=self.confidence_threshold,
            max_sources=self.max_sources,
            cache_ttl_hours=cache_ttl_hours,
            sqlite_cache_enabled=self.sqlite_cache_enabled,
            sqlite_cache_path=self.sqlite_cache_path,
            elasticsearch_writeback_enabled=self.elasticsearch_client is not None,
        )

    def _initialize_clients(self) -> None:
        """Initialize threat intelligence source clients."""
        sources_config = self.config.get("threat_intelligence", {}).get("sources", {})

        # Initialize DShield client (existing)
        if sources_config.get("dshield", {}).get("enabled", True):
            try:
                self.clients[ThreatIntelligenceSource.DSHIELD] = DShieldClient()
                logger.info("DShield client initialized")
            except Exception as e:
                logger.warning("Failed to initialize DShield client", error=str(e))

        # Initialize VirusTotal client (placeholder for future implementation)
        if sources_config.get("virustotal", {}).get("enabled", False):
            logger.info("VirusTotal client not yet implemented")
            # self.clients[ThreatIntelligenceSource.VIRUSTOTAL] = VirusTotalClient()

        # Initialize Shodan client (placeholder for future implementation)
        if sources_config.get("shodan", {}).get("enabled", False):
            logger.info("Shodan client not yet implemented")
            # self.clients[ThreatIntelligenceSource.SHODAN] = ShodanClient()

        if not self.clients:
            logger.warning("No threat intelligence clients initialized")

    def _initialize_sqlite_cache(self) -> None:
        """Initialize SQLite cache database.

        Creates the database file and tables if they don't exist.
        Sets up proper indexes for efficient querying.
        """
        try:
            # Ensure the database directory exists
            db_dir = os.path.dirname(self.sqlite_cache_path)
            os.makedirs(db_dir, exist_ok=True)

            with sqlite3.connect(self.sqlite_cache_path) as conn:
                # Create the enrichment cache table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS enrichment_cache (
                        indicator TEXT NOT NULL,
                        source TEXT NOT NULL,
                        result_json TEXT NOT NULL,
                        retrieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL,
                        PRIMARY KEY (indicator, source)
                    )
                """)

                # Create indexes for efficient querying
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_enrichment_expires_at ON enrichment_cache(expires_at)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_enrichment_indicator ON enrichment_cache(indicator)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_enrichment_source ON enrichment_cache(source)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_enrichment_retrieved_at ON enrichment_cache(retrieved_at)"
                )

                # Clean up expired entries
                conn.execute("DELETE FROM enrichment_cache WHERE expires_at < datetime('now')")

                conn.commit()

            logger.info(
                "SQLite cache initialized",
                db_path=self.sqlite_cache_path,
                ttl_hours=self.user_config.performance_settings.sqlite_cache_ttl_hours,
            )
        except Exception as e:
            logger.warning(
                "Failed to initialize SQLite cache", error=str(e), db_path=self.sqlite_cache_path
            )
            # Disable SQLite cache if initialization fails
            self.sqlite_cache_enabled = False

    def _initialize_rate_limit_trackers(self) -> None:
        """Initialize rate limiting trackers and concurrency controls for each source."""
        for source in self.clients.keys():
            self.rate_limit_trackers[source] = []

            # Initialize concurrency semaphores for each source
            sources_config = self.config.get("threat_intelligence", {}).get("sources", {})
            source_config = sources_config.get(source.value, {})
            concurrency_limit = source_config.get(
                "concurrency_limit", 5
            )  # Default 5 concurrent requests

            self.concurrency_semaphores[source] = asyncio.Semaphore(concurrency_limit)

        logger.info(
            "Rate limit trackers and concurrency controls initialized",
            sources=list(self.clients.keys()),
            concurrency_limits={
                source.value: self.concurrency_semaphores[source]._value
                for source in self.concurrency_semaphores.keys()
            },
        )

    async def __aenter__(self) -> "ThreatIntelligenceManager":
        """Async context manager entry.

        Returns:
            ThreatIntelligenceManager: The initialized manager instance

        """
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit.

        Cleans up resources and closes client connections.
        """
        await self.cleanup()

    async def enrich_ip_comprehensive(self, ip_address: str) -> ThreatIntelligenceResult:
        """Comprehensive IP enrichment from multiple sources.

        Queries all enabled threat intelligence sources for information about
        the specified IP address, aggregates results, and provides a comprehensive
        threat assessment.

        Args:
            ip_address: The IP address to enrich

        Returns:
            ThreatIntelligenceResult: Comprehensive threat intelligence data

        Raises:
            ValueError: If IP address is invalid
            RuntimeError: If no sources are available

        """
        # Validate IP address
        try:
            import ipaddress

            ipaddress.ip_address(ip_address)
        except ValueError:
            raise ValueError(f"Invalid IP address: {ip_address}") from None

        # Check cache first
        cache_key = f"comprehensive_ip_{ip_address}"

        # Check SQLite cache first (if enabled)
        if self.sqlite_cache_enabled:
            cached_result = await self._get_sqlite_cached_result(cache_key)
            if cached_result:
                logger.debug("Returning SQLite cached IP enrichment result", ip_address=ip_address)
                cached_result.cache_hit = True
                return cached_result

        # Check memory cache as fallback
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            logger.debug("Returning memory cached IP enrichment result", ip_address=ip_address)
            cached_result.cache_hit = True
            return cached_result

        if not self.clients:
            raise RuntimeError("No threat intelligence sources available")

        logger.info(
            "Starting comprehensive IP enrichment",
            ip_address=ip_address,
            available_sources=list(self.clients.keys()),
        )

        # Query all enabled sources concurrently
        tasks = []
        for source, client in self.clients.items():
            if hasattr(client, "get_ip_reputation"):
                tasks.append(self._query_source_async(source, client, ip_address))

        # Wait for all queries to complete
        source_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        result = ThreatIntelligenceResult(ip_address=ip_address)
        successful_sources = []

        for source, source_result in zip(self.clients.keys(), source_results, strict=False):
            if isinstance(source_result, Exception):
                logger.warning(
                    "Source query failed",
                    source=source,
                    ip_address=ip_address,
                    error=str(source_result),
                )
                continue

            result.source_results[source] = source_result
            successful_sources.append(source)

        result.sources_queried = successful_sources

        # Correlate and score results
        await self._correlate_results(result)

        # Cache the result in both SQLite and memory
        if self.sqlite_cache_enabled:
            self._cache_result_to_sqlite(cache_key, result)
        self._cache_result(cache_key, result)

        # Write to Elasticsearch for enrichment correlation
        await self._write_to_elasticsearch(result)

        logger.info(
            "IP enrichment completed",
            ip_address=ip_address,
            sources_queried=len(successful_sources),
            overall_threat_score=result.overall_threat_score,
            confidence_score=result.confidence_score,
        )

        return result

    async def enrich_domain_comprehensive(self, domain: str) -> DomainIntelligence:
        """Comprehensive domain enrichment from multiple sources.

        Queries all enabled threat intelligence sources for information about
        the specified domain, aggregates results, and provides a comprehensive
        threat assessment.

        Args:
            domain: The domain to enrich

        Returns:
            DomainIntelligence: Comprehensive domain threat intelligence data

        Raises:
            ValueError: If domain is invalid
            RuntimeError: If no sources are available

        """
        # Validate domain
        if not domain or "." not in domain:
            raise ValueError(f"Invalid domain: {domain}")

        # Check cache first
        cache_key = f"comprehensive_domain_{domain.lower()}"
        cached_result = self._get_cached_domain_result(cache_key)
        if cached_result:
            logger.debug("Returning cached domain enrichment result", domain=domain)
            cached_result.cache_hit = True
            return cached_result

        if not self.clients:
            raise RuntimeError("No threat intelligence sources available")

        logger.info(
            "Starting comprehensive domain enrichment",
            domain=domain,
            available_sources=list(self.clients.keys()),
        )

        # For now, return a basic result since domain enrichment is not yet implemented
        result = DomainIntelligence(
            domain=domain.lower(),
            registrar=None,
            creation_date=None,
            cache_hit=False,
        )
        result.sources_queried = []

        # TODO: Implement domain enrichment when VirusTotal and other clients are added

        # Cache the result
        self._cache_domain_result(cache_key, result)

        logger.info(
            "Domain enrichment completed",
            domain=domain,
            sources_queried=len(result.sources_queried),
        )

        return result

    async def correlate_threat_indicators(self, indicators: list[str]) -> dict[str, Any]:
        """Correlate multiple threat indicators across sources.

        Analyzes multiple threat indicators (IPs, domains, hashes, etc.) and
        finds correlations and relationships between them.

        Args:
            indicators: List of threat indicators to correlate

        Returns:
            Dictionary containing correlation results

        Raises:
            ValueError: If indicators list is empty

        """
        if not indicators:
            raise ValueError("Indicators list cannot be empty")

        logger.info(
            "Starting threat indicator correlation",
            indicator_count=len(indicators),
            indicators=indicators[:5],
        )  # Log first 5 for privacy

        # TODO: Implement indicator correlation logic
        # For now, return a basic structure
        result = {
            "correlation_id": f"corr_{int(time.time())}",
            "indicators": indicators,
            "correlations": [],
            "relationships": [],
            "confidence_score": 0.0,
            "sources_queried": [],
            "timestamp": datetime.now(UTC).isoformat(),
        }

        logger.info(
            "Threat indicator correlation completed",
            correlation_id=result["correlation_id"],
            confidence_score=result["confidence_score"],
        )

        return result

    async def _query_source_async(
        self, source: ThreatIntelligenceSource, client: Any, ip_address: str
    ) -> dict[str, Any]:
        """Query a single source asynchronously with concurrency control and timeout.

        Args:
            source: The threat intelligence source
            client: The source client instance
            ip_address: The IP address to query

        Returns:
            Dictionary containing source-specific results

        Raises:
            Exception: If the source query fails
            asyncio.TimeoutError: If the query times out

        """
        # Get source configuration
        sources_config = self.config.get("threat_intelligence", {}).get("sources", {})
        source_config = sources_config.get(source.value, {})
        timeout_seconds = source_config.get("timeout_seconds", 30)

        # Use concurrency semaphore if available
        semaphore = self.concurrency_semaphores.get(source)

        async def _execute_query() -> Any:
            # Check rate limiting
            await self._check_rate_limit(source)

            try:
                if source == ThreatIntelligenceSource.DSHIELD:
                    return await client.get_ip_reputation(ip_address)
                # TODO: Add other sources when implemented
                # elif source == ThreatIntelligenceSource.VIRUSTOTAL:
                #     return await client.get_ip_report(ip_address)
                # elif source == ThreatIntelligenceSource.SHODAN:
                #     return await client.get_host_info(ip_address)
                raise ValueError(f"Unknown source: {source}")
            except Exception as e:
                logger.error(
                    "Source query failed", source=source, ip_address=ip_address, error=str(e)
                )
                raise

        # Execute with concurrency control and timeout
        if semaphore:
            async with semaphore:
                return await asyncio.wait_for(_execute_query(), timeout=timeout_seconds)
        else:
            return await asyncio.wait_for(_execute_query(), timeout=timeout_seconds)

    async def _correlate_results(self, result: ThreatIntelligenceResult) -> None:
        """Correlate results from multiple sources using advanced algorithms.

        Analyzes results from different sources and calculates aggregated
        threat scores and confidence levels using weighted scoring, source
        reliability, and temporal correlation.

        Args:
            result: The threat intelligence result to correlate

        """
        if not result.source_results:
            logger.warning("No source results to correlate")
            return

        # Source reliability weights (can be configured)
        source_reliability = {
            ThreatIntelligenceSource.DSHIELD: 0.8,
            ThreatIntelligenceSource.VIRUSTOTAL: 0.9,
            ThreatIntelligenceSource.SHODAN: 0.7,
            ThreatIntelligenceSource.ABUSEIPDB: 0.8,
            ThreatIntelligenceSource.ALIENVAULT: 0.8,
            ThreatIntelligenceSource.THREATFOX: 0.7,
        }

        # Calculate weighted threat scores
        weighted_threat_scores = []
        weighted_confidence_scores = []
        source_weights = []

        for source, source_data in result.source_results.items():
            if isinstance(source_data, dict):
                reliability = source_reliability.get(source, 0.5)

                # Extract and normalize threat score
                threat_score = None
                if "threat_score" in source_data and source_data["threat_score"] is not None:
                    threat_score = float(source_data["threat_score"])
                elif (
                    "reputation_score" in source_data
                    and source_data["reputation_score"] is not None
                ):
                    # Convert reputation score to threat score (inverse relationship)
                    rep_score = float(source_data["reputation_score"])
                    threat_score = 100 - rep_score  # Higher reputation = lower threat

                if threat_score is not None:
                    # Apply source reliability weighting
                    weighted_score = threat_score * reliability
                    weighted_threat_scores.append(weighted_score)
                    source_weights.append(reliability)

                # Extract confidence score
                confidence = None
                if "confidence" in source_data:
                    confidence = float(source_data["confidence"])
                else:
                    # Default confidence based on source
                    default_confidence = {
                        ThreatIntelligenceSource.DSHIELD: 0.8,
                        ThreatIntelligenceSource.VIRUSTOTAL: 0.9,
                        ThreatIntelligenceSource.SHODAN: 0.7,
                    }.get(source, 0.5)
                    confidence = default_confidence

                if confidence is not None:
                    weighted_confidence_scores.append(confidence * reliability)

        # Calculate weighted averages
        if weighted_threat_scores and source_weights:
            total_weight = sum(source_weights)
            result.overall_threat_score = sum(weighted_threat_scores) / total_weight

        if weighted_confidence_scores and source_weights:
            total_weight = sum(source_weights)
            result.confidence_score = sum(weighted_confidence_scores) / total_weight

        # Advanced threat indicator correlation
        result.threat_indicators = await self._correlate_threat_indicators(result.source_results)

        # Aggregate geographic and network data with confidence weighting
        self._aggregate_geographic_data_advanced(result)
        self._aggregate_network_data_advanced(result)

        # Determine timestamps with temporal correlation
        self._determine_timestamps_advanced(result)

        # Calculate correlation metrics
        self._calculate_correlation_metrics(result)

    def _deduplicate_indicators(self, indicators: list[Any]) -> list[dict[str, Any]]:
        """Remove duplicate indicators and merge metadata.

        Args:
            indicators: List of raw indicators

        Returns:
            List of deduplicated indicators with metadata

        """
        if not indicators:
            return []

        # Convert to strings for deduplication
        indicator_strings = [str(indicator).lower() for indicator in indicators]
        unique_indicators = list(set(indicator_strings))

        # Create structured indicator objects
        structured_indicators = []
        for indicator in unique_indicators:
            structured_indicators.append(
                {
                    "indicator": indicator,
                    "type": self._classify_indicator(indicator),
                    "count": indicator_strings.count(indicator),
                    "sources": len(self.clients),  # All sources contributed
                }
            )

        return structured_indicators

    def _classify_indicator(self, indicator: str) -> str:
        """Classify the type of indicator.

        Args:
            indicator: The indicator string

        Returns:
            The indicator type classification

        """
        indicator_lower = indicator.lower()

        # IP address patterns
        if any(char.isdigit() for char in indicator_lower) and "." in indicator_lower:
            return "ip_address"

        # Domain patterns
        if "." in indicator_lower and not any(
            char.isdigit() for char in indicator_lower.split(".")[0]
        ):
            return "domain"

        # Hash patterns
        if len(indicator_lower) in [32, 40, 64] and all(
            c in "0123456789abcdef" for c in indicator_lower
        ):
            return "hash"

        # CVE patterns
        if indicator_lower.startswith("cve-"):
            return "cve"

        # Default to generic
        return "generic"

    def _aggregate_geographic_data(self, result: ThreatIntelligenceResult) -> None:
        """Aggregate geographic data from multiple sources.

        Args:
            result: The threat intelligence result to update

        """
        geographic_data = {}

        for source_data in result.source_results.values():
            if isinstance(source_data, dict):
                if "geographic_data" in source_data:
                    geographic_data.update(source_data["geographic_data"])
                elif "country" in source_data:
                    geographic_data["country"] = source_data["country"]

        result.geographic_data = geographic_data

    def _aggregate_network_data(self, result: ThreatIntelligenceResult) -> None:
        """Aggregate network data from multiple sources.

        Args:
            result: The threat intelligence result to update

        """
        network_data = {}

        for source_data in result.source_results.values():
            if isinstance(source_data, dict):
                if "network_data" in source_data:
                    network_data.update(source_data["network_data"])
                elif "asn" in source_data:
                    network_data["asn"] = source_data["asn"]
                elif "organization" in source_data:
                    network_data["organization"] = source_data["organization"]

        result.network_data = network_data

    def _determine_timestamps(self, result: ThreatIntelligenceResult) -> None:
        """Determine first and last seen timestamps across sources.

        Args:
            result: The threat intelligence result to update

        """
        first_seen_times = []
        last_seen_times = []

        for source_data in result.source_results.values():
            if isinstance(source_data, dict):
                if source_data.get("first_seen"):
                    first_seen_times.append(source_data["first_seen"])
                if source_data.get("last_seen"):
                    last_seen_times.append(source_data["last_seen"])

        if first_seen_times:
            result.first_seen = min(first_seen_times)

        if last_seen_times:
            result.last_seen = max(last_seen_times)

    async def _check_rate_limit(self, source: ThreatIntelligenceSource) -> None:
        """Check and enforce rate limiting for a source with exponential backoff.

        Args:
            source: The source to check rate limiting for

        Raises:
            RuntimeError: If rate limit would be exceeded after backoff attempts

        """
        if source not in self.rate_limit_trackers:
            return

        current_time = time.time()
        tracker = self.rate_limit_trackers[source]

        # Remove old entries (older than 1 minute)
        tracker[:] = [t for t in tracker if current_time - t < 60]

        # Get rate limit configuration
        sources_config = self.config.get("threat_intelligence", {}).get("sources", {})
        source_config = sources_config.get(source.value, {})
        rate_limit = source_config.get("rate_limit_requests_per_minute", 60)
        max_backoff_attempts = source_config.get("max_backoff_attempts", 3)

        # Check if we're at the rate limit
        if len(tracker) >= rate_limit:
            # Calculate wait time until we can make another request
            oldest_request = min(tracker)
            wait_time = 60 - (current_time - oldest_request)

            if wait_time > 0:
                logger.debug(
                    "Rate limit hit, waiting",
                    source=source.value,
                    wait_time=wait_time,
                    current_requests=len(tracker),
                    rate_limit=rate_limit,
                )

                # Implement exponential backoff
                for _attempt in range(max_backoff_attempts):
                    try:
                        await asyncio.sleep(wait_time)
                        break
                    except asyncio.CancelledError:
                        logger.warning("Rate limit wait cancelled", source=source.value)
                        raise RuntimeError(
                            f"Rate limit wait cancelled for {source.value}"
                        ) from None

                # Re-check after waiting
                current_time = time.time()
                tracker[:] = [t for t in tracker if current_time - t < 60]

                if len(tracker) >= rate_limit:
                    raise RuntimeError(f"Rate limit exceeded for {source.value} after backoff")

        tracker.append(current_time)

    def _get_cached_result(self, cache_key: str) -> ThreatIntelligenceResult | None:
        """Get cached result if available and not expired.

        Args:
            cache_key: The cache key to look up

        Returns:
            Cached result if available and valid, None otherwise

        """
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.now(UTC) - cached.query_timestamp < self.cache_ttl:
                return cached
            del self.cache[cache_key]
        return None

    def _cache_result(self, cache_key: str, result: ThreatIntelligenceResult) -> None:
        """Cache a result.

        Args:
            cache_key: The cache key
            result: The result to cache

        """
        self.cache[cache_key] = result

        # Implement cache size limit
        max_cache_size = self.config.get("threat_intelligence", {}).get("max_cache_size", 1000)
        if len(self.cache) > max_cache_size:
            # Remove oldest entries
            oldest_keys = sorted(self.cache.keys(), key=lambda k: self.cache[k].query_timestamp)[
                : len(self.cache) - max_cache_size
            ]
            for key in oldest_keys:
                del self.cache[key]

    def _get_cached_domain_result(self, cache_key: str) -> DomainIntelligence | None:
        """Get cached domain result if available and not expired.

        Args:
            cache_key: The cache key to look up

        Returns:
            Cached domain result if available and valid, None otherwise

        """
        # TODO: Implement domain result caching
        return None

    def _cache_domain_result(self, cache_key: str, result: DomainIntelligence) -> None:
        """Cache a domain result.

        Args:
            cache_key: The cache key
            result: The domain result to cache

        """
        # TODO: Implement domain result caching

    async def _get_sqlite_cached_result(self, cache_key: str) -> ThreatIntelligenceResult | None:
        """Get cached result from SQLite if available and not expired.

        Args:
            cache_key: The cache key to look up

        Returns:
            Cached result if available and valid, None otherwise

        """
        if not self.sqlite_cache_enabled:
            return None

        try:
            with sqlite3.connect(self.sqlite_cache_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT result_json, retrieved_at, expires_at
                    FROM enrichment_cache
                    WHERE indicator = ? AND source = ?
                """,
                    (cache_key, "comprehensive_ip"),
                )  # Assuming source is "comprehensive_ip" for now

                row = cursor.fetchone()

                if row:
                    result_json, _, expires_at_str = row
                    expires_at = datetime.fromisoformat(expires_at_str)

                    if datetime.now(UTC) < expires_at:
                        result = ThreatIntelligenceResult.model_validate_json(result_json)
                        result.cache_hit = True
                        return result
                    # Delete expired entry
                    conn.execute(
                        "DELETE FROM enrichment_cache WHERE indicator = ? AND source = ?",
                        (cache_key, "comprehensive_ip"),
                    )
                    conn.commit()
                    return None
                return None
        except Exception as e:
            logger.warning("Failed to get SQLite cached result", error=str(e), cache_key=cache_key)
            return None

    def _cache_result_to_sqlite(self, cache_key: str, result: ThreatIntelligenceResult) -> None:
        """Cache a result to SQLite.

        Args:
            cache_key: The cache key
            result: The result to cache

        """
        if not self.sqlite_cache_enabled:
            return

        try:
            with sqlite3.connect(self.sqlite_cache_path) as conn:
                # Convert datetime objects to strings for JSON serialization
                retrieved_at_str = result.query_timestamp.isoformat()
                expires_at_str = (result.query_timestamp + self.sqlite_cache_ttl).isoformat()

                conn.execute(
                    """
                    INSERT OR REPLACE INTO enrichment_cache (indicator, source, result_json, retrieved_at, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        cache_key,
                        "comprehensive_ip",
                        result.model_dump_json(),
                        retrieved_at_str,
                        expires_at_str,
                    ),
                )
                conn.commit()
            logger.debug("Cached result to SQLite", cache_key=cache_key)
        except Exception as e:
            logger.warning("Failed to cache result to SQLite", error=str(e), cache_key=cache_key)

    async def _write_to_elasticsearch(self, result: "ThreatIntelligenceResult") -> None:
        """Write enrichment result to Elasticsearch for correlation, if enabled in config."""
        es_config = self.config.get("threat_intelligence", {}).get("elasticsearch", {})
        writeback_enabled = es_config.get("writeback_enabled", False)
        if not (self.elasticsearch_client and writeback_enabled):
            return
        try:
            # Prepare document for Elasticsearch
            doc = {
                "indicator": result.ip_address,
                "indicator_type": "ip",
                "sources": result.source_results,
                "asn": result.network_data.get("asn"),
                "geo": result.geographic_data,
                "tags": [
                    indicator.get("type", "unknown") for indicator in result.threat_indicators
                ],
                "timestamp": result.query_timestamp.isoformat(),
                "threat_score": result.overall_threat_score,
                "confidence_score": result.confidence_score,
            }
            # Use index prefix from config if present
            index_prefix = es_config.get("index_prefix", "enrichment-intel")
            index_name = f"{index_prefix}-{result.query_timestamp.strftime('%Y.%m')}"
            await self.elasticsearch_client.index(
                index=index_name,
                document=doc,
                id=f"{result.ip_address}_{result.query_timestamp.isoformat()}",
            )
        except Exception as e:
            import structlog

            logger = structlog.get_logger(__name__)
            logger.warning("Failed to write to Elasticsearch", error=str(e))

    async def cleanup(self) -> None:
        """Clean up resources and close connections."""
        try:
            # Clean up expired entries from SQLite cache
            if self.sqlite_cache_enabled:
                self._cleanup_sqlite_cache()

            # Close client connections
            for client in self.clients.values():
                if hasattr(client, "cleanup"):
                    await client.cleanup()

            logger.info("Threat Intelligence Manager cleanup completed")
        except Exception as e:
            logger.error("Error during cleanup", error=str(e))

    def _cleanup_sqlite_cache(self) -> None:
        """Clean up expired entries from SQLite cache."""
        if not self.sqlite_cache_enabled:
            return

        try:
            with sqlite3.connect(self.sqlite_cache_path) as conn:
                # Delete expired entries
                deleted_count = conn.execute(
                    "DELETE FROM enrichment_cache WHERE expires_at < datetime('now')"
                ).rowcount
                conn.commit()

                if deleted_count > 0:
                    logger.info(
                        "Cleaned up expired SQLite cache entries", deleted_count=deleted_count
                    )
        except Exception as e:
            logger.warning("Failed to cleanup SQLite cache", error=str(e))

    def get_available_sources(self) -> list[ThreatIntelligenceSource]:
        """Get list of available threat intelligence sources.

        Returns:
            List of available sources

        """
        return list(self.clients.keys())

    def get_source_status(self) -> dict[str, Any]:
        """Get status of all threat intelligence sources.

        Returns:
            Dictionary containing source status information

        """
        status = {}
        for source, client in self.clients.items():
            # Get source configuration
            sources_config = self.config.get("threat_intelligence", {}).get("sources", {})
            source_config = sources_config.get(source.value, {})

            status[source.value] = {
                "enabled": True,
                "client_type": type(client).__name__,
                "rate_limit_tracker": len(self.rate_limit_trackers.get(source, [])),
                "concurrency_limit": self.concurrency_semaphores.get(
                    source, asyncio.Semaphore(5)
                )._value,
                "rate_limit_per_minute": source_config.get("rate_limit_requests_per_minute", 60),
                "timeout_seconds": source_config.get("timeout_seconds", 30),
                "max_backoff_attempts": source_config.get("max_backoff_attempts", 3),
            }
        return status

    def get_cache_statistics(self) -> dict[str, Any]:
        """Get cache statistics for both memory and SQLite caches.

        Returns:
            Dictionary containing cache statistics

        """
        stats = {
            "memory_cache": {
                "enabled": True,
                "size": len(self.cache),
                "ttl_hours": self.cache_ttl.total_seconds() / 3600,
            },
            "sqlite_cache": {
                "enabled": self.sqlite_cache_enabled,
                "path": self.sqlite_cache_path,
                "ttl_hours": self.sqlite_cache_ttl.total_seconds() / 3600,
            },
        }

        # Get SQLite cache statistics if enabled
        if self.sqlite_cache_enabled:
            try:
                with sqlite3.connect(self.sqlite_cache_path) as conn:
                    # Get total entries
                    total_entries = conn.execute(
                        "SELECT COUNT(*) FROM enrichment_cache"
                    ).fetchone()[0]

                    # Get expired entries
                    expired_entries = conn.execute(
                        "SELECT COUNT(*) FROM enrichment_cache WHERE expires_at < datetime('now')"
                    ).fetchone()[0]

                    # Get database size
                    db_size = (
                        os.path.getsize(self.sqlite_cache_path)
                        if os.path.exists(self.sqlite_cache_path)
                        else 0
                    )

                    stats["sqlite_cache"].update(
                        {
                            "total_entries": total_entries,
                            "expired_entries": expired_entries,
                            "valid_entries": total_entries - expired_entries,
                            "database_size_bytes": db_size,
                        }
                    )
            except Exception as e:
                logger.warning("Failed to get SQLite cache statistics", error=str(e))
                stats["sqlite_cache"]["error"] = str(e)

        return stats

    def _initialize_elasticsearch(self) -> None:
        """Initialize Elasticsearch client for enrichment writeback if enabled in config."""
        es_config = self.config.get("threat_intelligence", {}).get("elasticsearch", {})
        if es_config.get("enabled", False):
            try:
                from elasticsearch import AsyncElasticsearch

                self.elasticsearch_client = AsyncElasticsearch(
                    hosts=es_config.get("hosts", ["localhost:9200"]),
                    basic_auth=(
                        es_config.get("username", "elastic"),
                        es_config.get("password", ""),
                    ),
                )
            except ImportError:
                self.elasticsearch_client = None
        else:
            self.elasticsearch_client = None

    async def _correlate_threat_indicators(
        self, source_results: dict[ThreatIntelligenceSource, dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Advanced threat indicator correlation with source weighting and confidence scoring.

        Args:
            source_results: Results from all sources

        Returns:
            List of correlated threat indicators with metadata

        """
        # Source reliability weights
        source_reliability = {
            ThreatIntelligenceSource.DSHIELD: 0.8,
            ThreatIntelligenceSource.VIRUSTOTAL: 0.9,
            ThreatIntelligenceSource.SHODAN: 0.7,
            ThreatIntelligenceSource.ABUSEIPDB: 0.8,
            ThreatIntelligenceSource.ALIENVAULT: 0.8,
            ThreatIntelligenceSource.THREATFOX: 0.7,
        }

        # Collect all indicators with source metadata
        indicator_sources = {}

        for source, source_data in source_results.items():
            if isinstance(source_data, dict):
                reliability = source_reliability.get(source, 0.5)

                # Extract indicators from various fields
                indicators = []
                if "indicators" in source_data:
                    indicators.extend(source_data["indicators"])
                if "attack_types" in source_data:
                    indicators.extend(source_data["attack_types"])
                if "tags" in source_data:
                    indicators.extend(source_data["tags"])

                # Add source metadata to each indicator
                for indicator in indicators:
                    indicator_key = str(indicator).lower()
                    if indicator_key not in indicator_sources:
                        indicator_sources[indicator_key] = {
                            "indicator": indicator,
                            "type": self._classify_indicator(indicator_key),
                            "sources": [],
                            "total_weight": 0.0,
                            "count": 0,
                        }

                    indicator_sources[indicator_key]["sources"].append(
                        {
                            "source": source,
                            "reliability": reliability,
                            "confidence": source_data.get("confidence", 0.5),
                        }
                    )
                    indicator_sources[indicator_key]["total_weight"] += reliability
                    indicator_sources[indicator_key]["count"] += 1

        # Calculate correlation scores and filter by confidence
        correlated_indicators = []
        confidence_threshold = self.correlation_config.get("confidence_threshold", 0.7)

        for indicator_data in indicator_sources.values():
            # Calculate weighted confidence score
            if indicator_data["sources"]:
                weighted_confidence = (
                    sum(
                        source["reliability"] * source["confidence"]
                        for source in indicator_data["sources"]
                    )
                    / indicator_data["total_weight"]
                )

                # Only include indicators that meet confidence threshold
                if weighted_confidence >= confidence_threshold:
                    correlated_indicators.append(
                        {
                            "indicator": indicator_data["indicator"],
                            "type": indicator_data["type"],
                            "count": indicator_data["count"],
                            "sources": [s["source"].value for s in indicator_data["sources"]],
                            "confidence": weighted_confidence,
                            "source_count": len(indicator_data["sources"]),
                        }
                    )

        # Sort by confidence and count
        correlated_indicators.sort(key=lambda x: (x["confidence"], x["count"]), reverse=True)

        return correlated_indicators

    def _aggregate_geographic_data_advanced(self, result: ThreatIntelligenceResult) -> None:
        """Aggregate geographic data with confidence weighting and conflict resolution.

        Args:
            result: The threat intelligence result to update

        """
        geographic_scores: dict[str, float] = {}
        source_reliability = {
            ThreatIntelligenceSource.DSHIELD: 0.8,
            ThreatIntelligenceSource.VIRUSTOTAL: 0.9,
            ThreatIntelligenceSource.SHODAN: 0.7,
        }

        for source, source_data in result.source_results.items():
            if isinstance(source_data, dict):
                reliability = source_reliability.get(source, 0.5)

                # Extract geographic data
                geo_data = {}
                if "geographic_data" in source_data:
                    geo_data.update(source_data["geographic_data"])
                elif "country" in source_data:
                    geo_data["country"] = source_data["country"]
                elif "region" in source_data:
                    geo_data["region"] = source_data["region"]
                elif "city" in source_data:
                    geo_data["city"] = source_data["city"]

                # Score geographic data by reliability
                for field, value in geo_data.items():
                    if value:
                        if field not in geographic_scores:
                            geographic_scores[field] = {}

                        if value not in geographic_scores[field]:
                            geographic_scores[field][value] = {"weight": 0.0, "sources": []}

                        geographic_scores[field][value]["weight"] += reliability
                        geographic_scores[field][value]["sources"].append(source)

        # Select highest weighted values for each field
        result.geographic_data = {}
        for field, values in geographic_scores.items():
            if values:
                # Select the value with highest weight
                best_value = max(values.keys(), key=lambda v: values[v]["weight"])
                result.geographic_data[field] = best_value

    def _aggregate_network_data_advanced(self, result: ThreatIntelligenceResult) -> None:
        """Aggregate network data with confidence weighting and conflict resolution.

        Args:
            result: The threat intelligence result to update

        """
        network_scores: dict[str, float] = {}
        source_reliability = {
            ThreatIntelligenceSource.DSHIELD: 0.8,
            ThreatIntelligenceSource.VIRUSTOTAL: 0.9,
            ThreatIntelligenceSource.SHODAN: 0.7,
        }

        for source, source_data in result.source_results.items():
            if isinstance(source_data, dict):
                reliability = source_reliability.get(source, 0.5)

                # Extract network data
                net_data = {}
                if "network_data" in source_data:
                    net_data.update(source_data["network_data"])
                elif "asn" in source_data:
                    net_data["asn"] = source_data["asn"]
                elif "organization" in source_data:
                    net_data["organization"] = source_data["organization"]
                elif "isp" in source_data:
                    net_data["isp"] = source_data["isp"]

                # Score network data by reliability
                for field, value in net_data.items():
                    if value:
                        if field not in network_scores:
                            network_scores[field] = {}

                        if value not in network_scores[field]:
                            network_scores[field][value] = {"weight": 0.0, "sources": []}

                        network_scores[field][value]["weight"] += reliability
                        network_scores[field][value]["sources"].append(source)

        # Select highest weighted values for each field
        result.network_data = {}
        for field, values in network_scores.items():
            if values:
                # Select the value with highest weight
                best_value = max(values.keys(), key=lambda v: values[v]["weight"])
                result.network_data[field] = best_value

    def _determine_timestamps_advanced(self, result: ThreatIntelligenceResult) -> None:
        """Determine timestamps with temporal correlation and source weighting.

        Args:
            result: The threat intelligence result to update

        """
        first_seen_times = []
        last_seen_times = []
        source_reliability = {
            ThreatIntelligenceSource.DSHIELD: 0.8,
            ThreatIntelligenceSource.VIRUSTOTAL: 0.9,
            ThreatIntelligenceSource.SHODAN: 0.7,
        }

        for source, source_data in result.source_results.items():
            if isinstance(source_data, dict):
                reliability = source_reliability.get(source, 0.5)

                # Extract timestamps with reliability weighting
                if source_data.get("first_seen"):
                    try:
                        if isinstance(source_data["first_seen"], str):
                            first_seen = datetime.fromisoformat(
                                source_data["first_seen"].replace("Z", "+00:00")
                            )
                        else:
                            first_seen = source_data["first_seen"]
                        first_seen_times.append((first_seen, reliability))
                    except (ValueError, TypeError):
                        pass

                if source_data.get("last_seen"):
                    try:
                        if isinstance(source_data["last_seen"], str):
                            last_seen = datetime.fromisoformat(
                                source_data["last_seen"].replace("Z", "+00:00")
                            )
                        else:
                            last_seen = source_data["last_seen"]
                        last_seen_times.append((last_seen, reliability))
                    except (ValueError, TypeError):
                        pass

        # Calculate weighted timestamps
        if first_seen_times:
            # Use earliest time with highest reliability as tiebreaker
            result.first_seen = min(first_seen_times, key=lambda x: (x[0], -x[1]))[0]

        if last_seen_times:
            # Use latest time with highest reliability as tiebreaker
            result.last_seen = max(last_seen_times, key=lambda x: (x[0], x[1]))[0]

    def _calculate_correlation_metrics(self, result: ThreatIntelligenceResult) -> None:
        """Calculate correlation metrics and quality indicators.

        Args:
            result: The threat intelligence result to update

        """
        if not result.source_results:
            return

        # Calculate source agreement
        source_count = len(result.source_results)
        threat_scores = []

        for source_data in result.source_results.values():
            if isinstance(source_data, dict):
                if "threat_score" in source_data and source_data["threat_score"] is not None:
                    threat_scores.append(float(source_data["threat_score"]))
                elif (
                    "reputation_score" in source_data
                    and source_data["reputation_score"] is not None
                ):
                    rep_score = float(source_data["reputation_score"])
                    threat_scores.append(100 - rep_score)

        # Calculate correlation metrics
        correlation_metrics = {
            "source_count": source_count,
            "indicator_count": len(result.threat_indicators),
            "data_completeness": len(result.source_results) / max(1, len(self.clients)),
            "confidence_variance": 0.0,
            "threat_score_variance": 0.0,
        }

        # Calculate variance in threat scores
        if len(threat_scores) > 1:
            mean_score = sum(threat_scores) / len(threat_scores)
            variance = sum((score - mean_score) ** 2 for score in threat_scores) / len(
                threat_scores
            )
            correlation_metrics["threat_score_variance"] = variance

        # Store correlation metrics in result
        result.correlation_metrics = correlation_metrics

    async def diagnose_data_availability(
        self,
        check_indices: bool = True,
        check_mappings: bool = True,
        check_recent_data: bool = True,
        sample_query: bool = True,
    ) -> dict[str, Any]:
        """Diagnose data availability issues and provide troubleshooting information.

        This method performs comprehensive diagnostics to identify why queries
        might return empty results, including index availability, field mappings,
        data freshness, and query pattern testing.

        Args:
            check_indices: Whether to check available indices and patterns
            check_mappings: Whether to check index mappings and field availability
            check_recent_data: Whether to check data availability across time ranges
            sample_query: Whether to test sample queries with different patterns

        Returns:
            Dictionary containing comprehensive diagnostic information

        """
        diagnosis = {
            "timestamp": datetime.now(UTC).isoformat(),
            "summary": {},
            "details": {},
            "recommendations": [],
        }

        try:
            # Get Elasticsearch client from config
            from .elasticsearch_client import ElasticsearchClient

            es_client = ElasticsearchClient()
            await es_client.connect()

            # Initialize available_indices variable
            available_indices = []

            # 1. Check available indices
            if check_indices:
                try:
                    available_indices = await es_client.get_available_indices()
                    diagnosis["details"]["available_indices"] = {
                        "count": len(available_indices),
                        "indices": available_indices,
                        "configured_patterns": es_client.dshield_indices,
                        "fallback_patterns": es_client.fallback_indices,
                    }

                    if not available_indices:
                        diagnosis["summary"]["indices_issue"] = "No DShield indices found"
                        diagnosis["recommendations"].append(
                            "Check index_patterns configuration in mcp_config.yaml",
                        )
                        diagnosis["recommendations"].append(
                            "Verify that Elasticsearch indices exist and are accessible",
                        )
                    else:
                        diagnosis["summary"]["indices_status"] = (
                            f"Found {len(available_indices)} indices"
                        )

                except Exception as e:
                    diagnosis["details"]["indices_error"] = str(e)
                    diagnosis["summary"]["indices_issue"] = f"Failed to check indices: {e}"

            # 2. Check index mappings
            if check_mappings and available_indices:
                try:
                    sample_index = available_indices[0] if available_indices else None
                    if sample_index:
                        mapping = await es_client.client.indices.get_mapping(index=sample_index)
                        diagnosis["details"]["sample_mapping"] = {
                            "index": sample_index,
                            "field_count": len(mapping[sample_index]["mappings"]["properties"]),
                            "key_fields": list(
                                mapping[sample_index]["mappings"]["properties"].keys()
                            )[:10],
                        }

                        # Check for common timestamp fields
                        properties = mapping[sample_index]["mappings"]["properties"]
                        timestamp_fields = [
                            field
                            for field in properties.keys()
                            if "time" in field.lower() or "date" in field.lower()
                        ]
                        diagnosis["details"]["timestamp_fields"] = timestamp_fields

                except Exception as e:
                    diagnosis["details"]["mapping_error"] = str(e)
                    diagnosis["summary"]["mapping_issue"] = f"Failed to check mappings: {e}"

            # 3. Check recent data availability
            if check_recent_data:
                try:
                    data_availability = {}
                    for hours in [1, 6, 24, 168]:
                        try:
                            events, count, _ = await es_client.query_dshield_events(
                                time_range_hours=hours,
                                page_size=1,
                            )
                            data_availability[f"{hours}h"] = {
                                "events_found": len(events),
                                "total_count": count,
                            }
                        except Exception as e:
                            data_availability[f"{hours}h"] = {
                                "error": str(e),
                            }

                    diagnosis["details"]["data_availability"] = data_availability

                    # Analyze data availability
                    recent_data = data_availability.get("24h", {})
                    if isinstance(recent_data, dict) and recent_data.get("total_count", 0) == 0:
                        diagnosis["summary"]["data_issue"] = "No recent data found in last 24 hours"
                        diagnosis["recommendations"].append(
                            "Check if data is being ingested into Elasticsearch",
                        )
                        diagnosis["recommendations"].append(
                            "Verify timestamp field mappings and data format",
                        )

                except Exception as e:
                    diagnosis["details"]["data_check_error"] = str(e)
                    diagnosis["summary"]["data_check_issue"] = (
                        f"Failed to check data availability: {e}"
                    )

            # 4. Sample query testing
            if sample_query:
                try:
                    test_patterns = [
                        ["dshield-*"],
                        ["cowrie-*"],
                        ["zeek-*"],
                        ["*"],
                        None,  # Use auto-detection
                    ]

                    pattern_tests = {}
                    for pattern in test_patterns:
                        try:
                            events, count, _ = await es_client.query_dshield_events(
                                time_range_hours=24,
                                indices=pattern,
                                page_size=1,
                            )
                            pattern_tests[f"pattern_{pattern or 'auto'}"] = {
                                "events_found": len(events),
                                "total_count": count,
                                "success": True,
                            }
                        except Exception as e:
                            pattern_tests[f"pattern_{pattern or 'auto'}"] = {
                                "error": str(e),
                                "success": False,
                            }

                    diagnosis["details"]["pattern_tests"] = pattern_tests

                    # Find working patterns
                    working_patterns = [
                        name
                        for name, result in pattern_tests.items()
                        if result.get("success") and result.get("total_count", 0) > 0
                    ]

                    if working_patterns:
                        diagnosis["summary"]["working_patterns"] = (
                            f"Found {len(working_patterns)} working patterns"
                        )
                        diagnosis["recommendations"].append(
                            f"Use working patterns: {', '.join(working_patterns)}",
                        )
                    else:
                        diagnosis["summary"]["pattern_issue"] = "No working query patterns found"
                        diagnosis["recommendations"].append(
                            "Check Elasticsearch connection and index permissions",
                        )

                except Exception as e:
                    diagnosis["details"]["pattern_test_error"] = str(e)
                    diagnosis["summary"]["pattern_test_issue"] = f"Failed to test patterns: {e}"

            # Generate overall summary
            issues = []
            if "indices_issue" in diagnosis["summary"]:
                issues.append("indices")
            if "mapping_issue" in diagnosis["summary"]:
                issues.append("mappings")
            if "data_issue" in diagnosis["summary"]:
                issues.append("data")
            if "pattern_issue" in diagnosis["summary"]:
                issues.append("queries")

            if issues:
                diagnosis["summary"]["overall_status"] = f"issues_detected: {', '.join(issues)}"
                diagnosis["summary"]["severity"] = "high" if len(issues) > 2 else "medium"
            else:
                diagnosis["summary"]["overall_status"] = "healthy"
                diagnosis["summary"]["severity"] = "low"

            # Add general recommendations
            if not diagnosis["recommendations"]:
                diagnosis["recommendations"].append("Data availability appears healthy")
                diagnosis["recommendations"].append(
                    "If issues persist, check application logs for errors"
                )

            await es_client.close()

        except Exception as e:
            diagnosis["summary"]["overall_status"] = "diagnosis_failed"
            diagnosis["summary"]["severity"] = "critical"
            diagnosis["details"]["diagnosis_error"] = str(e)
            diagnosis["recommendations"].append(f"Diagnosis failed: {e}")
            diagnosis["recommendations"].append("Check Elasticsearch connection and configuration")

        return diagnosis

    async def has_cached_data(self) -> bool:
        """Check if there is any cached threat intelligence data available.

        Returns:
            bool: True if cached data exists, False otherwise

        """
        try:
            # Check in-memory cache
            if self.cache and len(self.cache) > 0:
                # Check if any cache entries are not expired
                current_time = datetime.now()
                for _cache_key, cache_entry in self.cache.items():
                    if isinstance(cache_entry, dict) and "timestamp" in cache_entry:
                        cache_time = cache_entry["timestamp"]
                        if isinstance(cache_time, datetime):
                            if current_time - cache_time < self.cache_ttl:
                                return True
                        elif isinstance(cache_time, int | float):
                            # Unix timestamp
                            if (
                                current_time.timestamp() - cache_time
                                < self.cache_ttl.total_seconds()
                            ):
                                return True

            # Check SQLite cache if enabled
            if self.sqlite_cache_enabled and hasattr(self, "_sqlite_cache"):
                try:
                    # Simple check for any cached entries
                    cursor = self._sqlite_cache.cursor()
                    cursor.execute("SELECT COUNT(*) FROM threat_intel_cache")
                    count = cursor.fetchone()[0]
                    return count > 0
                except Exception:
                    pass

            return False

        except Exception as e:
            logger.error("Failed to check cached data availability", error=str(e))
            return False
