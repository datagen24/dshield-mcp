# data_processor

Data processor for formatting and structuring DShield SIEM data for AI consumption.

This module provides utilities for processing, normalizing, and structuring
DShield SIEM data for downstream AI analysis and reporting. It includes
functions for event normalization, attack pattern detection, enrichment,
summarization, and report generation.

Features:
- Security event normalization and enrichment
- Attack pattern detection
- DShield-specific data mapping
- Summary and report generation
- Utility methods for extracting and analyzing event data

Example:
    >>> from src.data_processor import DataProcessor
    >>> processor = DataProcessor()
    >>> processed = processor.process_security_events(events)
    >>> print(processed)

### _is_debug_mode

```python
def _is_debug_mode()
```

Check if we're running in debug mode or test mode.

## DataProcessor

Process and structure DShield SIEM data for AI analysis.

    This class provides methods to normalize, enrich, and summarize DShield SIEM
    data for use in AI-driven analytics and reporting. It includes attack pattern
    detection, severity/category mapping, and report generation utilities.

    Attributes:
        dshield_attack_patterns: Mapping of attack pattern names to keywords
        dshield_severity_mapping: Mapping of severity labels to EventSeverity
        dshield_category_mapping: Mapping of category labels to EventCategory

    Example:
        >>> processor = DataProcessor()
        >>> summary = processor.generate_security_summary(events)

#### __init__

```python
def __init__(self)
```

Initialize the DataProcessor.

        Sets up DShield-specific mappings for attack patterns, severity, and category.

#### process_security_events

```python
def process_security_events(self, events)
```

Process and normalize security events from DShield SIEM.

        Normalizes, enriches, and detects attack patterns in a list of security events.
        Handles error logging and skips events that cannot be processed.

        Args:
            events: List of raw event dictionaries

        Returns:
            List of processed and normalized event dictionaries

#### process_dshield_attacks

```python
def process_dshield_attacks(self, attacks)
```

Process DShield attack events into structured format.

        Converts raw attack event dictionaries into DShieldAttack model instances.
        Handles error logging and skips attacks that cannot be processed.

        Args:
            attacks: List of raw attack event dictionaries

        Returns:
            List of DShieldAttack model instances

#### process_dshield_reputation

```python
def process_dshield_reputation(self, reputation_data)
```

Process DShield reputation data into structured format.

        Converts raw reputation data dictionaries into DShieldReputation model instances.
        Handles error logging and skips entries that cannot be processed.

        Args:
            reputation_data: List of raw reputation data dictionaries

        Returns:
            Dictionary mapping IP addresses to DShieldReputation model instances

#### process_dshield_top_attackers

```python
def process_dshield_top_attackers(self, attackers)
```

Process DShield top attackers data into structured format.

#### generate_dshield_summary

```python
def generate_dshield_summary(self, events)
```

Generate DShield-specific security summary.

#### generate_security_summary

```python
def generate_security_summary(self, events)
```

Generate security summary statistics with DShield enrichment.

#### generate_attack_report

```python
def generate_attack_report(self, events, threat_intelligence)
```

Generate structured attack report with DShield data.

#### extract_unique_ips

```python
def extract_unique_ips(self, events)
```

Extract unique IP addresses from events.

#### _normalize_event

```python
def _normalize_event(self, event)
```

Normalize event data structure.

#### _enrich_dshield_data

```python
def _enrich_dshield_data(self, event)
```

Enrich event with DShield-specific data.

#### _detect_attack_patterns

```python
def _detect_attack_patterns(self, events)
```

Detect attack patterns in events.

#### _get_top_countries

```python
def _get_top_countries(self, events)
```

Get top countries by attack count.

#### _get_top_ports

```python
def _get_top_ports(self, events)
```

Get top ports by attack count.

#### _get_top_protocols

```python
def _get_top_protocols(self, events)
```

Get top protocols by attack count.

#### _get_top_asns

```python
def _get_top_asns(self, events)
```

Get top ASNs by attack count.

#### _get_top_organizations

```python
def _get_top_organizations(self, events)
```

Get top organizations by attack count.

#### _calculate_average_reputation

```python
def _calculate_average_reputation(self, events)
```

Calculate average reputation score.

#### _get_geographic_distribution

```python
def _get_geographic_distribution(self, events)
```

Get geographic distribution of attacks.

#### _get_port_distribution

```python
def _get_port_distribution(self, events)
```

Get port distribution of attacks.

#### _get_asn_distribution

```python
def _get_asn_distribution(self, events)
```

Get ASN distribution of attacks.

#### _get_organization_distribution

```python
def _get_organization_distribution(self, events)
```

Get organization distribution of attacks.

#### _get_reputation_distribution

```python
def _get_reputation_distribution(self, events)
```

Get reputation score distribution.

#### _generate_timeline

```python
def _generate_timeline(self, events)
```

Generate timeline of events.

#### _analyze_events

```python
def _analyze_events(self, events)
```

Analyze events for patterns and insights.

#### _extract_threat_indicators

```python
def _extract_threat_indicators(self, events, threat_intelligence)
```

Extract threat indicators from events and threat intelligence.

#### _identify_attack_vectors

```python
def _identify_attack_vectors(self, events)
```

Identify attack vectors from events.

#### _identify_affected_systems

```python
def _identify_affected_systems(self, events)
```

Identify affected systems from events.

#### _assess_impact

```python
def _assess_impact(self, events, threat_indicators)
```

Assess the impact of the security incident.

#### _generate_recommendations

```python
def _generate_recommendations(self, events, threat_indicators, impact)
```

Generate security recommendations.

#### _generate_mitigation_actions

```python
def _generate_mitigation_actions(self, events, threat_indicators)
```

Generate specific mitigation actions.

#### _assess_confidence_level

```python
def _assess_confidence_level(self, events, threat_intelligence)
```

Assess confidence level of the analysis.

#### _extract_tags

```python
def _extract_tags(self, events)
```

Extract tags from events.

#### _generate_executive_summary

```python
def _generate_executive_summary(self, events, threat_indicators)
```

Generate executive summary of the security incident.

#### _identify_high_risk_ips

```python
def _identify_high_risk_ips(self, events, threat_intelligence)
```

Identify high-risk IP addresses.

#### _create_empty_summary

```python
def _create_empty_summary(self)
```

Create empty security summary.

#### _create_empty_attack_report

```python
def _create_empty_attack_report(self)
```

Create empty attack report.

#### _calculate_time_range

```python
def _calculate_time_range(self, events)
```

Calculate time range from events, handling empty sequences.

#### _create_empty_dshield_statistics

```python
def _create_empty_dshield_statistics(self)
```

Create empty DShield statistics.
