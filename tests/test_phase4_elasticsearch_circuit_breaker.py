#!/usr/bin/env python3
"""Tests for Phase 4 Elasticsearch Circuit Breaker Integration.

This module tests the circuit breaker integration with the Elasticsearch client,
ensuring that the circuit breaker pattern works correctly for external service
error handling.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.elasticsearch_client import ElasticsearchClient
from src.mcp_error_handler import MCPErrorHandler, ErrorHandlingConfig, CircuitBreaker, CircuitBreakerState


class TestElasticsearchCircuitBreakerIntegration:
    """Test Elasticsearch client circuit breaker integration."""
    
    @pytest.fixture
    def error_handler(self) -> MCPErrorHandler:
        """Create a test error handler."""
        config = ErrorHandlingConfig()
        return MCPErrorHandler(config)
    
    @pytest.fixture
    def elasticsearch_client(self, error_handler: MCPErrorHandler) -> ElasticsearchClient:
        """Create a test Elasticsearch client with error handler."""
        with patch('src.elasticsearch_client.get_config') as mock_get_config, \
             patch('src.elasticsearch_client.get_user_config') as mock_get_user_config:
            
            # Mock config
            mock_get_config.return_value = {
                "elasticsearch": {
                    "url": "https://test-elasticsearch:9200",
                    "username": "test_user",
                    "password": "test_pass",
                    "timeout": 30,
                    "max_results": 1000,
                    "index_patterns": {
                        "cowrie": ["cowrie-*"],
                        "zeek": ["zeek-*"],
                        "dshield": ["dshield-*"],
                        "fallback": ["fallback-*"]
                    }
                }
            }
            
            # Mock user config
            mock_user_config_instance = Mock()
            mock_user_config_instance.get_setting.side_effect = lambda section, key: {
                ("query", "default_page_size"): 100,
                ("query", "max_page_size"): 1000,
                ("query", "default_timeout_seconds"): 30,
                ("query", "max_timeout_seconds"): 300,
                ("query", "enable_smart_optimization"): True,
                ("query", "fallback_strategy"): "aggregate",
                ("query", "max_query_complexity"): 10,
                ("logging", "enable_performance_logging"): False
            }.get((section, key), None)
            mock_get_user_config.return_value = mock_user_config_instance
            
            return ElasticsearchClient(error_handler=error_handler)
    
    def test_circuit_breaker_initialization(self, elasticsearch_client: ElasticsearchClient) -> None:
        """Test that circuit breaker is properly initialized."""
        assert elasticsearch_client.circuit_breaker is not None
        assert isinstance(elasticsearch_client.circuit_breaker, CircuitBreaker)
        assert elasticsearch_client.circuit_breaker.service_name == "elasticsearch"
    
    def test_circuit_breaker_initialization_without_error_handler(self) -> None:
        """Test that circuit breaker is not initialized without error handler."""
        with patch('src.elasticsearch_client.get_config') as mock_get_config, \
             patch('src.elasticsearch_client.get_user_config') as mock_get_user_config:
            
            # Mock config
            mock_get_config.return_value = {
                "elasticsearch": {
                    "url": "https://test-elasticsearch:9200",
                    "username": "test_user",
                    "password": "test_pass",
                    "timeout": 30,
                    "max_results": 1000,
                    "index_patterns": {
                        "cowrie": ["cowrie-*"],
                        "zeek": ["zeek-*"],
                        "dshield": ["dshield-*"],
                        "fallback": ["fallback-*"]
                    }
                }
            }
            
            # Mock user config
            mock_user_config_instance = Mock()
            mock_user_config_instance.get_setting.side_effect = lambda section, key: {
                ("query", "default_page_size"): 100,
                ("query", "max_page_size"): 1000,
                ("query", "default_timeout_seconds"): 30,
                ("query", "max_timeout_seconds"): 300,
                ("query", "enable_smart_optimization"): True,
                ("query", "fallback_strategy"): "aggregate",
                ("query", "max_query_complexity"): 10,
                ("logging", "enable_performance_logging"): False
            }.get((section, key), None)
            mock_get_user_config.return_value = mock_user_config_instance
            
            client = ElasticsearchClient()
            assert client.circuit_breaker is None
    
    def test_circuit_breaker_check_allows_execution_when_closed(self, elasticsearch_client: ElasticsearchClient) -> None:
        """Test that circuit breaker allows execution when closed."""
        result = elasticsearch_client._check_circuit_breaker("test_operation")
        assert result is True
    
    def test_circuit_breaker_check_blocks_execution_when_open(self, elasticsearch_client: ElasticsearchClient) -> None:
        """Test that circuit breaker blocks execution when open."""
        # Force circuit breaker to open state
        elasticsearch_client.circuit_breaker.state = CircuitBreakerState.OPEN
        elasticsearch_client.circuit_breaker.failure_count = 5
        
        result = elasticsearch_client._check_circuit_breaker("test_operation")
        assert isinstance(result, dict)
        assert "error" in result
        assert "circuit breaker is open" in result["error"]["message"]
    
    def test_circuit_breaker_success_recording(self, elasticsearch_client: ElasticsearchClient) -> None:
        """Test that successful operations are recorded with circuit breaker."""
        # Mock client connection
        elasticsearch_client.client = AsyncMock()
        
        # Record success
        elasticsearch_client._record_circuit_breaker_success()
        
        # Verify success was recorded
        assert elasticsearch_client.circuit_breaker.failure_count == 0
    
    def test_circuit_breaker_failure_recording(self, elasticsearch_client: ElasticsearchClient) -> None:
        """Test that failed operations are recorded with circuit breaker."""
        # Mock client connection
        elasticsearch_client.client = AsyncMock()
        
        # Record failure
        test_exception = Exception("Test failure")
        elasticsearch_client._record_circuit_breaker_failure(test_exception)
        
        # Verify failure was recorded
        assert elasticsearch_client.circuit_breaker.failure_count == 1
    
    def test_circuit_breaker_status_retrieval(self, elasticsearch_client: ElasticsearchClient) -> None:
        """Test that circuit breaker status can be retrieved."""
        status = elasticsearch_client.get_circuit_breaker_status()
        
        assert status is not None
        assert "service_name" in status
        assert "state" in status
        assert "failure_count" in status
        assert "success_count" in status
        assert status["service_name"] == "elasticsearch"
    
    def test_circuit_breaker_status_when_disabled(self) -> None:
        """Test that circuit breaker status returns None when disabled."""
        with patch('src.elasticsearch_client.get_config') as mock_get_config, \
             patch('src.elasticsearch_client.get_user_config') as mock_get_user_config:
            
            # Mock config
            mock_get_config.return_value = {
                "elasticsearch": {
                    "url": "https://test-elasticsearch:9200",
                    "username": "test_user",
                    "password": "test_pass",
                    "timeout": 30,
                    "max_results": 1000,
                    "index_patterns": {
                        "cowrie": ["cowrie-*"],
                        "zeek": ["zeek-*"],
                        "dshield": ["dshield-*"],
                        "fallback": ["fallback-*"]
                    }
                }
            }
            
            # Mock user config
            mock_user_config_instance = Mock()
            mock_user_config_instance.get_setting.side_effect = lambda section, key: {
                ("query", "default_page_size"): 100,
                ("query", "max_page_size"): 1000,
                ("query", "default_timeout_seconds"): 30,
                ("query", "max_timeout_seconds"): 300,
                ("query", "enable_smart_optimization"): True,
                ("query", "fallback_strategy"): "aggregate",
                ("query", "max_query_complexity"): 10,
                ("logging", "enable_performance_logging"): False
            }.get((section, key), None)
            mock_get_user_config.return_value = mock_user_config_instance
            
            client = ElasticsearchClient()
            status = client.get_circuit_breaker_status()
            assert status is None


class TestElasticsearchCircuitBreakerInOperations:
    """Test circuit breaker integration in actual Elasticsearch operations."""
    
    @pytest.fixture
    def error_handler(self) -> MCPErrorHandler:
        """Create a test error handler."""
        config = ErrorHandlingConfig()
        return MCPErrorHandler(config)
    
    @pytest.fixture
    def elasticsearch_client(self, error_handler: MCPErrorHandler) -> ElasticsearchClient:
        """Create a test Elasticsearch client with error handler."""
        with patch('src.elasticsearch_client.get_config') as mock_get_config, \
             patch('src.elasticsearch_client.get_user_config') as mock_get_user_config:
            
            # Mock config
            mock_get_config.return_value = {
                "elasticsearch": {
                    "url": "https://test-elasticsearch:9200",
                    "username": "test_user",
                    "password": "test_pass",
                    "timeout": 30,
                    "max_results": 1000,
                    "index_patterns": {
                        "cowrie": ["cowrie-*"],
                        "zeek": ["zeek-*"],
                        "dshield": ["dshield-*"],
                        "fallback": ["fallback-*"]
                    }
                }
            }
            
            # Mock user config
            mock_user_config_instance = Mock()
            mock_user_config_instance.get_setting.side_effect = lambda section, key: {
                ("query", "default_page_size"): 100,
                ("query", "max_page_size"): 1000,
                ("query", "default_timeout_seconds"): 30,
                ("query", "max_timeout_seconds"): 300,
                ("query", "enable_smart_optimization"): True,
                ("query", "fallback_strategy"): "aggregate",
                ("query", "max_query_complexity"): 10,
                ("logging", "enable_performance_logging"): False
            }.get((section, key), None)
            mock_get_user_config.return_value = mock_user_config_instance
            
            client = ElasticsearchClient(error_handler=error_handler)
            return client
    
    @pytest.mark.asyncio
    async def test_query_events_with_circuit_breaker_closed(self, elasticsearch_client: ElasticsearchClient) -> None:
        """Test query events when circuit breaker is closed."""
        # Mock client connection
        elasticsearch_client.client = AsyncMock()
        
        # Mock successful search response
        mock_response = {
            "hits": {
                "total": {"value": 10},
                "hits": [
                    {
                        "_source": {
                            "@timestamp": "2025-08-29T10:00:00Z",
                            "source": {"ip": "192.168.1.1"},
                            "destination": {"ip": "192.168.1.2"}
                        },
                        "sort": ["2025-08-29T10:00:00Z"]
                    }
                ]
            }
        }
        elasticsearch_client.client.search.return_value = mock_response
        
        # Mock available indices
        with patch.object(elasticsearch_client, 'get_available_indices') as mock_get_indices:
            mock_get_indices.return_value = ["dshield-*"]
            
            # Execute query
            events, total_count, pagination_info = await elasticsearch_client.query_dshield_events(
                time_range_hours=24,
                page=1,
                page_size=100
            )
            
            # Verify success was recorded
            assert elasticsearch_client.circuit_breaker.failure_count == 0
            assert len(events) == 1
            assert total_count == 10
    
    @pytest.mark.asyncio
    async def test_query_events_with_circuit_breaker_open(self, elasticsearch_client: ElasticsearchClient) -> None:
        """Test query events when circuit breaker is open."""
        # Force circuit breaker to open state
        elasticsearch_client.circuit_breaker.state = CircuitBreakerState.OPEN
        elasticsearch_client.circuit_breaker.failure_count = 5
        
        # Execute query - should return circuit breaker error
        result = await elasticsearch_client.query_dshield_events(
            time_range_hours=24,
            page=1,
            page_size=100
        )
        
        # Verify circuit breaker error was returned
        assert isinstance(result, dict)
        assert "error" in result
        assert "circuit breaker is open" in result["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_stream_events_with_circuit_breaker_closed(self, elasticsearch_client: ElasticsearchClient) -> None:
        """Test stream events when circuit breaker is closed."""
        # Mock client connection
        elasticsearch_client.client = AsyncMock()
        
        # Mock successful search response
        mock_response = {
            "hits": {
                "total": {"value": 5},
                "hits": [
                    {
                        "_source": {
                            "@timestamp": "2025-08-29T10:00:00Z",
                            "source": {"ip": "192.168.1.1"},
                            "destination": {"ip": "192.168.1.2"}
                        },
                        "sort": ["2025-08-29T10:00:00Z", "doc_id_1"]
                    }
                ]
            }
        }
        elasticsearch_client.client.search.return_value = mock_response
        
        # Mock available indices
        with patch.object(elasticsearch_client, 'get_available_indices') as mock_get_indices:
            mock_get_indices.return_value = ["dshield-*"]
            
            # Execute streaming query
            events, total_count, last_event_id = await elasticsearch_client.stream_dshield_events(
                time_range_hours=24,
                chunk_size=500
            )
            
            # Verify success was recorded
            assert elasticsearch_client.circuit_breaker.failure_count == 0
            assert len(events) == 1
            assert total_count == 5
    
    @pytest.mark.asyncio
    async def test_stream_events_with_circuit_breaker_open(self, elasticsearch_client: ElasticsearchClient) -> None:
        """Test stream events when circuit breaker is open."""
        # Force circuit breaker to open state
        elasticsearch_client.circuit_breaker.state = CircuitBreakerState.OPEN
        elasticsearch_client.circuit_breaker.failure_count = 5
        
        # Execute streaming query - should return circuit breaker error
        result = await elasticsearch_client.stream_dshield_events(
            time_range_hours=24,
            chunk_size=500
        )
        
        # Verify circuit breaker error was returned
        assert isinstance(result, tuple)
        assert len(result) == 3
        assert result[0] == []  # Empty events
        assert result[1] == 0   # Zero total count
        assert result[2] is None  # No last event ID


class TestElasticsearchCircuitBreakerRecovery:
    """Test circuit breaker recovery mechanisms."""
    
    @pytest.fixture
    def error_handler(self) -> MCPErrorHandler:
        """Create a test error handler."""
        config = ErrorHandlingConfig()
        return MCPErrorHandler(config)
    
    @pytest.fixture
    def elasticsearch_client(self, error_handler: MCPErrorHandler) -> ElasticsearchClient:
        """Create a test Elasticsearch client with error handler."""
        with patch('src.elasticsearch_client.get_config') as mock_get_config, \
             patch('src.elasticsearch_client.get_user_config') as mock_get_user_config:
            
            # Mock config
            mock_get_config.return_value = {
                "elasticsearch": {
                    "url": "https://test-elasticsearch:9200",
                    "username": "test_user",
                    "password": "test_pass",
                    "timeout": 30,
                    "max_results": 1000,
                    "index_patterns": {
                        "cowrie": ["cowrie-*"],
                        "zeek": ["zeek-*"],
                        "dshield": ["dshield-*"],
                        "fallback": ["fallback-*"]
                    }
                }
            }
            
            # Mock user config
            mock_user_config_instance = Mock()
            mock_user_config_instance.get_setting.side_effect = lambda section, key: {
                ("query", "default_page_size"): 100,
                ("query", "max_page_size"): 1000,
                ("query", "default_timeout_seconds"): 30,
                ("query", "max_timeout_seconds"): 300,
                ("query", "enable_smart_optimization"): True,
                ("query", "fallback_strategy"): "aggregate",
                ("query", "max_query_complexity"): 10,
                ("logging", "enable_performance_logging"): False
            }.get((section, key), None)
            mock_get_user_config.return_value = mock_user_config_instance
            
            client = ElasticsearchClient(error_handler=error_handler)
            return client
    
    def test_circuit_breaker_recovery_timeout(self, elasticsearch_client: ElasticsearchClient) -> None:
        """Test that circuit breaker recovers after timeout."""
        # Force circuit breaker to open state
        elasticsearch_client.circuit_breaker.state = CircuitBreakerState.OPEN
        elasticsearch_client.circuit_breaker.failure_count = 5
        
        # Simulate time passing (recovery timeout)
        from datetime import datetime, timezone, timedelta
        elasticsearch_client.circuit_breaker.last_failure_time = datetime.now(timezone.utc) - timedelta(seconds=70)
        
        # Check if circuit breaker allows execution (should set to half-open)
        result = elasticsearch_client._check_circuit_breaker("test_operation")
        assert result is True
        assert elasticsearch_client.circuit_breaker.state == CircuitBreakerState.HALF_OPEN
    
    def test_circuit_breaker_success_recovery(self, elasticsearch_client: ElasticsearchClient) -> None:
        """Test that circuit breaker recovers after successful operations."""
        # Set circuit breaker to half-open state
        elasticsearch_client.circuit_breaker.state = CircuitBreakerState.HALF_OPEN
        elasticsearch_client.circuit_breaker.success_count = 0
        
        # Record first success (should stay in half-open)
        elasticsearch_client._record_circuit_breaker_success()
        assert elasticsearch_client.circuit_breaker.state == CircuitBreakerState.HALF_OPEN
        assert elasticsearch_client.circuit_breaker.success_count == 1
        
        # Record second success (should close circuit)
        elasticsearch_client._record_circuit_breaker_success()
        assert elasticsearch_client.circuit_breaker.state == CircuitBreakerState.CLOSED
        assert elasticsearch_client.circuit_breaker.success_count == 0
        assert elasticsearch_client.circuit_breaker.failure_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
