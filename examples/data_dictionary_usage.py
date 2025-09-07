#!/usr/bin/env python3
"""
Example usage of the DShield Data Dictionary functionality.

This demonstrates how the data dictionary helps models understand DShield data.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import json

from src.data_dictionary import DataDictionary


async def demonstrate_data_dictionary():
    """Demonstrate the data dictionary functionality."""
    print("=== DShield Data Dictionary Usage Example ===\n")

    # 1. Get the initial prompt for models
    print("1. Initial Prompt for Models:")
    print("=" * 50)
    prompt = DataDictionary.get_initial_prompt()
    print(f"Generated prompt ({len(prompt)} characters):")
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
    print("\n")

    # 2. Show field descriptions
    print("2. Field Descriptions:")
    print("=" * 50)
    field_descriptions = DataDictionary.get_field_descriptions()

    # Show a few key fields
    key_fields = ["source_ip", "reputation_score", "attack_count", "country"]
    for field in key_fields:
        for _category, fields in field_descriptions.items():
            if field in fields:
                field_info = fields[field]
                print(f"• {field}: {field_info['description']}")
                if 'examples' in field_info:
                    print(f"  Examples: {field_info['examples']}")
                print()
                break

    # 3. Show query examples
    print("3. Query Examples:")
    print("=" * 50)
    query_examples = DataDictionary.get_query_examples()
    for name, example in query_examples.items():
        print(f"• {name.replace('_', ' ').title()}:")
        print(f"  Description: {example['description']}")
        print(f"  Query Type: {example['query_type']}")
        print(f"  Parameters: {example['parameters']}")
        print()

    # 4. Show threat levels
    print("4. Threat Levels:")
    print("=" * 50)
    data_patterns = DataDictionary.get_data_patterns()
    threat_levels = data_patterns['threat_levels']
    for level, info in threat_levels.items():
        print(f"• {level.title()}:")
        print(f"  Reputation Score: {info['reputation_score']}")
        print(f"  Attack Count: {info['attack_count']}")
        print(f"  Description: {info['description']}")
        print()

    # 5. Show correlation rules
    print("5. Correlation Rules:")
    print("=" * 50)
    analysis_guidelines = DataDictionary.get_analysis_guidelines()
    correlation_rules = analysis_guidelines['correlation_rules']
    for rule_name, rule_info in correlation_rules.items():
        print(f"• {rule_name.replace('_', ' ').title()}:")
        print(f"  Description: {rule_info['description']}")
        print(f"  Action: {rule_info['action']}")
        if 'threshold' in rule_info:
            print(f"  Threshold: {rule_info['threshold']}")
        print()

    # 6. Demonstrate how this helps with analysis
    print("6. How This Helps with Analysis:")
    print("=" * 50)
    print("With this data dictionary, models can:")
    print("• Understand what each field means and how to use it")
    print("• Know the expected data types and value ranges")
    print("• Follow established query patterns for common use cases")
    print("• Apply appropriate threat levels and response priorities")
    print("• Correlate events using defined rules")
    print("• Generate meaningful security insights")
    print()

    # 7. Show JSON format for programmatic access
    print("7. JSON Format (for programmatic access):")
    print("=" * 50)
    json_data = {
        "field_descriptions": DataDictionary.get_field_descriptions(),
        "query_examples": DataDictionary.get_query_examples(),
        "data_patterns": DataDictionary.get_data_patterns(),
        "analysis_guidelines": DataDictionary.get_analysis_guidelines(),
    }
    print(
        f"Complete data dictionary available in JSON format "
        f"({len(json.dumps(json_data))} characters)"
    )
    print("This can be used by applications to build dynamic queries and analysis tools.")
    print()


def show_usage_scenarios():
    """Show practical usage scenarios."""
    print("=== Practical Usage Scenarios ===\n")

    scenarios = [
        {
            "title": "Model Initialization",
            "description": "When a model first connects to the DShield MCP server, it receives "
            "the data dictionary as part of the initialization, helping it understand the "
            "available data structure.",
            "benefit": "Reduces trial and error in query formulation",
        },
        {
            "title": "Dynamic Query Building",
            "description": "Applications can use the JSON format to dynamically build queries "
            "based on available fields and patterns.",
            "benefit": "Enables intelligent query construction",
        },
        {
            "title": "Threat Analysis",
            "description": "Analysts can use the correlation rules and threat levels to "
            "prioritize investigations and responses.",
            "benefit": "Standardizes threat assessment and response",
        },
        {
            "title": "Training and Documentation",
            "description": "The data dictionary serves as comprehensive documentation for new "
            "team members and automated systems.",
            "benefit": "Accelerates onboarding and reduces errors",
        },
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"{i}. {scenario['title']}:")
        print(f"   {scenario['description']}")
        print(f"   Benefit: {scenario['benefit']}")
        print()


if __name__ == "__main__":
    asyncio.run(demonstrate_data_dictionary())
    show_usage_scenarios()
