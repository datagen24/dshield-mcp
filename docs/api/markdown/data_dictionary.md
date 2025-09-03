# data_dictionary

Data Dictionary for DShield MCP Elastic SIEM Integration.

This module provides comprehensive field descriptions, query examples, and
analysis guidelines to help AI models understand DShield SIEM data structures
and their meanings. It serves as a reference for data interpretation and
query construction.

Features:
- Comprehensive field descriptions and types
- Query examples for common use cases
- Data patterns and analysis guidelines
- Initial prompt generation for AI models
- Structured data reference for DShield SIEM

Example:
    >>> from src.data_dictionary import DataDictionary
    >>> fields = DataDictionary.get_field_descriptions()
    >>> examples = DataDictionary.get_query_examples()
    >>> prompt = DataDictionary.get_initial_prompt()

## DataDictionary

Comprehensive data dictionary for DShield SIEM data.

    This class provides static methods to access comprehensive information
    about DShield SIEM data structures, including field descriptions,
    query examples, data patterns, and analysis guidelines.

    The class serves as a central reference for understanding DShield
    data formats and constructing effective queries and analysis.

    Example:
        >>> fields = DataDictionary.get_field_descriptions()
        >>> examples = DataDictionary.get_query_examples()
        >>> prompt = DataDictionary.get_initial_prompt()

#### get_field_descriptions

```python
def get_field_descriptions()
```

Get comprehensive field descriptions for DShield data.

        Returns a detailed dictionary containing descriptions, types,
        examples, and usage information for all DShield SIEM fields.

        Returns:
            Dictionary containing field descriptions organized by category:
            - core_fields: Basic event fields (timestamp, id)
            - network_fields: Network-related fields (IPs, ports, protocols)
            - event_fields: Event classification fields (type, severity, category)
            - dshield_specific_fields: DShield-specific threat intelligence
            - geographic_fields: Geographic location data
            - service_fields: Service and application data

#### get_query_examples

```python
def get_query_examples()
```

Get example queries for common use cases.

        Returns a collection of example queries demonstrating how to
        use the DShield MCP tools for various security analysis scenarios.

        Returns:
            Dictionary containing query examples with descriptions,
            parameters, and expected fields for each use case

#### get_data_patterns

```python
def get_data_patterns()
```

Get common data patterns and their interpretations.

        Returns patterns that commonly appear in DShield data and
        their security implications for analysis.

        Returns:
            Dictionary containing data patterns with descriptions
            and security context

#### get_analysis_guidelines

```python
def get_analysis_guidelines()
```

Get guidelines for analyzing DShield SIEM data.

        Returns best practices and guidelines for interpreting
        and analyzing DShield security data effectively.

        Returns:
            Dictionary containing analysis guidelines and best practices

#### get_initial_prompt

```python
def get_initial_prompt()
```

Get the initial prompt for AI models.

        Generates a comprehensive initial prompt that provides AI models
        with all the necessary context about DShield SIEM data structures,
        field meanings, and analysis guidelines.

        Returns:
            String containing the complete initial prompt for AI models

#### _format_field_section

```python
def _format_field_section(fields)
```

Format field descriptions into a readable section.

        Args:
            fields: Dictionary containing field descriptions

        Returns:
            Formatted string representation of the field section

#### _format_query_examples

```python
def _format_query_examples(examples)
```

Format query examples into a readable section.

        Args:
            examples: Dictionary containing query examples

        Returns:
            Formatted string representation of the query examples section

#### _format_data_patterns

```python
def _format_data_patterns(patterns)
```

Format data patterns into a readable section.

        Args:
            patterns: Dictionary containing data patterns

        Returns:
            Formatted string representation of the data patterns section

#### _format_analysis_guidelines

```python
def _format_analysis_guidelines(guidelines)
```

Format analysis guidelines into a readable section.

        Args:
            guidelines: Dictionary containing analysis guidelines

        Returns:
            Formatted string representation of the analysis guidelines section

#### has_offline_threat_intel

```python
def has_offline_threat_intel()
```

Check if offline threat intelligence sources are available.

        Returns:
            bool: True if offline threat intelligence is available, False otherwise

#### get_threat_intelligence_data

```python
def get_threat_intelligence_data()
```

Get offline threat intelligence data.

        Returns:
            Dict[str, Any]: Dictionary containing offline threat intelligence data
