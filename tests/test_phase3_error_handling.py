#!/usr/bin/env python3
"""Tests for Phase 3 Advanced Error Handling Features.

This module tests the advanced error handling features implemented in Phase 3,
including circuit breaker pattern, error aggregation, and enhanced error
handling methods.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock

from src.mcp_error_handler import (
    MCPErrorHandler, 
    ErrorHandlingConfig, 
    CircuitBreaker, 
    CircuitBreakerConfig,
    CircuitBreakerState,
    ErrorAggregator
)


class TestPhase3ErrorHandlingFeatures:
    """Test Phase 3 advanced error handling features."""
    
    def test_enhanced_error_handling_config(self) -> None:
        """Test enhanced error handling configuration with Phase 3 features."""
        config = ErrorHandlingConfig()
        
        # Test circuit breaker configuration
        assert hasattr(config, 'circuit_breaker')
        assert isinstance(config.circuit_breaker, CircuitBreakerConfig)
        assert config.circuit_breaker.failure_threshold == 5
        assert config.circuit_breaker.recovery_timeout == 60.0
        assert config.circuit_breaker.success_threshold == 2
        
        # Test error aggregation configuration
        assert hasattr(config, 'error_aggregation')
        assert config.error_aggregation['enabled'] is True
        assert config.error_aggregation['window_size'] == 300
        assert config.error_aggregation['max_errors_per_window'] == 100
    
    def test_enhanced_resource_error_methods(self) -> None:
        """Test enhanced resource error handling methods."""
        error_handler = MCPErrorHandler()
        
        # Test resource not found error
        error = error_handler.create_resource_not_found_error("test://resource")
        assert error["error"]["code"] == MCPErrorHandler.RESOURCE_NOT_FOUND
        assert "Resource 'test://resource' not found" in error["error"]["message"]
        assert "suggestion" in error["error"]["data"]
        
        # Test resource access denied error
        error = error_handler.create_resource_access_denied_error("test://resource", "Permission denied")
        assert error["error"]["code"] == MCPErrorHandler.RESOURCE_ACCESS_DENIED
        assert "Access denied to resource 'test://resource'" in error["error"]["message"]
        assert "Permission denied" in error["error"]["message"]
        
        # Test resource unavailable error
        error = error_handler.create_resource_unavailable_error("test://resource", "Service down")
        assert error["error"]["code"] == MCPErrorHandler.RESOURCE_UNAVAILABLE
        assert "Resource 'test://resource' unavailable" in error["error"]["message"]
        assert "Service down" in error["error"]["message"]
    
    def test_circuit_breaker_open_error(self) -> None:
        """Test circuit breaker open error creation."""
        error_handler = MCPErrorHandler()
        
        error = error_handler.create_circuit_breaker_open_error("elasticsearch")
        assert error["error"]["code"] == MCPErrorHandler.EXTERNAL_SERVICE_ERROR
        assert "circuit breaker is open" in error["error"]["message"]
        assert "elasticsearch" in error["error"]["message"]
        assert "suggestion" in error["error"]["data"]
    
    def test_validation_error_with_context(self) -> None:
        """Test validation error with additional context."""
        error_handler = MCPErrorHandler()
        
        # Mock validation error
        mock_validation_error = Mock()
        mock_validation_error.errors.return_value = [
            {"loc": ("field",), "msg": "Field is required", "type": "missing"}
        ]
        
        context = {"tool": "test_tool", "user_input": "invalid_data"}
        error = error_handler.create_validation_error_with_context("test_tool", mock_validation_error, context)
        
        assert error["error"]["code"] == MCPErrorHandler.VALIDATION_ERROR
        assert "Validation failed for tool 'test_tool'" in error["error"]["message"]
        assert "context" in error["error"]["data"]
        assert "validation_errors" in error["error"]["data"]
    
    def test_timeout_error_with_context(self) -> None:
        """Test timeout error with operation context."""
        error_handler = MCPErrorHandler()
        
        operation_context = {"operation": "query", "indices": ["events"], "timeout": 30}
        error = error_handler.create_timeout_error_with_context("test_tool", 30.0, operation_context)
        
        assert error["error"]["code"] == MCPErrorHandler.TIMEOUT_ERROR
        assert "Tool 'test_tool' timed out after 30.0 seconds" in error["error"]["message"]
        assert "operation_context" in error["error"]["data"]
        assert "suggestion" in error["error"]["data"]
    
    def test_enhanced_error_summary(self) -> None:
        """Test enhanced error summary with Phase 3 features."""
        error_handler = MCPErrorHandler()
        
        summary = error_handler.get_enhanced_error_summary()
        
        # Check base summary
        assert "timeouts" in summary
        assert "retry_settings" in summary
        assert "error_codes" in summary
        
        # Check Phase 3 features
        assert "phase_3_features" in summary
        phase3 = summary["phase_3_features"]
        
        assert "circuit_breaker" in phase3
        assert "error_aggregation" in phase3
        assert "enhanced_resource_handling" in phase3
        assert "context_aware_errors" in phase3
        
        # Check circuit breaker config
        cb_config = phase3["circuit_breaker"]
        assert "enabled" in cb_config
        assert "config" in cb_config
        assert cb_config["config"]["failure_threshold"] == 5
    
    def test_error_analytics_access(self) -> None:
        """Test error analytics access methods."""
        error_handler = MCPErrorHandler()
        
        # Test error analytics
        analytics = error_handler.get_error_analytics()
        assert "error_summary" in analytics
        assert "error_trends" in analytics
        assert "aggregation_config" in analytics
        
        # Test with custom window
        analytics = error_handler.get_error_analytics(600)  # 10 minutes
        assert analytics["error_summary"]["window_seconds"] == 600
    
    def test_circuit_breaker_status_access(self) -> None:
        """Test circuit breaker status access."""
        error_handler = MCPErrorHandler()
        
        # Currently returns None as circuit breakers aren't implemented for specific services yet
        status = error_handler.get_circuit_breaker_status("elasticsearch")
        assert status is None


class TestCircuitBreaker:
    """Test CircuitBreaker implementation."""
    
    def test_circuit_breaker_initialization(self) -> None:
        """Test circuit breaker initialization."""
        cb = CircuitBreaker("test_service")
        
        assert cb.service_name == "test_service"
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0
        assert cb.last_failure_time is None
    
    def test_circuit_breaker_can_execute_closed(self) -> None:
        """Test circuit breaker allows execution when closed."""
        cb = CircuitBreaker("test_service")
        
        assert cb.can_execute() is True
    
    def test_circuit_breaker_failure_tracking(self) -> None:
        """Test circuit breaker failure tracking."""
        cb = CircuitBreaker("test_service")
        
        # Simulate failures
        for i in range(4):  # Below threshold
            cb.on_failure(Exception("Test failure"))
            assert cb.state == CircuitBreakerState.CLOSED
        
        # 5th failure should open circuit
        cb.on_failure(Exception("Test failure"))
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.failure_count == 5
    
    def test_circuit_breaker_recovery_timeout(self) -> None:
        """Test circuit breaker recovery timeout."""
        cb = CircuitBreaker("test_service")
        
        # Open circuit
        for i in range(5):
            cb.on_failure(Exception("Test failure"))
        
        assert cb.state == CircuitBreakerState.OPEN
        
        # Should not allow execution immediately
        assert cb.can_execute() is False
        
        # Simulate time passing (mock last_failure_time)
        cb.last_failure_time = datetime.now(timezone.utc) - timedelta(seconds=70)
        
        # Should now allow execution and set to half-open
        assert cb.can_execute() is True
        assert cb.state == CircuitBreakerState.HALF_OPEN
    
    def test_circuit_breaker_success_recovery(self) -> None:
        """Test circuit breaker success recovery."""
        cb = CircuitBreaker("test_service")
        
        # Open circuit
        for i in range(5):
            cb.on_failure(Exception("Test failure"))
        
        # Simulate recovery timeout
        cb.last_failure_time = datetime.now(timezone.utc) - timedelta(seconds=70)
        cb.can_execute()  # This sets to half-open
        
        # Simulate successes
        cb.on_success()
        assert cb.state == CircuitBreakerState.HALF_OPEN
        
        cb.on_success()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0
    
    def test_circuit_breaker_status(self) -> None:
        """Test circuit breaker status reporting."""
        cb = CircuitBreaker("test_service")
        
        status = cb.get_status()
        
        assert "service_name" in status
        assert "state" in status
        assert "failure_count" in status
        assert "success_count" in status
        assert "last_failure_time" in status
        assert "config" in status
        
        assert status["service_name"] == "test_service"
        assert status["state"] == "closed"
        assert status["config"]["failure_threshold"] == 5


class TestErrorAggregator:
    """Test ErrorAggregator implementation."""
    
    def test_error_aggregator_initialization(self) -> None:
        """Test error aggregator initialization."""
        aggregator = ErrorAggregator()
        
        assert aggregator.config["enabled"] is True
        assert aggregator.config["window_size"] == 300
        assert aggregator.config["max_errors_per_window"] == 100
        assert aggregator.config["history_size"] == 1000
    
    def test_error_recording(self) -> None:
        """Test error recording functionality."""
        aggregator = ErrorAggregator()
        
        context = {"tool": "test_tool", "user": "test_user"}
        aggregator.record_error(100, "test_error", context)
        
        # Check error count
        assert aggregator.error_counts["100_test_error"] == 1
        
        # Check error history
        assert len(aggregator.error_history) == 1
        error_record = aggregator.error_history[0]
        assert error_record["error_code"] == 100
        assert error_record["error_type"] == "test_error"
        assert error_record["context"] == context
    
    def test_error_threshold_checking(self) -> None:
        """Test error threshold checking."""
        config = {
            "enabled": True,
            "window_size": 300,
            "max_errors_per_window": 3,
            "history_size": 100
        }
        aggregator = ErrorAggregator(config)
        
        # Record errors up to threshold
        for i in range(3):
            aggregator.record_error(100, "test_error", {"count": i})
        
        # 4th error should trigger warning
        aggregator.record_error(100, "test_error", {"count": 3})
        
        # Check that error count is tracked
        assert aggregator.error_counts["100_test_error"] == 4
    
    def test_error_summary(self) -> None:
        """Test error summary generation."""
        aggregator = ErrorAggregator()
        
        # Record some errors
        for i in range(5):
            aggregator.record_error(100, "test_error", {"count": i})
        
        for i in range(3):
            aggregator.record_error(200, "another_error", {"count": i})
        
        summary = aggregator.get_error_summary()
        
        assert summary["total_errors"] == 8
        assert "100_test_error" in summary["error_patterns"]
        assert "200_another_error" in summary["error_patterns"]
        assert summary["error_patterns"]["100_test_error"]["count"] == 5
        assert summary["error_patterns"]["200_another_error"]["count"] == 3
    
    def test_error_trends(self) -> None:
        """Test error trend analysis."""
        aggregator = ErrorAggregator()
        
        # Record errors over time
        for i in range(10):
            aggregator.record_error(100, "test_error", {"count": i})
        
        trends = aggregator.get_error_trends(1)  # 1 hour
        
        assert "analysis_period_hours" in trends
        assert "total_errors" in trends
        assert "hourly_breakdown" in trends
        assert "trend_percentage" in trends
        assert "trend_description" in trends
    
    def test_error_aggregator_reset(self) -> None:
        """Test error aggregator reset functionality."""
        aggregator = ErrorAggregator()
        
        # Record some errors
        aggregator.record_error(100, "test_error", {"count": 1})
        aggregator.record_error(200, "another_error", {"count": 2})
        
        # Verify errors are recorded
        assert len(aggregator.error_history) == 2
        assert len(aggregator.error_counts) == 2
        
        # Reset
        aggregator.reset()
        
        # Verify reset
        assert len(aggregator.error_history) == 0
        assert len(aggregator.error_counts) == 0


class TestPhase3Integration:
    """Test Phase 3 features integration."""
    
    def test_error_handler_with_aggregator(self) -> None:
        """Test that error handler properly uses error aggregator."""
        config = ErrorHandlingConfig()
        config.error_aggregation["enabled"] = True
        
        error_handler = MCPErrorHandler(config)
        
        # Create an error
        error = error_handler.create_error(100, "Test error", {"test": "data"})
        
        # Check that error was recorded
        analytics = error_handler.get_error_analytics()
        assert analytics["error_summary"]["total_errors"] >= 1
    
    def test_enhanced_error_methods_integration(self) -> None:
        """Test that all enhanced error methods work together."""
        error_handler = MCPErrorHandler()
        
        # Test various error types
        errors = [
            error_handler.create_resource_not_found_error("test://resource"),
            error_handler.create_circuit_breaker_open_error("test_service"),
            error_handler.create_timeout_error_with_context("test_tool", 30.0, {"op": "test"})
        ]
        
        # Verify all errors have proper structure
        for error in errors:
            assert "jsonrpc" in error
            assert "error" in error
            assert "code" in error["error"]
            assert "message" in error["error"]
            assert "data" in error["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
