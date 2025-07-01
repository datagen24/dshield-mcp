# DShield MCP Usage Guide

This guide explains how to use the DShield MCP utility to integrate your Elastic SIEM with ChatGPT for enhanced security analysis.

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd dshield-mcp

# Install dependencies
pip install -r requirements.txt

# Or install in development mode
pip install -e .
```

### 2. Configuration

```bash
# Run interactive configuration setup
python config.py setup

# Test connections
python config.py test

# Validate configuration
python config.py validate
```

### 3. Run the MCP Server

```bash
# Start the MCP server
python mcp_server.py
```

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Elasticsearch Configuration
ELASTICSEARCH_URL=https://your-elasticsearch-cluster:9200
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=your-password
ELASTICSEARCH_VERIFY_SSL=true
ELASTICSEARCH_CA_CERTS=/path/to/ca.crt

# DShield API Configuration
DSHIELD_API_KEY=your-dshield-api-key
DSHIELD_API_URL=https://dshield.org/api

# MCP Server Configuration
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=8000
MCP_SERVER_DEBUG=false

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Security Configuration
RATE_LIMIT_REQUESTS_PER_MINUTE=60
MAX_QUERY_RESULTS=1000
QUERY_TIMEOUT_SECONDS=30

# Data Processing Configuration
DEFAULT_TIME_RANGE_HOURS=24
MAX_IP_ENRICHMENT_BATCH_SIZE=100
CACHE_TTL_SECONDS=300

# Optional: Proxy Configuration
HTTP_PROXY=
HTTPS_PROXY=
NO_PROXY=localhost,127.0.0.1
```

## Configuration Optimizations

### Index Pattern Optimization
The system has been optimized to include only valid, existing index patterns to minimize connection retries and improve performance:

**Supported Index Patterns:**
- **Cowrie Honeypot**: `cowrie-*`, `cowrie.dshield-*`, `cowrie.vt_data-*`, `cowrie.webhoneypot-*`
- **Zeek Network**: `filebeat-zeek-*`, `zeek.connection*`, `zeek.dns*`, `zeek.files*`, `zeek.http*`, `zeek.ssl*`

**Benefits:**
- Reduced connection retries on non-existent indices
- Faster initial connection establishment
- Improved overall system performance
- Cleaner error handling and logging

### Data Dictionary Integration
The data dictionary is automatically provided to AI models during initialization, reducing the need for trial-and-error query formulation.

## Using with ChatGPT

### Method 1: MCP Protocol Integration

1. **Start the MCP Server**:
   ```bash
   python mcp_server.py
   ```

2. **Configure ChatGPT Client**:
   - Add the MCP server to your ChatGPT client configuration
   - The server will be available as `dshield-elastic-mcp`

3. **Available Tools**:
   - `query_dshield_events`: Query DShield events from Elasticsearch
   - `query_dshield_attacks`: Query DShield attack data specifically
   - `query_dshield_reputation`: Query DShield reputation data for IP addresses
   - `query_dshield_top_attackers`: Query DShield top attackers data
   - `query_dshield_geographic_data`: Query DShield geographic attack data
   - `query_dshield_port_data`: Query DShield port attack data
   - `get_dshield_statistics`: Get comprehensive DShield statistics
   - `enrich_ip_with_dshield`: Enrich IP address with DShield threat intelligence
   - `generate_attack_report`: Generate structured attack reports
   - `query_events_by_ip`: Query events for specific IP addresses
   - `get_security_summary`: Get security summary for the last 24 hours
   - `get_data_dictionary`: Get comprehensive data dictionary for DShield SIEM fields
   - `test_elasticsearch_connection`: Test connection to Elasticsearch and show available indices

### Method 2: Context Injection

1. **Generate Context**:
   ```python
   from src.context_injector import ContextInjector
   
   context_injector = ContextInjector()
   context = context_injector.prepare_security_context(events, threat_intelligence)
   chatgpt_context = context_injector.inject_context_for_chatgpt(context)
   ```

2. **Use with ChatGPT**:
   - Copy the generated context
   - Paste it into your ChatGPT conversation
   - Ask ChatGPT to analyze the security data

## Data Dictionary Usage

The DShield MCP server includes a comprehensive data dictionary that helps AI models understand the available data structures and analysis patterns.

### Accessing the Data Dictionary

#### Method 1: MCP Tool
```python
# Get the data dictionary as a formatted prompt
result = await mcp_client.call_tool("get_data_dictionary", {
    "format": "prompt"
})

# Get specific sections as JSON
result = await mcp_client.call_tool("get_data_dictionary", {
    "format": "json",
    "sections": ["fields", "examples"]
})
```

#### Method 2: MCP Resource
```python
# Read the data dictionary resource
dictionary = await mcp_client.read_resource("dshield://data-dictionary")
```

#### Method 3: Server Initialization
The data dictionary is automatically provided to models during server initialization as part of the experimental capabilities.

### Data Dictionary Contents

The data dictionary includes:

1. **Field Descriptions**: Detailed explanations of all available fields with examples and usage guidelines
2. **Query Examples**: Pre-built patterns for common security analysis tasks
3. **Data Patterns**: Recognition patterns for attack types, threat levels, and time-based analysis
4. **Analysis Guidelines**: Correlation rules and response priorities for threat assessment

### Example: Using the Data Dictionary

```python
import asyncio
from src.data_dictionary import DataDictionary

async def demonstrate_data_dictionary():
    # Get the initial prompt for models
    prompt = DataDictionary.get_initial_prompt()
    print(f"Generated prompt ({len(prompt)} characters)")
    
    # Get field descriptions
    field_descriptions = DataDictionary.get_field_descriptions()
    print(f"Available field categories: {list(field_descriptions.keys())}")
    
    # Get query examples
    query_examples = DataDictionary.get_query_examples()
    for name, example in query_examples.items():
        print(f"{name}: {example['description']}")
    
    # Get analysis guidelines
    guidelines = DataDictionary.get_analysis_guidelines()
    print(f"Correlation rules: {len(guidelines['correlation_rules'])}")
    print(f"Response priorities: {len(guidelines['response_priorities'])}")

# Run the example
asyncio.run(demonstrate_data_dictionary())
```

### Benefits for AI Models

- **Reduced Trial and Error**: Models receive comprehensive field descriptions and usage patterns upfront
- **Standardized Analysis**: Pre-defined correlation rules and threat levels ensure consistent analysis
- **Better Query Formulation**: Query examples help models construct effective searches
- **Contextual Understanding**: Data patterns help models recognize attack signatures and threat indicators

## Example Workflows

### Basic Security Analysis

```python
import asyncio
from src.elasticsearch_client import ElasticsearchClient
from src.dshield_client import DShieldClient
from src.data_processor import DataProcessor

async def basic_analysis():
    # Initialize clients
    es_client = ElasticsearchClient()
    dshield_client = DShieldClient()
    data_processor = DataProcessor()
    
    # Connect to Elasticsearch
    await es_client.connect()
    
    # Query recent events
    events = await es_client.query_security_events(time_range_hours=24)
    
    # Process events
    processed_events = data_processor.process_security_events(events)
    
    # Generate summary
    summary = data_processor.generate_security_summary(processed_events)
    
    # Extract IPs for enrichment
    unique_ips = data_processor.extract_unique_ips(processed_events)
    
    # Enrich with threat intelligence
    threat_intelligence = {}
    for ip in unique_ips[:10]:  # Limit to avoid rate limiting
        ti_data = await dshield_client.get_ip_reputation(ip)
        threat_intelligence[ip] = ti_data
    
    # Generate attack report
    report = data_processor.generate_attack_report(processed_events, threat_intelligence)
    
    return summary, report, threat_intelligence

# Run analysis
summary, report, ti = asyncio.run(basic_analysis())
```

### IP-Specific Analysis

```python
async def analyze_specific_ips(ip_addresses):
    es_client = ElasticsearchClient()
    dshield_client = DShieldClient()
    
    await es_client.connect()
    
    # Query events for specific IPs
    events = await es_client.query_events_by_ip(ip_addresses, time_range_hours=24)
    
    # Enrich IPs with threat intelligence
    threat_intelligence = {}
    for ip in ip_addresses:
        ti_data = await dshield_client.get_ip_reputation(ip)
        threat_intelligence[ip] = ti_data
    
    return events, threat_intelligence

# Analyze specific IPs
ips = ["192.168.1.100", "10.0.0.50"]
events, ti = asyncio.run(analyze_specific_ips(ips))
```

### Real-time Monitoring

```python
import asyncio
import time
from src.elasticsearch_client import ElasticsearchClient
from src.data_processor import DataProcessor

async def monitor_security_events():
    es_client = ElasticsearchClient()
    data_processor = DataProcessor()
    
    await es_client.connect()
    
    while True:
        try:
            # Query recent events (last hour)
            events = await es_client.query_security_events(time_range_hours=1)
            
            if events:
                # Process and analyze
                processed_events = data_processor.process_security_events(events)
                summary = data_processor.generate_security_summary(processed_events)
                
                # Check for high-severity events
                high_severity = summary.get('events_by_severity', {}).get('high', 0)
                critical_severity = summary.get('events_by_severity', {}).get('critical', 0)
                
                if high_severity > 0 or critical_severity > 0:
                    print(f"ALERT: {high_severity} high and {critical_severity} critical events detected!")
                    
                    # Generate report for high-severity events
                    high_events = [e for e in processed_events 
                                 if e.get('severity') in ['high', 'critical']]
                    report = data_processor.generate_attack_report(high_events)
                    
                    print(f"Report: {report['title']}")
                    print(f"Impact: {report['impact_assessment']}")
            
            # Wait before next check
            await asyncio.sleep(300)  # 5 minutes
            
        except Exception as e:
            print(f"Error in monitoring: {e}")
            await asyncio.sleep(60)  # Wait 1 minute on error

# Start monitoring
asyncio.run(monitor_security_events())
```

## ChatGPT Integration Examples

### Example 1: Security Incident Analysis

**User**: "I have security events from my Elastic SIEM. Can you analyze them and provide recommendations?"

**Context Injection**: Use the `get_security_summary` tool to get recent events and inject the context.

**ChatGPT Response**: "Based on the security events from your SIEM, I can see:
- 15 high-severity events in the last 24 hours
- 3 unique source IPs with suspicious activity
- Potential brute force attack patterns
- 2 IPs with high threat intelligence scores

**Recommendations**:
1. Block the identified malicious IPs immediately
2. Implement multi-factor authentication
3. Review firewall rules for the affected systems
4. Conduct a full security audit..."

### Example 2: IP Reputation Analysis

**User**: "Can you check the reputation of IP address 192.168.1.100?"

**Tool Call**: Use the `enrich_ip_with_dshield` tool.

**ChatGPT Response**: "I've checked the reputation of 192.168.1.100 with DShield:
- Threat Level: HIGH
- Reputation Score: 85/100
- Country: Russia
- ASN: AS12345
- Organization: Suspicious ISP
- Attack Types: Port scanning, brute force

**Recommendation**: This IP should be blocked immediately as it has a high threat score and is associated with malicious activities."

### Example 3: Attack Report Generation

**User**: "Generate a detailed attack report for the security incident."

**Tool Call**: Use the `generate_attack_report` tool with recent events.

**ChatGPT Response**: "Here's your detailed attack report:

**Executive Summary**: A coordinated brute force attack was detected involving 3 source IPs targeting your authentication systems.

**Key Findings**:
- Total Events: 47
- Unique IPs: 3
- Attack Vectors: Brute force, reconnaissance
- Impact: HIGH - Multiple failed authentication attempts

**Threat Indicators**:
- IP 192.168.1.100: High threat score (85/100)
- IP 10.0.0.50: Medium threat score (65/100)

**Recommendations**:
1. Implement account lockout policies
2. Enable multi-factor authentication
3. Block the identified malicious IPs
4. Monitor for additional attack attempts..."

## Advanced Usage

### Custom Query Filters

```python
# Query with custom filters
filters = {
    "event.severity": "high",
    "source.ip": ["192.168.1.100", "10.0.0.50"],
    "event.category": "authentication"
}

events = await es_client.query_security_events(
    time_range_hours=24,
    filters=filters
)
```

### Batch IP Enrichment

```python
# Enrich multiple IPs efficiently
ip_addresses = ["192.168.1.100", "10.0.0.50", "172.16.0.25"]
threat_intelligence = await dshield_client.enrich_ips_batch(ip_addresses)
```

### Custom Context Formatting

```python
# Customize context format
context_injector = ContextInjector()
context_injector.context_format = "summary"  # or "structured", "raw"
context_injector.include_raw_data = False

context = context_injector.prepare_security_context(events, threat_intelligence)
```

## Troubleshooting

### Common Issues

1. **Elasticsearch Connection Failed**:
   - Check URL, username, and password
   - Verify SSL certificate settings
   - Ensure network connectivity

2. **DShield API Errors**:
   - Check API key validity
   - Verify rate limiting settings
   - Check network connectivity

3. **No Events Found**:
   - Verify index patterns in configuration
   - Check time range settings
   - Ensure events exist in the specified time period

4. **MCP Server Issues**:
   - Check port availability
   - Verify environment variables
   - Check log files for errors

### Debug Mode

Enable debug mode for detailed logging:

```bash
# Set debug mode in .env
MCP_SERVER_DEBUG=true
LOG_LEVEL=DEBUG
```

### Log Analysis

Check logs for troubleshooting:

```bash
# View recent logs
tail -f logs/dshield-mcp.log

# Search for errors
grep "ERROR" logs/dshield-mcp.log
```

## Security Considerations

1. **API Keys**: Store API keys securely in environment variables
2. **Network Security**: Use HTTPS for all API communications
3. **Rate Limiting**: Respect API rate limits to avoid service disruption
4. **Data Privacy**: Be careful with sensitive security data in ChatGPT conversations
5. **Access Control**: Limit access to the MCP server to authorized users

## Performance Optimization

1. **Caching**: Enable caching for threat intelligence data
2. **Batch Processing**: Use batch operations for multiple IPs
3. **Connection Pooling**: Reuse connections when possible
4. **Query Optimization**: Use specific time ranges and filters
5. **Resource Limits**: Set appropriate limits for query results

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the example code
3. Check the configuration validation
4. Enable debug logging for detailed error information 