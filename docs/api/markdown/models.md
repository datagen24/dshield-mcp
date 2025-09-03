# models

Data models for DShield MCP Elastic SIEM integration.

This module provides comprehensive data models for the DShield MCP server,
optimized for DShield SIEM data structures and patterns. It includes models
for security events, attacks, reputation data, and various DShield-specific
data types.

The models are built using Pydantic for automatic validation, serialization,
and documentation generation. They provide type safety and ensure data
consistency across the application.

This module provides:
- Security event models with validation
- DShield-specific data models
- Threat intelligence models
- Query and filter models
- Statistics and summary models

Example:
    >>> from src.models import SecurityEvent, EventSeverity
    >>> event = SecurityEvent(
    ...     id="event_123",
    ...     timestamp=datetime.now(),
    ...     event_type="attack",
    ...     severity=EventSeverity.HIGH,
    ...     description="Suspicious activity detected"
    ... )
    >>> print(event.severity)
    EventSeverity.HIGH

## EventSeverity

Security event severity levels.

## EventCategory

Security event categories.

## DShieldEventType

DShield specific event types.

## SecurityEvent

Model for security events from DShield SIEM.

#### validate_ip_address

```python
def validate_ip_address(cls, v)
```

Validate IP address format.

        Args:
            v: IP address string to validate

        Returns:
            The validated IP address string

        Raises:
            ValueError: If the IP address format is invalid

#### validate_port

```python
def validate_port(cls, v)
```

Validate port number.

        Args:
            v: Port number to validate

        Returns:
            The validated port number

        Raises:
            ValueError: If the port number is outside valid range (1-65535)

#### validate_reputation_score

```python
def validate_reputation_score(cls, v)
```

Validate reputation score range.

        Args:
            v: Reputation score to validate

        Returns:
            The validated reputation score

        Raises:
            ValueError: If the reputation score is outside valid range (0-100)

## DShieldAttack

Model for DShield attack events.

## DShieldReputation

Model for DShield reputation data.

#### validate_ip_address

```python
def validate_ip_address(cls, v)
```

Validate IP address format.

#### validate_reputation_score

```python
def validate_reputation_score(cls, v)
```

Validate reputation score range.

## DShieldTopAttacker

Model for DShield top attacker data.

#### validate_ip_address

```python
def validate_ip_address(cls, v)
```

Validate IP address format.

## DShieldGeographicData

Model for DShield geographic data.

## DShieldPortData

Model for DShield port data.

#### validate_port

```python
def validate_port(cls, v)
```

Validate port number.

## ThreatIntelligenceSource

Threat intelligence sources.

## ThreatIntelligence

Model for DShield threat intelligence data.

#### validate_ip_address

```python
def validate_ip_address(cls, v)
```

Validate IP address format.

#### validate_reputation_score

```python
def validate_reputation_score(cls, v)
```

Validate reputation score range.

## ThreatIntelligenceResult

Enhanced threat intelligence result from multiple sources.

#### validate_ip_address

```python
def validate_ip_address(cls, v)
```

Validate IP address format.

#### validate_overall_threat_score

```python
def validate_overall_threat_score(cls, v)
```

Validate overall threat score range.

#### validate_confidence_score

```python
def validate_confidence_score(cls, v)
```

Validate confidence score range.

## DomainIntelligence

Domain threat intelligence data.

#### validate_domain

```python
def validate_domain(cls, v)
```

Validate domain name format.

#### validate_score

```python
def validate_score(cls, v)
```

Validate score range.

## AttackReport

Model for structured attack reports.

## SecuritySummary

Model for security summary statistics.

## QueryFilter

Model for Elasticsearch query filters.

#### validate_operator

```python
def validate_operator(cls, v)
```

Validate filter operator.

## ElasticsearchQuery

Model for Elasticsearch queries.

#### validate_size

```python
def validate_size(cls, v)
```

Validate result size.

## DShieldStatistics

Model for DShield statistics data.
