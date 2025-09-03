# campaign_analyzer

Campaign Analysis Engine for DShield MCP.

Core campaign correlation and analysis engine for identifying coordinated attack campaigns.

## CorrelationMethod

Correlation methods for campaign analysis.

## CampaignConfidence

Campaign confidence levels.

## CampaignEvent

Individual event within a campaign.

## IndicatorRelationship

Relationship between indicators in a campaign.

## Campaign

Campaign data model.

## CampaignAnalyzer

Core campaign analysis and correlation engine.

    Provides methods for correlating security events, expanding indicators,
    and building campaign timelines for coordinated attack detection.

#### __init__

```python
def __init__(self, es_client)
```

Initialize the CampaignAnalyzer.

        Args:
            es_client: Optional ElasticsearchClient instance. If not provided, a new one is created.

#### _extract_iocs_from_event

```python
def _extract_iocs_from_event(self, event)
```

Extract IOCs from an event.

        Args:
            event: Event dictionary to extract IOCs from.

        Returns:
            List of extracted IOCs (IPs, domains, user agents, etc.).

#### _extract_domain_from_url

```python
def _extract_domain_from_url(self, url)
```

Extract domain from URL.

        Args:
            url: URL string to extract domain from.

        Returns:
            Extracted domain or None if extraction fails.

#### _deduplicate_events

```python
def _deduplicate_events(self, events)
```

Remove duplicate events based on event ID.

        Args:
            events: List of event dictionaries to deduplicate.

        Returns:
            List of unique event dictionaries.

#### _extract_infrastructure_indicators

```python
def _extract_infrastructure_indicators(self, events)
```

Extract infrastructure indicators from events.

        Args:
            events: List of event dictionaries to extract indicators from.

        Returns:
            List of infrastructure indicators (domains, certificates, etc.).

#### _extract_behavioral_patterns

```python
def _extract_behavioral_patterns(self, events)
```

Extract behavioral patterns from events.

        Args:
            events: List of event dictionaries to analyze.

        Returns:
            List of behavioral pattern dictionaries.

#### _extract_payload_pattern

```python
def _extract_payload_pattern(self, event)
```

Extract payload pattern from event.

        Args:
            event: Event dictionary to analyze.

        Returns:
            Extracted payload pattern or None if no pattern found.

#### _analyze_attack_sequences

```python
def _analyze_attack_sequences(self, events)
```

Analyze attack sequences and TTP patterns.

        Args:
            events: List of event dictionaries to analyze.

        Returns:
            List of attack sequence dictionaries.

#### _extract_user_agent_patterns

```python
def _extract_user_agent_patterns(self, events)
```

Extract patterns from user agents.

#### _extract_payload_patterns

```python
def _extract_payload_patterns(self, events)
```

Extract patterns from payloads.

#### _extract_payload_signatures

```python
def _extract_payload_signatures(self, payload)
```

Extract signatures from payload.

#### _create_time_windows

```python
def _create_time_windows(self, events, window_minutes)
```

Create time windows for temporal correlation.

#### _extract_ip_addresses

```python
def _extract_ip_addresses(self, events)
```

Extract IP addresses from events.

#### _convert_to_campaign_event

```python
def _convert_to_campaign_event(self, event)
```

Convert raw event to CampaignEvent.

#### _calculate_event_confidence

```python
def _calculate_event_confidence(self, event, all_events)
```

Calculate confidence score for an event.

#### _calculate_time_proximity_score

```python
def _calculate_time_proximity_score(self, event, all_events)
```

Calculate time proximity score for an event.

#### _create_campaign_from_events

```python
def _create_campaign_from_events(self, events)
```

Create a campaign from a list of events.

#### _deduplicate_relationships

```python
def _deduplicate_relationships(self, relationships)
```

Remove duplicate relationships.

#### _group_ips_by_subnet

```python
def _group_ips_by_subnet(self, ips, subnet_mask)
```

Group IP addresses by subnet.
