#!/usr/bin/env python3
"""Tests for Phase 4 DShield API Circuit Breaker Integration.

This module tests the circuit breaker integration with the DShield client,
ensuring that the circuit breaker pattern works correctly for external service
error handling.
"""

from datetime import UTC
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.dshield_client import DShieldClient
from src.mcp_error_handler import (
    CircuitBreaker,
    CircuitBreakerState,
    ErrorHandlingConfig,
    MCPErrorHandler,
)


class TestDShieldCircuitBreakerIntegration:
    """Test DShield client circuit breaker integration."""

    @pytest.fixture
    def error_handler(self) -> MCPErrorHandler:
        """Create a test error handler."""
        config = ErrorHandlingConfig()
        return MCPErrorHandler(config)

    @pytest.fixture
    def dshield_client(self, error_handler: MCPErrorHandler) -> DShieldClient:
        """Create a test DShield client with error handler."""
        with (
            patch('src.dshield_client.get_config') as mock_get_config,
            patch('src.dshield_client.get_user_config') as mock_get_user_config,
        ):
            # Mock config
            mock_get_config.return_value = {
                "secrets": {
                    "dshield_api_key": "test_api_key",
                    "dshield_api_url": "https://test-dshield.org/api",
                    "rate_limit_requests_per_minute": 60,
                    "cache_ttl_seconds": 300,
                    "max_ip_enrichment_batch_size": 100,
                }
            }

            # Mock user config
            mock_user_config_instance = Mock()
            mock_user_config_instance.get_setting.side_effect = lambda section, key: {
                ("performance", "enable_caching"): True,
                ("performance", "max_cache_size"): 1000,
                ("performance", "request_timeout_seconds"): 30,
                ("logging", "enable_performance_logging"): False,
            }.get((section, key), None)
            mock_get_user_config.return_value = mock_user_config_instance

            client = DShieldClient(error_handler=error_handler)
            return client

    def test_circuit_breaker_initialization(self, dshield_client: DShieldClient) -> None:
        """Test that circuit breaker is properly initialized."""
        assert dshield_client.circuit_breaker is not None
        assert isinstance(dshield_client.circuit_breaker, CircuitBreaker)
        assert dshield_client.circuit_breaker.service_name == "dshield_api"

    def test_circuit_breaker_initialization_without_error_handler(self) -> None:
        """Test that circuit breaker is not initialized without error handler."""
        with (
            patch('src.dshield_client.get_config') as mock_get_config,
            patch('src.dshield_client.get_user_config') as mock_get_user_config,
        ):
            # Mock config
            mock_get_config.return_value = {
                "secrets": {
                    "dshield_api_key": "test_api_key",
                    "dshield_api_url": "https://test-dshield.org/api",
                    "rate_limit_requests_per_minute": 60,
                    "cache_ttl_seconds": 300,
                    "max_ip_enrichment_batch_size": 100,
                }
            }

            # Mock user config
            mock_user_config_instance = Mock()
            mock_user_config_instance.get_setting.side_effect = lambda section, key: {
                ("performance", "enable_caching"): True,
                ("performance", "max_cache_size"): 1000,
                ("performance", "request_timeout_seconds"): 30,
                ("logging", "enable_performance_logging"): False,
            }.get((section, key), None)
            mock_get_user_config.return_value = mock_user_config_instance

            client = DShieldClient()
            assert client.circuit_breaker is None

    def test_circuit_breaker_check_allows_execution_when_closed(
        self, dshield_client: DShieldClient
    ) -> None:
        """Test that circuit breaker allows execution when closed."""
        result = dshield_client._check_circuit_breaker("test_operation")
        assert result is True

    def test_circuit_breaker_check_blocks_execution_when_open(
        self, dshield_client: DShieldClient
    ) -> None:
        """Test that circuit breaker blocks execution when open."""
        # Force circuit breaker to open state
        dshield_client.circuit_breaker.state = CircuitBreakerState.OPEN
        dshield_client.circuit_breaker.failure_count = 5

        result = dshield_client._check_circuit_breaker("test_operation")
        assert result is False

    def test_circuit_breaker_success_recording(self, dshield_client: DShieldClient) -> None:
        """Test that successful operations are recorded with circuit breaker."""
        # Record success
        dshield_client._record_circuit_breaker_success()

        # Verify success was recorded
        assert dshield_client.circuit_breaker.failure_count == 0

    def test_circuit_breaker_failure_recording(self, dshield_client: DShieldClient) -> None:
        """Test that failed operations are recorded with circuit breaker."""
        # Record failure
        test_exception = Exception("Test failure")
        dshield_client._record_circuit_breaker_failure(test_exception)

        # Verify failure was recorded
        assert dshield_client.circuit_breaker.failure_count == 1

    def test_circuit_breaker_status_retrieval(self, dshield_client: DShieldClient) -> None:
        """Test that circuit breaker status can be retrieved."""
        status = dshield_client.get_circuit_breaker_status()

        assert status is not None
        assert "service_name" in status
        assert "state" in status
        assert "failure_count" in status
        assert "success_count" in status
        assert status["service_name"] == "dshield_api"

    def test_circuit_breaker_status_when_disabled(self) -> None:
        """Test that circuit breaker status returns None when disabled."""
        with (
            patch('src.dshield_client.get_config') as mock_get_config,
            patch('src.dshield_client.get_user_config') as mock_get_user_config,
        ):
            # Mock config
            mock_get_config.return_value = {
                "secrets": {
                    "dshield_api_key": "test_api_key",
                    "dshield_api_url": "https://test-dshield.org/api",
                    "rate_limit_requests_per_minute": 60,
                    "cache_ttl_seconds": 300,
                    "max_ip_enrichment_batch_size": 100,
                }
            }

            # Mock user config
            mock_user_config_instance = Mock()
            mock_user_config_instance.get_setting.side_effect = lambda section, key: {
                ("performance", "enable_caching"): True,
                ("performance", "max_cache_size"): 1000,
                ("performance", "request_timeout_seconds"): 30,
                ("logging", "enable_performance_logging"): False,
            }.get((section, key), None)
            mock_get_user_config.return_value = mock_user_config_instance

            client = DShieldClient()
            status = client.get_circuit_breaker_status()
            assert status is None


class TestDShieldCircuitBreakerInOperations:
    """Test circuit breaker integration in actual DShield API operations."""

    @pytest.fixture
    def error_handler(self) -> MCPErrorHandler:
        """Create a test error handler."""
        config = ErrorHandlingConfig()
        return MCPErrorHandler(config)

    @pytest.fixture
    def dshield_client(self, error_handler: MCPErrorHandler) -> DShieldClient:
        """Create a test DShield client with error handler."""
        with (
            patch('src.dshield_client.get_config') as mock_get_config,
            patch('src.dshield_client.get_user_config') as mock_get_user_config,
        ):
            # Mock config
            mock_get_config.return_value = {
                "secrets": {
                    "dshield_api_key": "test_api_key",
                    "dshield_api_url": "https://test-dshield.org/api",
                    "rate_limit_requests_per_minute": 60,
                    "cache_ttl_seconds": 300,
                    "max_ip_enrichment_batch_size": 100,
                }
            }

            # Mock user config
            mock_user_config_instance = Mock()
            mock_user_config_instance.get_setting.side_effect = lambda section, key: {
                ("performance", "enable_caching"): True,
                ("performance", "max_cache_size"): 1000,
                ("performance", "request_timeout_seconds"): 30,
                ("logging", "enable_performance_logging"): False,
            }.get((section, key), None)
            mock_get_user_config.return_value = mock_user_config_instance

            client = DShieldClient(error_handler=error_handler)
            return client

    @pytest.mark.asyncio
    async def test_get_ip_reputation_with_circuit_breaker_closed(
        self, dshield_client: DShieldClient
    ) -> None:
        """Test get IP reputation when circuit breaker is closed."""
        # Mock the entire HTTP request to avoid complex async context manager mocking
        with (
            patch.object(dshield_client, '_check_rate_limit'),
            patch.object(dshield_client, 'connect'),
            patch.object(dshield_client, 'session') as mock_session,
        ):
            # Mock successful response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {"reputation": 75, "country": "US"}

            # Mock the async context manager
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_response
            mock_context.__aexit__.return_value = None
            mock_session.get.return_value = mock_context

            result = await dshield_client.get_ip_reputation("8.8.8.8")

        # Verify success was recorded
        assert dshield_client.circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_get_ip_reputation_with_circuit_breaker_open(
        self, dshield_client: DShieldClient
    ) -> None:
        """Test get IP reputation when circuit breaker is open."""
        # Force circuit breaker to open state
        dshield_client.circuit_breaker.state = CircuitBreakerState.OPEN
        dshield_client.circuit_breaker.failure_count = 5

        # Mock rate limiting
        with patch.object(dshield_client, '_check_rate_limit'):
            result = await dshield_client.get_ip_reputation("8.8.8.8")

        # Verify circuit breaker error was returned
        assert "error" in result
        assert "circuit breaker is open" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_get_ip_details_with_circuit_breaker_closed(
        self, dshield_client: DShieldClient
    ) -> None:
        """Test get IP details when circuit breaker is closed."""
        # Mock the entire HTTP request to avoid complex async context manager mocking
        with (
            patch.object(dshield_client, '_check_rate_limit'),
            patch.object(dshield_client, 'connect'),
            patch.object(dshield_client, 'session') as mock_session,
        ):
            # Mock successful response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {"details": "test_details"}

            # Mock the async context manager
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_response
            mock_context.__aexit__.return_value = None
            mock_session.get.return_value = mock_context

            result = await dshield_client.get_ip_details("8.8.8.8")

        # Verify success was recorded
        assert dshield_client.circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_get_ip_details_with_circuit_breaker_open(
        self, dshield_client: DShieldClient
    ) -> None:
        """Test get IP details when circuit breaker is open."""
        # Force circuit breaker to open state
        dshield_client.circuit_breaker.state = CircuitBreakerState.OPEN
        dshield_client.circuit_breaker.failure_count = 5

        # Mock rate limiting
        with patch.object(dshield_client, '_check_rate_limit'):
            result = await dshield_client.get_ip_details("8.8.8.8")

        # Verify circuit breaker error was returned
        assert "error" in result
        assert "circuit breaker is open" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_get_top_attackers_with_circuit_breaker_closed(
        self, dshield_client: DShieldClient
    ) -> None:
        """Test get top attackers when circuit breaker is closed."""
        # Mock the entire HTTP request to avoid complex async context manager mocking
        with (
            patch.object(dshield_client, '_check_rate_limit'),
            patch.object(dshield_client, 'connect'),
            patch.object(dshield_client, 'session') as mock_session,
        ):
            # Mock successful response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = [{"ip": "1.1.1.1", "count": 100}]

            # Mock the async context manager
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_response
            mock_context.__aexit__.return_value = None
            mock_session.get.return_value = mock_context

            result = await dshield_client.get_top_attackers(24)

        # Verify success was recorded
        assert dshield_client.circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_get_top_attackers_with_circuit_breaker_open(
        self, dshield_client: DShieldClient
    ) -> None:
        """Test get top attackers when circuit breaker is open."""
        # Force circuit breaker to open state
        dshield_client.circuit_breaker.state = CircuitBreakerState.OPEN
        dshield_client.circuit_breaker.failure_count = 5

        # Mock rate limiting
        with patch.object(dshield_client, '_check_rate_limit'):
            result = await dshield_client.get_top_attackers(24)

        # Verify circuit breaker error was returned
        assert "error" in result
        assert "circuit breaker is open" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_get_attack_summary_with_circuit_breaker_closed(
        self, dshield_client: DShieldClient
    ) -> None:
        """Test get attack summary when circuit breaker is closed."""
        # Mock the entire HTTP request to avoid complex async context manager mocking
        with (
            patch.object(dshield_client, '_check_rate_limit'),
            patch.object(dshield_client, 'connect'),
            patch.object(dshield_client, 'session') as mock_session,
        ):
            # Mock successful response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {"summary": "test_summary"}

            # Mock the async context manager
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_response
            mock_context.__aexit__.return_value = None
            mock_session.get.return_value = mock_context

            result = await dshield_client.get_attack_summary(24)

        # Verify success was recorded
        assert dshield_client.circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_get_attack_summary_with_circuit_breaker_open(
        self, dshield_client: DShieldClient
    ) -> None:
        """Test get attack summary when circuit breaker is open."""
        # Force circuit breaker to open state
        dshield_client.circuit_breaker.state = CircuitBreakerState.OPEN
        dshield_client.circuit_breaker.failure_count = 5

        # Mock rate limiting
        with patch.object(dshield_client, '_check_rate_limit'):
            result = await dshield_client.get_attack_summary(24)

        # Verify circuit breaker error was returned
        assert "error" in result
        assert "circuit breaker is open" in result["error"]["message"]


class TestDShieldCircuitBreakerRecovery:
    """Test circuit breaker recovery mechanisms."""

    @pytest.fixture
    def error_handler(self) -> MCPErrorHandler:
        """Create a test error handler."""
        config = ErrorHandlingConfig()
        return MCPErrorHandler(config)

    @pytest.fixture
    def dshield_client(self, error_handler: MCPErrorHandler) -> DShieldClient:
        """Create a test DShield client with error handler."""
        with (
            patch('src.dshield_client.get_config') as mock_get_config,
            patch('src.dshield_client.get_user_config') as mock_get_user_config,
        ):
            # Mock config
            mock_get_config.return_value = {
                "secrets": {
                    "dshield_api_key": "test_api_key",
                    "dshield_api_url": "https://test-dshield.org/api",
                    "rate_limit_requests_per_minute": 60,
                    "cache_ttl_seconds": 300,
                    "max_ip_enrichment_batch_size": 100,
                }
            }

            # Mock user config
            mock_user_config_instance = Mock()
            mock_user_config_instance.get_setting.side_effect = lambda section, key: {
                ("performance", "enable_caching"): True,
                ("performance", "max_cache_size"): 1000,
                ("performance", "request_timeout_seconds"): 30,
                ("logging", "enable_performance_logging"): False,
            }.get((section, key), None)
            mock_get_user_config.return_value = mock_user_config_instance

            client = DShieldClient(error_handler=error_handler)
            return client

    def test_circuit_breaker_recovery_timeout(self, dshield_client: DShieldClient) -> None:
        """Test that circuit breaker recovers after timeout."""
        # Force circuit breaker to open state
        dshield_client.circuit_breaker.state = CircuitBreakerState.OPEN
        dshield_client.circuit_breaker.failure_count = 5

        # Simulate time passing (recovery timeout)
        from datetime import datetime, timedelta

        dshield_client.circuit_breaker.last_failure_time = datetime.now(UTC) - timedelta(seconds=70)

        # Check if circuit breaker allows execution (should set to half-open)
        result = dshield_client._check_circuit_breaker("test_operation")
        assert result is True
        assert dshield_client.circuit_breaker.state == CircuitBreakerState.HALF_OPEN

    def test_circuit_breaker_success_recovery(self, dshield_client: DShieldClient) -> None:
        """Test that circuit breaker recovers after successful operations."""
        # Set circuit breaker to half-open state
        dshield_client.circuit_breaker.state = CircuitBreakerState.HALF_OPEN
        dshield_client.circuit_breaker.success_count = 0

        # Record first success (should stay in half-open)
        dshield_client._record_circuit_breaker_success()
        assert dshield_client.circuit_breaker.state == CircuitBreakerState.HALF_OPEN
        assert dshield_client.circuit_breaker.success_count == 1

        # Record second success (should close circuit)
        dshield_client._record_circuit_breaker_success()
        assert dshield_client.circuit_breaker.state == CircuitBreakerState.CLOSED
        assert dshield_client.circuit_breaker.success_count == 0
        assert dshield_client.circuit_breaker.failure_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
