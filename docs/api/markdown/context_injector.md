# context_injector

Context injector for preparing data for ChatGPT context injection.

This module provides utilities for preparing and formatting security data
for injection into ChatGPT conversations. It handles various data types
including security events, threat intelligence, attack reports, and query
results, formatting them appropriately for AI consumption.

Features:
- Security context preparation and formatting
- Attack report context injection
- Query result formatting
- MCP-compatible context injection
- Multiple output formats (structured, summary, raw)
- ChatGPT-optimized formatting

Example:
    >>> from src.context_injector import ContextInjector
    >>> injector = ContextInjector()
    >>> context = injector.prepare_security_context(events, threat_intel)
    >>> formatted = injector.inject_context_for_chatgpt(context)

## ContextInjector

Prepare and inject security context for ChatGPT analysis.

    This class provides methods to prepare and format various types of
    security data for injection into ChatGPT conversations. It supports
    multiple output formats and optimizes data for AI consumption.

    Attributes:
        max_context_size: Maximum context size in characters
        include_raw_data: Whether to include raw data in context
        context_format: Output format (structured, summary, or raw)

    Example:
        >>> injector = ContextInjector()
        >>> context = injector.prepare_security_context(events)
        >>> formatted = injector.inject_context_for_chatgpt(context)

#### __init__

```python
def __init__(self)
```

Initialize the ContextInjector.

        Loads configuration from environment variables for context
        formatting preferences and size limits.

#### prepare_security_context

```python
def prepare_security_context(self, events, threat_intelligence, summary)
```

Prepare security context for injection.

        Creates a comprehensive security context from events, threat
        intelligence, and summary data, formatted according to the
        configured context format preference.

        Args:
            events: List of security event dictionaries
            threat_intelligence: Optional threat intelligence data
            summary: Optional summary data

        Returns:
            Dictionary containing formatted security context

#### prepare_attack_report_context

```python
def prepare_attack_report_context(self, report)
```

Prepare attack report context for injection.

        Formats an attack report for injection into ChatGPT conversations,
        including metadata and confidence information.

        Args:
            report: Attack report dictionary

        Returns:
            Dictionary containing formatted attack report context

#### prepare_query_context

```python
def prepare_query_context(self, query_type, parameters, results)
```

Prepare query context for injection.

        Formats query results and parameters for injection into ChatGPT
        conversations, including metadata about the query execution.

        Args:
            query_type: Type of query that was executed
            parameters: Query parameters that were used
            results: Query results to format

        Returns:
            Dictionary containing formatted query context

#### inject_context_for_chatgpt

```python
def inject_context_for_chatgpt(self, context)
```

Format context for ChatGPT consumption.

        Converts a context dictionary into a string format optimized
        for ChatGPT consumption, handling different context types
        appropriately.

        Args:
            context: Context dictionary to format

        Returns:
            String formatted for ChatGPT consumption

#### create_mcp_context_injection

```python
def create_mcp_context_injection(self, context)
```

Create MCP-compatible context injection.

        Formats context data for use with the Model Context Protocol (MCP),
        including proper metadata and version information.

        Args:
            context: Context dictionary to format

        Returns:
            Dictionary formatted for MCP protocol

#### _structure_events

```python
def _structure_events(self, events)
```

Structure events for better analysis.

        Converts raw event data into a structured format optimized
        for analysis, organizing network information and metadata.

        Args:
            events: List of raw event dictionaries

        Returns:
            List of structured event dictionaries

#### _summarize_events

```python
def _summarize_events(self, events)
```

Create a summary of events instead of full details.

        Generates a summary of events including counts by severity,
        category, and unique IP addresses for efficient context injection.

        Args:
            events: List of event dictionaries to summarize

        Returns:
            Dictionary containing event summary

#### _clean_events

```python
def _clean_events(self, events)
```

Clean events by removing sensitive or unnecessary data.

        Removes sensitive fields and unnecessary metadata from events
        while preserving essential information for analysis.

        Args:
            events: List of event dictionaries to clean

        Returns:
            List of cleaned event dictionaries

#### _process_threat_intelligence

```python
def _process_threat_intelligence(self, threat_intelligence)
```

Process threat intelligence data for context injection.

        Formats threat intelligence data for inclusion in context,
        organizing it by IP address and threat level.

        Args:
            threat_intelligence: Raw threat intelligence data

        Returns:
            Processed threat intelligence dictionary

#### _generate_metadata

```python
def _generate_metadata(self, events, threat_intelligence)
```

Generate metadata for the context.

        Creates metadata including time ranges, data sources, and
        processing information for the context.

        Args:
            events: List of events to analyze
            threat_intelligence: Optional threat intelligence data

        Returns:
            Dictionary containing context metadata

#### _generate_analysis_hints

```python
def _generate_analysis_hints(self, events, threat_intelligence)
```

Generate analysis hints for ChatGPT.

        Creates a list of analysis hints and suggestions based on
        the events and threat intelligence data.

        Args:
            events: List of events to analyze
            threat_intelligence: Optional threat intelligence data

        Returns:
            List of analysis hints and suggestions

#### _format_attack_report

```python
def _format_attack_report(self, report)
```

Format attack report for context injection.

        Formats an attack report for inclusion in context, organizing
        it into sections for executive summary, details, and recommendations.

        Args:
            report: Raw attack report dictionary

        Returns:
            Formatted attack report dictionary

#### _format_query_results

```python
def _format_query_results(self, results)
```

Format query results for context injection.

        Formats query results for inclusion in context, ensuring
        they are properly structured and readable.

        Args:
            results: Raw query results list

        Returns:
            Formatted query results list

#### _format_security_context_for_chatgpt

```python
def _format_security_context_for_chatgpt(self, data)
```

Format security context specifically for ChatGPT.

        Converts security context data into a text format optimized
        for ChatGPT consumption, including structured sections and
        analysis guidance.

        Args:
            data: Security context data dictionary

        Returns:
            String formatted for ChatGPT consumption

#### _format_attack_report_for_chatgpt

```python
def _format_attack_report_for_chatgpt(self, data)
```

Format attack report specifically for ChatGPT.

        Converts attack report data into a text format optimized
        for ChatGPT consumption, including executive summary and
        detailed analysis sections.

        Args:
            data: Attack report data dictionary

        Returns:
            String formatted for ChatGPT consumption

#### _format_query_results_for_chatgpt

```python
def _format_query_results_for_chatgpt(self, data)
```

Format query results specifically for ChatGPT.

        Converts query results data into a text format optimized
        for ChatGPT consumption, including query parameters and
        result summaries.

        Args:
            data: Query results data dictionary

        Returns:
            String formatted for ChatGPT consumption

#### _extract_time_range

```python
def _extract_time_range(self, events)
```

Extract time range from events.

        Determines the earliest and latest timestamps from a list
        of events to establish the time range.

        Args:
            events: List of event dictionaries

        Returns:
            Dictionary with 'start' and 'end' timestamps

#### _extract_data_sources

```python
def _extract_data_sources(self, events)
```

Extract data sources from events.

        Identifies the unique data sources (indices) from which
        the events were retrieved.

        Args:
            events: List of event dictionaries

        Returns:
            List of unique data source names

#### _detect_attack_patterns

```python
def _detect_attack_patterns(self, events)
```

Detect attack patterns in events.

        Analyzes events to identify common attack patterns and
        their frequencies.

        Args:
            events: List of event dictionaries

        Returns:
            Dictionary mapping attack patterns to their counts
