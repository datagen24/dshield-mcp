"""Data models for DShield MCP Elastic SIEM integration.

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

"""

import ipaddress
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class EventSeverity(str, Enum):
    """Security event severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventCategory(str, Enum):
    """Security event categories."""

    NETWORK = "network"
    AUTHENTICATION = "authentication"
    MALWARE = "malware"
    INTRUSION = "intrusion"
    DATA_EXFILTRATION = "data_exfiltration"
    RECONNAISSANCE = "reconnaissance"
    DENIAL_OF_SERVICE = "denial_of_service"
    ATTACK = "attack"
    BLOCK = "block"
    REPUTATION = "reputation"
    GEOGRAPHIC = "geographic"
    ASN = "asn"
    ORGANIZATION = "organization"
    PORT = "port"
    PROTOCOL = "protocol"
    OTHER = "other"


class DShieldEventType(str, Enum):
    """DShield specific event types."""

    ATTACK = "attack"
    BLOCK = "block"
    REPUTATION = "reputation"
    TOP_ATTACKER = "top_attacker"
    TOP_PORT = "top_port"
    GEOGRAPHIC = "geographic"
    ASN = "asn"
    ORGANIZATION = "organization"
    TAG = "tag"
    STATISTICS = "statistics"
    SUMMARY = "summary"
    ALERT = "alert"
    LOG = "log"
    REPORT = "report"


class SecurityEvent(BaseModel):
    """Model for security events from DShield SIEM."""

    id: str = Field(..., description="Unique event identifier")
    timestamp: datetime = Field(..., description="Event timestamp")
    source_ip: str | None = Field(None, description="Source IP address")
    destination_ip: str | None = Field(None, description="Destination IP address")
    source_port: int | None = Field(None, description="Source port")
    destination_port: int | None = Field(None, description="Destination port")
    protocol: str | None = Field(None, description="Network protocol")
    event_type: str = Field(..., description="Type of security event")
    severity: EventSeverity = Field(EventSeverity.MEDIUM, description="Event severity")
    category: EventCategory = Field(EventCategory.OTHER, description="Event category")
    description: str = Field(..., description="Event description")

    # DShield-specific fields
    country: str | None = Field(None, description="Country of origin")
    asn: str | None = Field(None, description="Autonomous System Number")
    organization: str | None = Field(None, description="Organization name")
    reputation_score: float | None = Field(None, description="DShield reputation score")
    attack_count: int | None = Field(None, description="Number of attacks from this source")
    first_seen: datetime | None = Field(None, description="First seen timestamp")
    last_seen: datetime | None = Field(None, description="Last seen timestamp")
    tags: list[str] = Field(default_factory=list, description="DShield tags")
    attack_types: list[str] = Field(default_factory=list, description="Types of attacks")

    # Metadata
    raw_data: dict[str, Any] = Field(default_factory=dict, description="Raw event data")
    indices: list[str] = Field(default_factory=list, description="Source indices")

    @field_validator("source_ip", "destination_ip")
    @classmethod
    def validate_ip_address(cls, v: str | None) -> str | None:
        """Validate IP address format.

        Args:
            v: IP address string to validate

        Returns:
            The validated IP address string

        Raises:
            ValueError: If the IP address format is invalid

        """
        if v is not None:
            try:
                ipaddress.ip_address(v)
            except ValueError:
                raise ValueError(f"Invalid IP address: {v}") from None
        return v

    @field_validator("source_port", "destination_port")
    @classmethod
    def validate_port(cls, v: int | None) -> int | None:
        """Validate port number.

        Args:
            v: Port number to validate

        Returns:
            The validated port number

        Raises:
            ValueError: If the port number is outside valid range (1-65535)

        """
        if v is not None and (v < 1 or v > 65535):
            raise ValueError(f"Invalid port number: {v}")
        return v

    @field_validator("reputation_score")
    @classmethod
    def validate_reputation_score(cls, v: float | None) -> float | None:
        """Validate reputation score range.

        Args:
            v: Reputation score to validate

        Returns:
            The validated reputation score

        Raises:
            ValueError: If the reputation score is outside valid range (0-100)

        """
        if v is not None and (v < 0 or v > 100):
            raise ValueError(f"Reputation score must be between 0 and 100: {v}")
        return v


class DShieldAttack(BaseModel):
    """Model for DShield attack events."""

    id: str = Field(..., description="Unique attack identifier")
    timestamp: datetime = Field(..., description="Attack timestamp")
    source_ip: str = Field(..., description="Attacker IP address")
    destination_ip: str | None = Field(None, description="Target IP address")
    source_port: int | None = Field(None, description="Attacker port")
    destination_port: int | None = Field(None, description="Target port")
    protocol: str | None = Field(None, description="Attack protocol")
    attack_type: str = Field(..., description="Type of attack")
    severity: EventSeverity = Field(EventSeverity.HIGH, description="Attack severity")
    description: str = Field(..., description="Attack description")

    # DShield-specific attack fields
    country: str | None = Field(None, description="Attacker country")
    asn: str | None = Field(None, description="Attacker ASN")
    organization: str | None = Field(None, description="Attacker organization")
    reputation_score: float | None = Field(None, description="Attacker reputation score")
    attack_count: int = Field(1, description="Number of attack attempts")
    first_seen: datetime | None = Field(None, description="First attack timestamp")
    last_seen: datetime | None = Field(None, description="Last attack timestamp")
    tags: list[str] = Field(default_factory=list, description="Attack tags")
    attack_methods: list[str] = Field(default_factory=list, description="Attack methods used")

    # Metadata
    raw_data: dict[str, Any] = Field(default_factory=dict, description="Raw attack data")
    indices: list[str] = Field(default_factory=list, description="Source indices")


class DShieldReputation(BaseModel):
    """Model for DShield reputation data."""

    ip_address: str = Field(..., description="IP address")
    reputation_score: float | None = Field(None, description="Reputation score (0-100)")
    threat_level: str | None = Field(None, description="Threat level")
    country: str | None = Field(None, description="Country of origin")
    asn: str | None = Field(None, description="Autonomous System Number")
    organization: str | None = Field(None, description="Organization name")
    first_seen: datetime | None = Field(None, description="First seen timestamp")
    last_seen: datetime | None = Field(None, description="Last seen timestamp")
    attack_types: list[str] = Field(default_factory=list, description="Types of attacks")
    tags: list[str] = Field(default_factory=list, description="Threat tags")
    attack_count: int | None = Field(None, description="Total attack count")
    port_count: int | None = Field(None, description="Number of ports targeted")
    service_count: int | None = Field(None, description="Number of services targeted")
    raw_data: dict[str, Any] = Field(default_factory=dict, description="Raw threat data")

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, v: str) -> str:
        """Validate IP address format."""
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError(f"Invalid IP address: {v}") from None
        return v

    @field_validator("reputation_score")
    @classmethod
    def validate_reputation_score(cls, v: int | None) -> int | None:
        """Validate reputation score range."""
        if v is not None and (v < 0 or v > 100):
            raise ValueError(f"Reputation score must be between 0 and 100: {v}")
        return v


class DShieldTopAttacker(BaseModel):
    """Model for DShield top attacker data."""

    ip_address: str = Field(..., description="Attacker IP address")
    attack_count: int = Field(..., description="Number of attacks")
    country: str | None = Field(None, description="Attacker country")
    asn: str | None = Field(None, description="Attacker ASN")
    organization: str | None = Field(None, description="Attacker organization")
    reputation_score: float | None = Field(None, description="Reputation score")
    first_seen: datetime | None = Field(None, description="First attack timestamp")
    last_seen: datetime | None = Field(None, description="Last attack timestamp")
    attack_types: list[str] = Field(default_factory=list, description="Attack types")
    tags: list[str] = Field(default_factory=list, description="Threat tags")
    target_ports: list[int] = Field(default_factory=list, description="Targeted ports")
    target_services: list[str] = Field(default_factory=list, description="Targeted services")
    raw_data: dict[str, Any] = Field(default_factory=dict, description="Raw attacker data")

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, v: str) -> str:
        """Validate IP address format."""
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError(f"Invalid IP address: {v}") from None
        return v


class DShieldGeographicData(BaseModel):
    """Model for DShield geographic data."""

    country: str = Field(..., description="Country name")
    country_code: str | None = Field(None, description="Country code")
    attack_count: int = Field(0, description="Number of attacks from this country")
    unique_attackers: int = Field(0, description="Number of unique attackers")
    reputation_score: float | None = Field(None, description="Average reputation score")
    top_attackers: list[str] = Field(default_factory=list, description="Top attacker IPs")
    attack_types: list[str] = Field(default_factory=list, description="Attack types")
    target_ports: list[int] = Field(default_factory=list, description="Targeted ports")
    timestamp: datetime = Field(default_factory=datetime.now, description="Data timestamp")
    raw_data: dict[str, Any] = Field(default_factory=dict, description="Raw geographic data")


class DShieldPortData(BaseModel):
    """Model for DShield port data."""

    port: int = Field(..., description="Port number")
    service: str | None = Field(None, description="Service name")
    attack_count: int = Field(0, description="Number of attacks on this port")
    unique_attackers: int = Field(0, description="Number of unique attackers")
    reputation_score: float | None = Field(None, description="Average reputation score")
    top_attackers: list[str] = Field(default_factory=list, description="Top attacker IPs")
    attack_types: list[str] = Field(default_factory=list, description="Attack types")
    countries: list[str] = Field(default_factory=list, description="Attacker countries")
    timestamp: datetime = Field(default_factory=datetime.now, description="Data timestamp")
    raw_data: dict[str, Any] = Field(default_factory=dict, description="Raw port data")

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port number."""
        if v < 1 or v > 65535:
            raise ValueError(f"Port must be between 1 and 65535: {v}")
        return v


class ThreatIntelligenceSource(str, Enum):
    """Threat intelligence sources."""

    DSHIELD = "dshield"
    VIRUSTOTAL = "virustotal"
    SHODAN = "shodan"
    ABUSEIPDB = "abuseipdb"
    ALIENVAULT = "alienvault"
    THREATFOX = "threatfox"


class ThreatIntelligence(BaseModel):
    """Model for DShield threat intelligence data."""

    ip_address: str = Field(..., description="IP address")
    reputation_score: float | None = Field(None, description="Reputation score (0-100)")
    threat_level: str | None = Field(None, description="Threat level")
    country: str | None = Field(None, description="Country of origin")
    asn: str | None = Field(None, description="Autonomous System Number")
    organization: str | None = Field(None, description="Organization name")
    first_seen: datetime | None = Field(None, description="First seen timestamp")
    last_seen: datetime | None = Field(None, description="Last seen timestamp")
    attack_types: list[str] = Field(default_factory=list, description="Types of attacks")
    tags: list[str] = Field(default_factory=list, description="Threat tags")
    attack_count: int | None = Field(None, description="Total attack count")
    port_count: int | None = Field(None, description="Number of ports targeted")
    service_count: int | None = Field(None, description="Number of services targeted")
    raw_data: dict[str, Any] = Field(default_factory=dict, description="Raw threat data")

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, v: str) -> str:
        """Validate IP address format."""
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError(f"Invalid IP address: {v}") from None
        return v

    @field_validator("reputation_score")
    @classmethod
    def validate_reputation_score(cls, v: int | None) -> int | None:
        """Validate reputation score range."""
        if v is not None and (v < 0 or v > 100):
            raise ValueError(f"Reputation score must be between 0 and 100: {v}")
        return v


class ThreatIntelligenceResult(BaseModel):
    """Enhanced threat intelligence result from multiple sources."""

    ip_address: str = Field(..., description="IP address")
    domain: str | None = Field(None, description="Associated domain")

    # Aggregated threat scores
    overall_threat_score: float | None = Field(None, description="Overall threat score (0-100)")
    confidence_score: float | None = Field(None, description="Confidence in assessment (0-1)")

    # Source-specific data
    source_results: dict[ThreatIntelligenceSource, dict[str, Any]] = Field(
        default_factory=dict,
        description="Results from each source",
    )

    # Correlated indicators
    threat_indicators: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Correlated threat indicators",
    )

    # Geographic and network data
    geographic_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Geographic information",
    )
    network_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Network infrastructure data",
    )

    # Timestamps
    first_seen: datetime | None = Field(None, description="First seen across sources")
    last_seen: datetime | None = Field(None, description="Last seen across sources")

    # Metadata
    sources_queried: list[ThreatIntelligenceSource] = Field(
        default_factory=list,
        description="Sources that were queried",
    )
    query_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Query timestamp"
    )
    cache_hit: bool = Field(False, description="Whether result was from cache")

    # Correlation metrics
    correlation_metrics: dict[str, Any] | None = Field(
        None,
        description="Correlation quality metrics and statistics",
    )

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, v: str) -> str:
        """Validate IP address format."""
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError(f"Invalid IP address: {v}") from None
        return v

    @field_validator("overall_threat_score")
    @classmethod
    def validate_overall_threat_score(cls, v: float) -> float:
        """Validate overall threat score range."""
        if v is not None and (v < 0 or v > 100):
            raise ValueError(f"Overall threat score must be between 0 and 100: {v}")
        return v

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence_score(cls, v: float) -> float:
        """Validate confidence score range."""
        if v is not None and (v < 0 or v > 1):
            raise ValueError(f"Confidence score must be between 0 and 1: {v}")
        return v


class DomainIntelligence(BaseModel):
    """Domain threat intelligence data."""

    domain: str = Field(..., description="Domain name")
    threat_score: float | None = Field(None, description="Threat score (0-100)")
    reputation_score: float | None = Field(None, description="Reputation score (0-100)")

    # DNS and infrastructure
    ip_addresses: list[str] = Field(default_factory=list, description="Associated IP addresses")
    nameservers: list[str] = Field(default_factory=list, description="Nameservers")
    registrar: str | None = Field(None, description="Domain registrar")
    creation_date: datetime | None = Field(None, description="Domain creation date")

    # Threat indicators
    malware_families: list[str] = Field(default_factory=list, description="Associated malware")
    categories: list[str] = Field(default_factory=list, description="Threat categories")
    tags: list[str] = Field(default_factory=list, description="Threat tags")

    # Source data
    source_results: dict[ThreatIntelligenceSource, dict[str, Any]] = Field(
        default_factory=dict,
        description="Results from each source",
    )

    # Metadata
    sources_queried: list[ThreatIntelligenceSource] = Field(
        default_factory=list,
        description="Sources that were queried",
    )
    query_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Query timestamp"
    )
    cache_hit: bool = Field(False, description="Whether result was from cache")

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        """Validate domain name format."""
        if not v or "." not in v:
            raise ValueError(f"Invalid domain name: {v}")
        return v.lower()

    @field_validator("threat_score", "reputation_score")
    @classmethod
    def validate_score(cls, v: float) -> float:
        """Validate score range."""
        if v is not None and (v < 0 or v > 100):
            raise ValueError(f"Score must be between 0 and 100: {v}")
        return v


class AttackReport(BaseModel):
    """Model for structured attack reports."""

    report_id: str = Field(..., description="Unique report identifier")
    timestamp: datetime = Field(default_factory=datetime.now, description="Report timestamp")
    title: str = Field(..., description="Report title")
    summary: str = Field(..., description="Executive summary")

    # Event analysis
    total_events: int = Field(..., description="Total number of events analyzed")
    unique_ips: int = Field(..., description="Number of unique IP addresses")
    time_range: dict[str, datetime] = Field(..., description="Analysis time range")

    # Threat intelligence
    threat_indicators: list[dict[str, Any]] = Field(
        default_factory=list, description="Threat indicators"
    )
    high_risk_ips: list[str] = Field(default_factory=list, description="High-risk IP addresses")

    # Attack details
    attack_vectors: list[str] = Field(default_factory=list, description="Attack vectors identified")
    affected_systems: list[str] = Field(default_factory=list, description="Affected systems")
    impact_assessment: str = Field(..., description="Impact assessment")

    # DShield-specific fields
    dshield_attacks: list[DShieldAttack] = Field(
        default_factory=list, description="DShield attack events"
    )
    dshield_reputation: dict[str, DShieldReputation] = Field(
        default_factory=dict, description="DShield reputation data"
    )
    top_attackers: list[DShieldTopAttacker] = Field(
        default_factory=list, description="Top attackers"
    )
    geographic_data: list[DShieldGeographicData] = Field(
        default_factory=list, description="Geographic data"
    )
    port_data: list[DShieldPortData] = Field(default_factory=list, description="Port data")

    # Recommendations
    recommendations: list[str] = Field(default_factory=list, description="Security recommendations")
    mitigation_actions: list[str] = Field(default_factory=list, description="Recommended actions")

    # Metadata
    analyst: str | None = Field(None, description="Analyst name")
    confidence_level: str = Field("medium", description="Confidence level of analysis")
    tags: list[str] = Field(default_factory=list, description="Report tags")

    # Raw data
    events: list[SecurityEvent] = Field(default_factory=list, description="Analyzed events")
    threat_intelligence: dict[str, ThreatIntelligence] = Field(
        default_factory=dict, description="Threat intelligence data"
    )


class SecuritySummary(BaseModel):
    """Model for security summary statistics."""

    timestamp: datetime = Field(default_factory=datetime.now, description="Summary timestamp")
    time_range_hours: int = Field(..., description="Time range in hours")

    # Event statistics
    total_events: int = Field(0, description="Total number of events")
    events_by_severity: dict[str, int] = Field(
        default_factory=dict, description="Events by severity"
    )
    events_by_category: dict[str, int] = Field(
        default_factory=dict, description="Events by category"
    )

    # Network statistics
    unique_source_ips: int = Field(0, description="Unique source IP addresses")
    unique_destination_ips: int = Field(0, description="Unique destination IP addresses")
    top_source_ips: list[dict[str, Any]] = Field(
        default_factory=list, description="Top source IPs by event count"
    )
    top_destination_ips: list[dict[str, Any]] = Field(
        default_factory=list, description="Top destination IPs by event count"
    )

    # Threat statistics
    high_risk_events: int = Field(0, description="High-risk events")
    threat_intelligence_hits: int = Field(0, description="IPs with threat intelligence")

    # DShield-specific statistics
    dshield_attacks: int = Field(0, description="DShield attack events")
    dshield_blocks: int = Field(0, description="DShield block events")
    dshield_reputation_hits: int = Field(0, description="IPs with DShield reputation data")
    top_attackers: list[DShieldTopAttacker] = Field(
        default_factory=list, description="Top attackers"
    )
    geographic_distribution: dict[str, int] = Field(
        default_factory=dict, description="Attacks by country"
    )
    port_distribution: dict[int, int] = Field(default_factory=dict, description="Attacks by port")

    # Performance metrics
    query_duration_ms: float | None = Field(None, description="Query duration in milliseconds")
    indices_queried: list[str] = Field(default_factory=list, description="Indices queried")


class QueryFilter(BaseModel):
    """Model for Elasticsearch query filters."""

    field: str = Field(..., description="Field to filter on")
    value: str | int | float | bool | list[Any] = Field(..., description="Filter value")
    operator: str = Field(
        "eq", description="Filter operator (eq, ne, gt, lt, gte, lte, in, not_in)"
    )

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        """Validate filter operator."""
        valid_operators = [
            "eq",
            "ne",
            "gt",
            "lt",
            "gte",
            "lte",
            "in",
            "not_in",
            "exists",
            "wildcard",
        ]
        if v not in valid_operators:
            raise ValueError(f"Invalid operator: {v}. Must be one of {valid_operators}")
        return v


class ElasticsearchQuery(BaseModel):
    """Model for Elasticsearch queries."""

    indices: list[str] = Field(default_factory=list, description="Indices to query")
    time_range: dict[str, datetime] = Field(..., description="Time range for query")
    filters: list[QueryFilter] = Field(default_factory=list, description="Query filters")
    size: int = Field(1000, description="Maximum number of results")
    sort: list[dict[str, str]] = Field(default_factory=list, description="Sort criteria")
    aggs: dict[str, Any] = Field(default_factory=dict, description="Aggregations")

    @field_validator("size")
    @classmethod
    def validate_size(cls, v: int) -> int:
        """Validate result size."""
        if v < 1 or v > 10000:
            raise ValueError(f"Size must be between 1 and 10000: {v}")
        return v


class DShieldStatistics(BaseModel):
    """Model for DShield statistics data."""

    timestamp: datetime = Field(default_factory=datetime.now, description="Statistics timestamp")
    time_range_hours: int = Field(..., description="Time range in hours")

    # Attack statistics
    total_attacks: int = Field(0, description="Total number of attacks")
    unique_attackers: int = Field(0, description="Number of unique attackers")
    total_targets: int = Field(0, description="Number of unique targets")

    # Geographic statistics
    countries_attacking: int = Field(0, description="Number of countries with attackers")
    top_countries: list[dict[str, Any]] = Field(
        default_factory=list, description="Top attacking countries"
    )

    # Port statistics
    ports_targeted: int = Field(0, description="Number of unique ports targeted")
    top_ports: list[dict[str, Any]] = Field(default_factory=list, description="Top targeted ports")

    # Protocol statistics
    protocols_used: int = Field(0, description="Number of unique protocols used")
    top_protocols: list[dict[str, Any]] = Field(
        default_factory=list, description="Top protocols used"
    )

    # ASN statistics
    asns_attacking: int = Field(0, description="Number of unique ASNs attacking")
    top_asns: list[dict[str, Any]] = Field(default_factory=list, description="Top attacking ASNs")

    # Organization statistics
    organizations_attacking: int = Field(0, description="Number of unique organizations attacking")
    top_organizations: list[dict[str, Any]] = Field(
        default_factory=list, description="Top attacking organizations"
    )

    # Reputation statistics
    high_reputation_ips: int = Field(0, description="Number of IPs with high reputation scores")
    average_reputation_score: float | None = Field(None, description="Average reputation score")

    # Performance metrics
    query_duration_ms: float | None = Field(None, description="Query duration in milliseconds")
    indices_queried: list[str] = Field(default_factory=list, description="Indices queried")
