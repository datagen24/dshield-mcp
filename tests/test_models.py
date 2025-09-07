"""Tests for models module."""

from datetime import UTC, datetime

from src.models import EventCategory, EventSeverity, SecurityEvent


class TestSecurityEvent:
    """Test SecurityEvent model."""

    def test_security_event_creation(self) -> None:
        """Test basic security event creation."""
        event = SecurityEvent(
            id="event-123",
            timestamp=datetime.now(UTC),
            event_type="attack",
            severity=EventSeverity.HIGH,
            description="Suspicious activity detected",
        )

        assert event.id == "event-123"
        assert event.event_type == "attack"
        assert event.severity == EventSeverity.HIGH


class TestEventSeverity:
    """Test EventSeverity enum."""

    def test_severity_values(self) -> None:
        """Test severity enum values."""
        assert EventSeverity.LOW == "low"
        assert EventSeverity.MEDIUM == "medium"
        assert EventSeverity.HIGH == "high"
        assert EventSeverity.CRITICAL == "critical"


class TestEventCategory:
    """Test EventCategory enum."""

    def test_category_values(self) -> None:
        """Test category enum values."""
        assert EventCategory.NETWORK == "network"
        assert EventCategory.APPLICATION == "application"
        assert EventCategory.SYSTEM == "system"
