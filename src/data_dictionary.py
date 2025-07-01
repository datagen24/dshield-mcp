"""
Data Dictionary for DShield MCP Elastic SIEM Integration
Provides comprehensive field descriptions and examples to help models understand
the available data structures and their meanings.
"""

from typing import Dict, List, Any
from datetime import datetime, timedelta


class DataDictionary:
    """Comprehensive data dictionary for DShield SIEM data."""
    
    @staticmethod
    def get_field_descriptions() -> Dict[str, Any]:
        """Get comprehensive field descriptions for DShield data."""
        return {
            "core_fields": {
                "timestamp": {
                    "description": "Event timestamp in ISO 8601 format",
                    "type": "datetime",
                    "examples": ["2024-01-15T10:30:45.123Z", "2024-01-15T14:22:10.456Z"],
                    "usage": "Primary time field for all queries and filtering"
                },
                "id": {
                    "description": "Unique identifier for the event",
                    "type": "string",
                    "examples": ["event_12345", "attack_67890"],
                    "usage": "Used for deduplication and event tracking"
                }
            },
            "network_fields": {
                "source_ip": {
                    "description": "Source IP address (attacker IP in most cases)",
                    "type": "string",
                    "examples": ["192.168.1.100", "10.0.0.50", "203.0.113.45"],
                    "usage": "Primary field for identifying attack sources"
                },
                "destination_ip": {
                    "description": "Destination IP address (target/victim IP)",
                    "type": "string",
                    "examples": ["192.168.1.1", "10.0.0.1"],
                    "usage": "Identifies the target of attacks"
                },
                "source_port": {
                    "description": "Source port number (1-65535)",
                    "type": "integer",
                    "examples": [22, 80, 443, 3389],
                    "usage": "Port used by the attacker"
                },
                "destination_port": {
                    "description": "Destination port number (1-65535)",
                    "type": "integer",
                    "examples": [22, 80, 443, 3389],
                    "usage": "Target port being attacked"
                },
                "protocol": {
                    "description": "Network protocol used",
                    "type": "string",
                    "examples": ["tcp", "udp", "icmp"],
                    "usage": "Protocol classification for attacks"
                }
            },
            "event_fields": {
                "event_type": {
                    "description": "Type of security event",
                    "type": "string",
                    "examples": ["attack", "block", "reputation", "authentication", "malware"],
                    "usage": "Categorizes the nature of the event"
                },
                "severity": {
                    "description": "Event severity level",
                    "type": "enum",
                    "values": ["low", "medium", "high", "critical"],
                    "usage": "Indicates the importance/risk level"
                },
                "category": {
                    "description": "Event category classification",
                    "type": "enum",
                    "values": ["network", "authentication", "malware", "intrusion", "data_exfiltration", "reconnaissance", "denial_of_service", "attack", "block", "reputation"],
                    "usage": "Groups events by security domain"
                },
                "description": {
                    "description": "Human-readable event description",
                    "type": "string",
                    "examples": ["SSH brute force attack detected", "Port scan from suspicious IP"],
                    "usage": "Provides context about what happened"
                }
            },
            "dshield_specific_fields": {
                "country": {
                    "description": "Country of origin for the IP address",
                    "type": "string",
                    "examples": ["United States", "China", "Russia", "Germany"],
                    "usage": "Geographic threat intelligence"
                },
                "asn": {
                    "description": "Autonomous System Number",
                    "type": "string",
                    "examples": ["AS7922", "AS4134", "AS15169"],
                    "usage": "Network infrastructure identification"
                },
                "organization": {
                    "description": "Organization name associated with the IP",
                    "type": "string",
                    "examples": ["Comcast Cable", "China Telecom", "Google LLC"],
                    "usage": "Entity responsible for the IP range"
                },
                "reputation_score": {
                    "description": "DShield reputation score (0-100, higher = more malicious)",
                    "type": "float",
                    "range": [0.0, 100.0],
                    "examples": [85.5, 12.3, 99.1],
                    "usage": "Threat level assessment"
                },
                "attack_count": {
                    "description": "Number of attacks from this source",
                    "type": "integer",
                    "examples": [1, 150, 2500],
                    "usage": "Attack frequency indicator"
                },
                "first_seen": {
                    "description": "First time this source was observed",
                    "type": "datetime",
                    "usage": "Threat actor timeline"
                },
                "last_seen": {
                    "description": "Most recent observation of this source",
                    "type": "datetime",
                    "usage": "Current threat status"
                },
                "tags": {
                    "description": "DShield threat tags",
                    "type": "array",
                    "examples": [["botnet", "ssh_brute_force"], ["malware", "c2"]],
                    "usage": "Threat classification"
                },
                "attack_types": {
                    "description": "Types of attacks observed",
                    "type": "array",
                    "examples": [["ssh_brute_force", "port_scan"], ["web_attack", "sql_injection"]],
                    "usage": "Attack methodology identification"
                }
            },
            "geographic_fields": {
                "country_code": {
                    "description": "ISO country code",
                    "type": "string",
                    "examples": ["US", "CN", "RU", "DE"],
                    "usage": "Standardized country identification"
                },
                "city": {
                    "description": "City name",
                    "type": "string",
                    "examples": ["New York", "Beijing", "Moscow"],
                    "usage": "Geographic precision"
                },
                "latitude": {
                    "description": "Geographic latitude",
                    "type": "float",
                    "usage": "Geographic plotting"
                },
                "longitude": {
                    "description": "Geographic longitude",
                    "type": "float",
                    "usage": "Geographic plotting"
                }
            },
            "service_fields": {
                "service": {
                    "description": "Service name associated with the port",
                    "type": "string",
                    "examples": ["ssh", "http", "https", "rdp"],
                    "usage": "Service identification"
                },
                "service_version": {
                    "description": "Version of the service",
                    "type": "string",
                    "examples": ["OpenSSH 8.2p1", "Apache 2.4.41"],
                    "usage": "Vulnerability assessment"
                }
            }
        }
    
    @staticmethod
    def get_query_examples() -> Dict[str, Any]:
        """Get example queries for common use cases."""
        return {
            "recent_attacks": {
                "description": "Get recent attacks from the last 24 hours",
                "query_type": "query_dshield_attacks",
                "parameters": {
                    "time_range_hours": 24,
                    "size": 100
                },
                "expected_fields": ["source_ip", "destination_ip", "attack_type", "severity", "timestamp"]
            },
            "high_risk_ips": {
                "description": "Find IPs with high reputation scores",
                "query_type": "query_dshield_reputation",
                "parameters": {
                    "size": 50
                },
                "filters": {
                    "reputation_score": {"operator": "gte", "value": 80}
                },
                "expected_fields": ["ip_address", "reputation_score", "country", "attack_count"]
            },
            "geographic_threats": {
                "description": "Get attacks by country",
                "query_type": "query_dshield_geographic_data",
                "parameters": {
                    "size": 100
                },
                "expected_fields": ["country", "attack_count", "unique_attackers"]
            },
            "port_analysis": {
                "description": "Analyze attacks by target port",
                "query_type": "query_dshield_port_data",
                "parameters": {
                    "size": 100
                },
                "expected_fields": ["port", "service", "attack_count", "attack_types"]
            },
            "top_attackers": {
                "description": "Get most active attackers",
                "query_type": "query_dshield_top_attackers",
                "parameters": {
                    "hours": 24,
                    "limit": 50
                },
                "expected_fields": ["ip_address", "attack_count", "country", "reputation_score"]
            }
        }
    
    @staticmethod
    def get_data_patterns() -> Dict[str, Any]:
        """Get common data patterns and their meanings."""
        return {
            "attack_patterns": {
                "ssh_brute_force": {
                    "description": "SSH brute force attacks",
                    "indicators": ["destination_port: 22", "multiple failed logins", "high attack_count"],
                    "severity": "high"
                },
                "port_scan": {
                    "description": "Port scanning activity",
                    "indicators": ["multiple destination_ports", "short time intervals", "reconnaissance category"],
                    "severity": "medium"
                },
                "web_attacks": {
                    "description": "Web application attacks",
                    "indicators": ["destination_ports: [80, 443, 8080]", "http/https protocols", "sql_injection or xss in attack_types"],
                    "severity": "high"
                },
                "botnet_activity": {
                    "description": "Botnet command and control",
                    "indicators": ["botnet tag", "regular intervals", "multiple source_ips"],
                    "severity": "critical"
                }
            },
            "threat_levels": {
                "low": {
                    "reputation_score": "0-20",
                    "attack_count": "1-10",
                    "description": "Minimal threat, likely automated scanning"
                },
                "medium": {
                    "reputation_score": "21-50",
                    "attack_count": "11-100",
                    "description": "Moderate threat, targeted attacks"
                },
                "high": {
                    "reputation_score": "51-80",
                    "attack_count": "101-1000",
                    "description": "High threat, persistent attacker"
                },
                "critical": {
                    "reputation_score": "81-100",
                    "attack_count": "1000+",
                    "description": "Critical threat, known malicious actor"
                }
            },
            "time_patterns": {
                "business_hours": {
                    "description": "Attacks during business hours (9 AM - 5 PM)",
                    "analysis": "May indicate targeted attacks vs automated scanning"
                },
                "weekend_spikes": {
                    "description": "Increased activity on weekends",
                    "analysis": "Often indicates automated attacks when security teams are less active"
                },
                "holiday_patterns": {
                    "description": "Spikes during holidays",
                    "analysis": "Attackers may target periods of reduced security monitoring"
                }
            }
        }
    
    @staticmethod
    def get_analysis_guidelines() -> Dict[str, Any]:
        """Get guidelines for analyzing DShield data."""
        return {
            "correlation_rules": {
                "multiple_attack_types": {
                    "description": "IP with multiple attack types",
                    "action": "High priority investigation - indicates sophisticated attacker",
                    "threshold": "3+ different attack_types"
                },
                "geographic_clustering": {
                    "description": "Multiple attacks from same country",
                    "action": "Check for coordinated attacks or botnet activity",
                    "threshold": "10+ IPs from same country in 24h"
                },
                "port_escalation": {
                    "description": "Progressive port scanning",
                    "action": "Monitor for targeted reconnaissance",
                    "pattern": "Sequential port scanning over time"
                },
                "reputation_spikes": {
                    "description": "Sudden increase in reputation score",
                    "action": "Investigate for new threat intelligence",
                    "threshold": "20+ point increase in 24h"
                }
            },
            "response_priorities": {
                "immediate": {
                    "criteria": ["reputation_score >= 90", "attack_count >= 1000", "critical severity"],
                    "actions": ["Block IP immediately", "Alert security team", "Start incident response"]
                },
                "high": {
                    "criteria": ["reputation_score >= 70", "attack_count >= 100", "high severity"],
                    "actions": ["Monitor closely", "Prepare blocking rules", "Investigate further"]
                },
                "medium": {
                    "criteria": ["reputation_score >= 40", "attack_count >= 10", "medium severity"],
                    "actions": ["Add to watchlist", "Monitor for escalation", "Document for trends"]
                },
                "low": {
                    "criteria": ["reputation_score < 40", "attack_count < 10", "low severity"],
                    "actions": ["Log for reference", "Include in periodic reports", "No immediate action"]
                }
            }
        }
    
    @staticmethod
    def get_initial_prompt() -> str:
        """Get the initial prompt to provide to models for understanding DShield data."""
        field_descriptions = DataDictionary.get_field_descriptions()
        query_examples = DataDictionary.get_query_examples()
        data_patterns = DataDictionary.get_data_patterns()
        analysis_guidelines = DataDictionary.get_analysis_guidelines()
        
        prompt = f"""
# DShield SIEM Data Dictionary

You are working with DShield SIEM data from Elasticsearch. This data contains security events, attacks, and threat intelligence information.

## Available Fields

### Core Fields
{DataDictionary._format_field_section(field_descriptions['core_fields'])}

### Network Fields
{DataDictionary._format_field_section(field_descriptions['network_fields'])}

### Event Fields
{DataDictionary._format_field_section(field_descriptions['event_fields'])}

### DShield-Specific Fields
{DataDictionary._format_field_section(field_descriptions['dshield_specific_fields'])}

### Geographic Fields
{DataDictionary._format_field_section(field_descriptions['geographic_fields'])}

### Service Fields
{DataDictionary._format_field_section(field_descriptions['service_fields'])}

## Common Query Patterns

{DataDictionary._format_query_examples(query_examples)}

## Data Patterns and Threat Levels

{DataDictionary._format_data_patterns(data_patterns)}

## Analysis Guidelines

{DataDictionary._format_analysis_guidelines(analysis_guidelines)}

## Best Practices

1. **Always specify time ranges** - Use time_range_hours parameter for queries
2. **Filter by severity** - Focus on high and critical events for immediate threats
3. **Correlate data** - Combine multiple queries to build comprehensive threat picture
4. **Consider reputation scores** - Higher scores indicate more malicious sources
5. **Look for patterns** - Multiple attacks from same source or geographic region
6. **Use appropriate size limits** - Start with smaller sizes and increase as needed

## Available Tools

- query_dshield_events: General event queries
- query_dshield_attacks: Attack-specific data
- query_dshield_reputation: IP reputation data
- query_dshield_top_attackers: Most active attackers
- query_dshield_geographic_data: Geographic attack distribution
- query_dshield_port_data: Port-based attack analysis
- get_dshield_statistics: Comprehensive statistics
- enrich_ip_with_dshield: IP threat enrichment

When analyzing DShield data, always consider the context, time patterns, and correlation with other security events to provide meaningful insights.
"""
        return prompt
    
    @staticmethod
    def _format_field_section(fields: Dict[str, Any]) -> str:
        """Format a field section for the prompt."""
        formatted = []
        for field_name, field_info in fields.items():
            formatted.append(f"- **{field_name}**: {field_info['description']}")
            if 'examples' in field_info:
                formatted.append(f"  - Examples: {', '.join(map(str, field_info['examples']))}")
            if 'usage' in field_info:
                formatted.append(f"  - Usage: {field_info['usage']}")
            formatted.append("")
        return "\n".join(formatted)
    
    @staticmethod
    def _format_query_examples(examples: Dict[str, Any]) -> str:
        """Format query examples for the prompt."""
        formatted = []
        for name, example in examples.items():
            formatted.append(f"### {name.replace('_', ' ').title()}")
            formatted.append(f"- Description: {example['description']}")
            formatted.append(f"- Query Type: {example['query_type']}")
            formatted.append(f"- Parameters: {example['parameters']}")
            formatted.append(f"- Expected Fields: {', '.join(example['expected_fields'])}")
            formatted.append("")
        return "\n".join(formatted)
    
    @staticmethod
    def _format_data_patterns(patterns: Dict[str, Any]) -> str:
        """Format data patterns for the prompt."""
        formatted = []
        
        # Attack patterns
        formatted.append("### Attack Patterns")
        for pattern_name, pattern_info in patterns['attack_patterns'].items():
            formatted.append(f"- **{pattern_name}**: {pattern_info['description']}")
            formatted.append(f"  - Indicators: {', '.join(pattern_info['indicators'])}")
            formatted.append(f"  - Severity: {pattern_info['severity']}")
            formatted.append("")
        
        # Threat levels
        formatted.append("### Threat Levels")
        for level, info in patterns['threat_levels'].items():
            formatted.append(f"- **{level.title()}**: {info['description']}")
            formatted.append(f"  - Reputation Score: {info['reputation_score']}")
            formatted.append(f"  - Attack Count: {info['attack_count']}")
            formatted.append("")
        
        return "\n".join(formatted)
    
    @staticmethod
    def _format_analysis_guidelines(guidelines: Dict[str, Any]) -> str:
        """Format analysis guidelines for the prompt."""
        formatted = []
        
        # Correlation rules
        formatted.append("### Correlation Rules")
        for rule_name, rule_info in guidelines['correlation_rules'].items():
            formatted.append(f"- **{rule_name.replace('_', ' ').title()}**: {rule_info['description']}")
            formatted.append(f"  - Action: {rule_info['action']}")
            if 'threshold' in rule_info:
                formatted.append(f"  - Threshold: {rule_info['threshold']}")
            formatted.append("")
        
        # Response priorities
        formatted.append("### Response Priorities")
        for priority, info in guidelines['response_priorities'].items():
            formatted.append(f"- **{priority.title()}**:")
            formatted.append(f"  - Criteria: {', '.join(info['criteria'])}")
            formatted.append(f"  - Actions: {', '.join(info['actions'])}")
            formatted.append("")
        
        return "\n".join(formatted) 