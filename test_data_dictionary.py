#!/usr/bin/env python3
"""
Test script for the DShield Data Dictionary functionality.
"""

import asyncio
import json
from src.data_dictionary import DataDictionary


async def test_data_dictionary():
    """Test the data dictionary functionality."""
    print("=== Testing DShield Data Dictionary ===\n")
    
    # Test field descriptions
    print("1. Testing field descriptions...")
    field_descriptions = DataDictionary.get_field_descriptions()
    print(f"   - Found {len(field_descriptions)} field categories")
    for category, fields in field_descriptions.items():
        print(f"   - {category}: {len(fields)} fields")
    print()
    
    # Test query examples
    print("2. Testing query examples...")
    query_examples = DataDictionary.get_query_examples()
    print(f"   - Found {len(query_examples)} query examples")
    for name, example in query_examples.items():
        print(f"   - {name}: {example['description']}")
    print()
    
    # Test data patterns
    print("3. Testing data patterns...")
    data_patterns = DataDictionary.get_data_patterns()
    print(f"   - Attack patterns: {len(data_patterns['attack_patterns'])}")
    print(f"   - Threat levels: {len(data_patterns['threat_levels'])}")
    print(f"   - Time patterns: {len(data_patterns['time_patterns'])}")
    print()
    
    # Test analysis guidelines
    print("4. Testing analysis guidelines...")
    analysis_guidelines = DataDictionary.get_analysis_guidelines()
    print(f"   - Correlation rules: {len(analysis_guidelines['correlation_rules'])}")
    print(f"   - Response priorities: {len(analysis_guidelines['response_priorities'])}")
    print()
    
    # Test initial prompt
    print("5. Testing initial prompt generation...")
    prompt = DataDictionary.get_initial_prompt()
    print(f"   - Prompt length: {len(prompt)} characters")
    print(f"   - Contains field descriptions: {'Available Fields' in prompt}")
    print(f"   - Contains query examples: {'Common Query Patterns' in prompt}")
    print(f"   - Contains data patterns: {'Data Patterns and Threat Levels' in prompt}")
    print(f"   - Contains analysis guidelines: {'Analysis Guidelines' in prompt}")
    print()
    
    # Test JSON format
    print("6. Testing JSON format...")
    data = {
        "field_descriptions": DataDictionary.get_field_descriptions(),
        "query_examples": DataDictionary.get_query_examples(),
        "data_patterns": DataDictionary.get_data_patterns(),
        "analysis_guidelines": DataDictionary.get_analysis_guidelines()
    }
    json_str = json.dumps(data, indent=2, default=str)
    print(f"   - JSON length: {len(json_str)} characters")
    print(f"   - Valid JSON: {json.loads(json_str) is not None}")
    print()
    
    print("=== Data Dictionary Tests Completed Successfully ===")


if __name__ == "__main__":
    asyncio.run(test_data_dictionary()) 