# Implementation Plan for Issue #11: Enhanced Template/Preset Queries System

## Project: dshield-mcp
## Issue: #11 - Enhanced Template/Preset Queries System
## Status: Ready for Implementation
## Estimated Timeline: 4 weeks

---

## Overview

This implementation plan addresses the need for **Template/Preset Queries** (Enhancement #7 from the roadmap), providing pre-built queries for common security analysis patterns. This enhancement will significantly improve the usability of the DShield MCP server by offering ready-to-use templates for typical threat hunting and security analysis scenarios.

## Background

The DShield MCP project currently provides powerful raw query capabilities but lacks convenient preset queries for common security analysis tasks. Based on the project's enhancement roadmap and current capabilities, implementing a robust template system will:

- Reduce time-to-insight for security analysts
- Standardize common query patterns
- Provide consistent analysis methodologies  
- Enable automated threat hunting workflows

## Implementation Phases

### **Phase 1: Core Template System (Week 1-2)**

#### 1.1 Template Engine Infrastructure
**File:** `src/query_templates.py`

**Key Components:**
- Template definition schema with JSON validation
- Parameter validation and substitution engine
- Template registration and discovery system
- Comprehensive error handling for invalid templates
- Support for nested parameter references
- Template versioning system

**Core Classes:**
```python
class QueryTemplate:
    """Represents a single query template with metadata and execution logic"""
    
class TemplateEngine:
    """Manages template loading, validation, and execution"""
    
class TemplateRegistry:
    """Central registry for all available templates"""
```

#### 1.2 Template Configuration System  
**Directory:** `templates/`

**Initial Templates:**
- `ssh_brute_force_analysis.json` - Detect SSH brute force patterns
- `port_scan_analysis.json` - Analyze port scanning activity
- `campaign_analysis.json` - Correlate attack campaigns using IOCs
- `malware_activity_analysis.json` - Identify malware-related events
- `geographic_threat_analysis.json` - Geographic attack distribution
- `web_attack_analysis.json` - HTTP/web-based attack detection
- `dns_tunneling_analysis.json` - DNS-based exfiltration detection

#### 1.3 MCP Integration
**New MCP Tools:**
```python
@mcp_tool("list_query_templates")
def list_query_templates() -> List[dict]:
    """List all available query templates with descriptions"""

@mcp_tool("execute_template_query") 
def execute_template_query(template_name: str, parameters: dict = None) -> dict:
    """Execute a template with custom parameters"""

@mcp_tool("get_template_info")
def get_template_info(template_name: str) -> dict:
    """Get detailed template information and parameter schema"""

@mcp_tool("validate_template_parameters")
def validate_template_parameters(template_name: str, parameters: dict) -> dict:
    """Validate parameters before template execution"""
```

### **Phase 2: Template Implementation (Week 2-3)**

#### 2.1 SSH Brute Force Analysis Template
```json
{
  "name": "ssh_brute_force_analysis",
  "description": "Detect SSH brute force attacks based on failed login patterns",
  "version": "1.0",
  "category": "authentication",
  "parameters": {
    "time_range_hours": {
      "type": "integer",
      "default": 24,
      "description": "Time range in hours to analyze",
      "min": 1,
      "max": 168
    },
    "source_ip": {
      "type": "string", 
      "optional": true,
      "description": "Specific source IP to analyze"
    },
    "min_attempts": {
      "type": "integer",
      "default": 10,
      "description": "Minimum failed attempts to consider brute force"
    },
    "exclude_internal": {
      "type": "boolean",
      "default": true,
      "description": "Exclude internal IP ranges"
    }
  },
  "query": {
    "bool": {
      "must": [
        {"match": {"event.action": "ssh_login_failed"}},
        {"range": {"@timestamp": "{{time_range}}"}}
      ],
      "must_not": "{{internal_networks}}"
    }
  },
  "aggregations": {
    "by_source": {
      "terms": {"field": "source.ip", "size": 50},
      "aggs": {
        "attempt_count": {"value_count": {"field": "@timestamp"}},
        "target_hosts": {"cardinality": {"field": "destination.ip"}},
        "time_span": {
          "date_range": {
            "field": "@timestamp",
            "ranges": [{"from": "now-{{time_range_hours}}h", "to": "now"}]
          }
        }
      }
    }
  },
  "output_format": {
    "summary": true,
    "detailed_events": false,
    "visualization_data": true
  }
}
```

#### 2.2 Port Scan Analysis Template
```json
{
  "name": "port_scan_analysis", 
  "description": "Analyze port scanning activity patterns",
  "version": "1.0",
  "category": "reconnaissance",
  "parameters": {
    "source_ip": {
      "type": "string",
      "required": true,
      "description": "Source IP to analyze for scanning activity"
    },
    "time_range_hours": {
      "type": "integer", 
      "default": 24,
      "description": "Time range in hours"
    },
    "min_ports": {
      "type": "integer",
      "default": 10, 
      "description": "Minimum ports accessed to consider scanning"
    },
    "scan_types": {
      "type": "array",
      "default": ["tcp_syn", "tcp_connect", "udp"],
      "description": "Types of scans to include"
    }
  }
}
```

#### 2.3 Campaign Analysis Template
```json
{
  "name": "campaign_analysis",
  "description": "Correlate events based on IOCs and attack patterns", 
  "version": "1.0",
  "category": "threat_hunting",
  "parameters": {
    "indicators": {
      "type": "array",
      "required": true,
      "description": "List of IOCs (IPs, hashes, domains)"
    },
    "time_range_hours": {
      "type": "integer",
      "default": 72,
      "description": "Time window for correlation"
    },
    "correlation_fields": {
      "type": "array", 
      "default": ["source.ip", "user_agent.original", "http.request.method"],
      "description": "Fields to use for event correlation"
    }
  }
}
```

### **Phase 3: Advanced Features (Week 3-4)**

#### 3.1 Template Customization Engine
**File:** `src/template_customizer.py`

**Features:**
- Dynamic parameter validation with type checking
- Field mapping for different data sources
- Custom aggregation builder
- Result formatting and transformation
- Template inheritance and composition
- Custom filter builders

#### 3.2 Template Caching System
**File:** `src/template_cache.py`

**Features:**
- Intelligent template result caching based on parameters
- Cache invalidation strategies (time-based, data-based)
- Cache warming for frequently used templates
- Memory and disk-based caching options
- Cache performance metrics

#### 3.3 Template Analytics & Optimization
**File:** `src/template_analytics.py`

**Features:**
- Template usage statistics
- Performance monitoring and optimization
- Query plan analysis
- Automatic parameter tuning suggestions
- Template effectiveness scoring

### **Phase 4: Testing & Documentation (Week 4)**

#### 4.1 Comprehensive Test Suite
**File:** `tests/test_query_templates.py`

**Test Coverage:**
- Template loading and validation (100%)
- Parameter substitution and validation (100%)
- Query execution across all templates (100%)
- Error handling and edge cases (100%)
- Performance benchmarks
- Integration tests with MCP server
- Cache behavior validation

#### 4.2 Documentation Package
**Files:**
- `docs/QUERY_TEMPLATES.md` - Complete template usage guide
- `docs/TEMPLATE_DEVELOPMENT.md` - Custom template creation guide
- `docs/TEMPLATE_API.md` - API reference for template system
- Update `README.md` with template examples and quick start
- Update `docs/USAGE.md` with comprehensive MCP tool documentation

#### 4.3 Example Scripts and Demos
**Files:**
- `examples/template_usage.py` - Basic template usage examples
- `examples/advanced_template_scenarios.py` - Complex analysis scenarios
- `examples/custom_template_development.py` - Template creation examples
- `examples/template_performance_testing.py` - Performance testing utilities

## Technical Implementation Details

### Core Template Schema
```json
{
  "name": "string",
  "description": "string", 
  "version": "string",
  "category": "string",
  "author": "string",
  "created": "iso_datetime",
  "updated": "iso_datetime",
  "parameters": {
    "param_name": {
      "type": "string|integer|boolean|array|object",
      "required": "boolean",
      "default": "any",
      "description": "string",
      "validation": "object"
    }
  },
  "query": "elasticsearch_query_object",
  "aggregations": "elasticsearch_aggregations_object", 
  "post_processing": "array_of_processing_steps",
  "output_format": "formatting_specification"
}
```

### MCP Server Integration Points
**File:** `mcp_server.py` (modifications)

```python
# Add template tools to MCP server
async def handle_list_query_templates():
    """Handle template listing requests"""
    
async def handle_execute_template_query():
    """Handle template execution requests"""
    
async def handle_get_template_info():
    """Handle template information requests"""
```

### Configuration Updates
**File:** `config.py` (additions)

```python
class TemplateConfig:
    """Template system configuration"""
    TEMPLATE_DIRECTORY = "templates/"
    CACHE_ENABLED = True
    CACHE_TTL_SECONDS = 3600
    MAX_TEMPLATE_EXECUTION_TIME = 300
    ENABLE_TEMPLATE_ANALYTICS = True
```

## Success Metrics

### Functional Requirements
- [ ] **Template System**: 7+ working templates covering major attack categories
- [ ] **MCP Integration**: All template tools fully functional via MCP protocol
- [ ] **Parameter Validation**: Comprehensive validation with helpful error messages
- [ ] **Caching**: Template result caching with configurable TTL
- [ ] **Performance**: Template execution within 30 seconds for typical queries
- [ ] **Documentation**: Complete documentation with examples and tutorials

### Quality Requirements  
- [ ] **Test Coverage**: 100% test coverage for template engine
- [ ] **Error Handling**: Graceful handling of all error conditions
- [ ] **Logging**: Comprehensive logging for debugging and monitoring
- [ ] **Backwards Compatibility**: No breaking changes to existing functionality
- [ ] **Security**: Template parameter sanitization and validation

### Performance Requirements
- [ ] **Template Loading**: Templates load in <100ms
- [ ] **Query Execution**: Most templates execute in <30 seconds
- [ ] **Memory Usage**: Template system uses <50MB additional memory
- [ ] **Caching**: Cache hit ratio >80% for repeated queries

## File Structure Changes

### New Files Created
```
src/
├── query_templates.py         # Core template engine
├── template_customizer.py     # Template customization
├── template_cache.py          # Caching system
├── template_analytics.py      # Analytics and optimization
└── template_validators.py     # Parameter validation

templates/
├── ssh_brute_force_analysis.json
├── port_scan_analysis.json
├── campaign_analysis.json
├── malware_activity_analysis.json
├── geographic_threat_analysis.json
├── web_attack_analysis.json
└── dns_tunneling_analysis.json

tests/
├── test_query_templates.py    # Template system tests
├── test_template_cache.py     # Cache testing
└── test_template_integration.py # Integration tests

examples/
├── template_usage.py          # Basic usage examples
├── advanced_template_scenarios.py # Complex scenarios
├── custom_template_development.py # Development guide
└── template_performance_testing.py # Performance testing

docs/
├── QUERY_TEMPLATES.md         # User guide
├── TEMPLATE_DEVELOPMENT.md    # Developer guide
└── TEMPLATE_API.md           # API reference
```

### Modified Files
```
mcp_server.py                  # Add template MCP tools
config.py                      # Add template configuration
README.md                      # Add template documentation section
docs/USAGE.md                  # Add template usage examples
requirements.txt               # Add template dependencies if needed
```

## Dependencies and Requirements

### New Dependencies
- `jsonschema>=4.0.0` - Template validation
- `jinja2>=3.0.0` - Template parameter substitution (if needed)

### System Requirements
- Python 3.8+ (existing requirement)
- Elasticsearch 7.0+ (existing requirement) 
- Sufficient memory for template caching (configurable)

## Risk Assessment and Mitigation

### Technical Risks
1. **Template Performance**: Large result sets may impact performance
   - *Mitigation*: Implement result size limits and streaming
   
2. **Parameter Injection**: Malicious parameter values could affect queries
   - *Mitigation*: Comprehensive parameter validation and sanitization
   
3. **Cache Memory Usage**: Template caching may consume significant memory
   - *Mitigation*: Configurable cache limits and LRU eviction

### Implementation Risks
1. **Scope Creep**: Template system may become overly complex
   - *Mitigation*: Focus on core functionality first, iterate incrementally
   
2. **Backwards Compatibility**: Changes might break existing functionality
   - *Mitigation*: Comprehensive testing and gradual rollout

## Future Enhancements

### Phase 2 Enhancements (Post-Issue #11)
- **Template Marketplace**: Community-contributed templates
- **Visual Template Builder**: GUI for non-technical users
- **Template Scheduling**: Automated execution with alerts
- **Machine Learning Integration**: ML-powered template recommendations
- **Template Versioning**: Advanced version control and rollback
- **Cross-Platform Templates**: Templates for multiple SIEM platforms

## Conclusion

This implementation plan provides a comprehensive roadmap for implementing the Enhanced Template/Preset Queries system for the dshield-mcp project. The phased approach ensures steady progress while maintaining code quality and system stability. The template system will significantly enhance the project's usability and provide a foundation for advanced threat hunting capabilities.

---

**Implementation Status**: Ready to begin  
**Next Steps**: 
1. Review and approve implementation plan
2. Set up development branch
3. Begin Phase 1 implementation
4. Establish testing framework
5. Create initial template prototypes

**Contact**: Implementation team ready to proceed with development upon approval.