# campaign_mcp_tools

Campaign Analysis MCP Tools.

MCP tools for campaign analysis and correlation.

## CampaignMCPTools

MCP tools for campaign analysis and correlation.

#### __init__

```python
def __init__(self, es_client)
```

Initialize CampaignMCPTools.

        Args:
            es_client: Optional ElasticsearchClient instance. If not provided, a new one is created.

#### _extract_iocs_from_campaign

```python
def _extract_iocs_from_campaign(self, campaign_events)
```

Extract IOCs from campaign events.

#### _extract_domain_from_url

```python
def _extract_domain_from_url(self, url)
```

Extract domain from URL.

#### _analyze_campaign_ttps

```python
def _analyze_campaign_ttps(self, campaign_events)
```

Analyze TTPs in campaign events.

#### _compare_campaign_ttps

```python
def _compare_campaign_ttps(self, campaigns)
```

Compare TTPs across campaigns.

#### _compare_campaign_infrastructure

```python
def _compare_campaign_infrastructure(self, campaigns)
```

Compare infrastructure across campaigns.

#### _compare_campaign_timing

```python
def _compare_campaign_timing(self, campaigns)
```

Compare timing patterns across campaigns.

#### _compare_campaign_geography

```python
def _compare_campaign_geography(self, campaigns)
```

Compare geographic patterns across campaigns.

#### _compare_campaign_sophistication

```python
def _compare_campaign_sophistication(self, campaigns)
```

Compare sophistication levels across campaigns.

#### _calculate_similarity_matrix

```python
def _calculate_similarity_matrix(self, campaigns, comparison_results)
```

Calculate similarity matrix for campaigns.

#### _generate_comparison_visualization_data

```python
def _generate_comparison_visualization_data(self, campaigns, comparison_results)
```

Generate visualization data for campaign comparison.

#### _group_events_by_campaigns

```python
def _group_events_by_campaigns(self, events, correlation_threshold)
```

Group events by potential campaigns.

#### _build_campaign_search_query

```python
def _build_campaign_search_query(self, search_criteria, time_range_hours)
```

Build search query for campaigns.

#### _generate_campaign_summary

```python
def _generate_campaign_summary(self, campaign)
```

Generate campaign summary.

#### _calculate_sophistication_score

```python
def _calculate_sophistication_score(self, campaign_data)
```

Calculate sophistication score for campaign.
