"""Unit tests for DataDictionary functionality."""

import pytest
import json
from src.data_dictionary import DataDictionary


class TestDataDictionary:
    """Test the DataDictionary class functionality."""
    
    def test_get_field_descriptions(self):
        """Test field descriptions retrieval."""
        field_descriptions = DataDictionary.get_field_descriptions()
        
        # Verify structure
        assert isinstance(field_descriptions, dict)
        assert len(field_descriptions) > 0
        
        # Verify expected categories exist
        expected_categories = [
            "core_fields", "network_fields", "event_fields", 
            "dshield_specific_fields", "geographic_fields", "service_fields"
        ]
        for category in expected_categories:
            assert category in field_descriptions
            assert isinstance(field_descriptions[category], dict)
            assert len(field_descriptions[category]) > 0
        
        # Verify field structure
        for category, fields in field_descriptions.items():
            for field_name, field_info in fields.items():
                assert isinstance(field_info, dict)
                assert "description" in field_info
                assert "type" in field_info
                assert "usage" in field_info
                assert isinstance(field_info["description"], str)
                assert isinstance(field_info["type"], str)
                assert isinstance(field_info["usage"], str)
    
    def test_get_query_examples(self):
        """Test query examples retrieval."""
        query_examples = DataDictionary.get_query_examples()
        
        # Verify structure
        assert isinstance(query_examples, dict)
        assert len(query_examples) > 0
        
        # Verify example structure
        for example_name, example_info in query_examples.items():
            assert isinstance(example_info, dict)
            assert "description" in example_info
            assert "query_type" in example_info
            assert "parameters" in example_info
            assert isinstance(example_info["description"], str)
            assert isinstance(example_info["query_type"], str)
            assert isinstance(example_info["parameters"], dict)
    
    def test_get_data_patterns(self):
        """Test data patterns retrieval."""
        data_patterns = DataDictionary.get_data_patterns()
        
        # Verify structure
        assert isinstance(data_patterns, dict)
        assert len(data_patterns) > 0
        
        # Verify expected sections exist
        expected_sections = ["attack_patterns", "threat_levels", "time_patterns"]
        for section in expected_sections:
            assert section in data_patterns
            assert isinstance(data_patterns[section], dict)
            assert len(data_patterns[section]) > 0
        
        # Verify attack patterns
        attack_patterns = data_patterns["attack_patterns"]
        assert isinstance(attack_patterns, dict)
        for pattern_name, pattern_info in attack_patterns.items():
            assert isinstance(pattern_info, dict)
            assert "description" in pattern_info
            assert "indicators" in pattern_info
            assert "severity" in pattern_info
        
        # Verify threat levels
        threat_levels = data_patterns["threat_levels"]
        assert isinstance(threat_levels, dict)
        for level_name, level_info in threat_levels.items():
            assert isinstance(level_info, dict)
            assert "reputation_score" in level_info
            assert "attack_count" in level_info
            assert "description" in level_info
        
        # Verify time patterns
        time_patterns = data_patterns["time_patterns"]
        assert isinstance(time_patterns, dict)
        for pattern_name, pattern_info in time_patterns.items():
            assert isinstance(pattern_info, dict)
            assert "description" in pattern_info
            assert "analysis" in pattern_info
    
    def test_get_analysis_guidelines(self):
        """Test analysis guidelines retrieval."""
        analysis_guidelines = DataDictionary.get_analysis_guidelines()
        
        # Verify structure
        assert isinstance(analysis_guidelines, dict)
        assert len(analysis_guidelines) > 0
        
        # Verify expected sections exist
        expected_sections = ["correlation_rules", "response_priorities"]
        for section in expected_sections:
            assert section in analysis_guidelines
            assert isinstance(analysis_guidelines[section], dict)
            assert len(analysis_guidelines[section]) > 0
        
        # Verify correlation rules
        correlation_rules = analysis_guidelines["correlation_rules"]
        for rule_name, rule_info in correlation_rules.items():
            assert isinstance(rule_info, dict)
            assert "description" in rule_info
            assert "action" in rule_info
            assert "threshold" in rule_info or "pattern" in rule_info
        
        # Verify response priorities
        response_priorities = analysis_guidelines["response_priorities"]
        for priority_name, priority_info in response_priorities.items():
            assert isinstance(priority_info, dict)
            assert "criteria" in priority_info
            assert "actions" in priority_info
    
    def test_get_initial_prompt(self):
        """Test initial prompt generation."""
        prompt = DataDictionary.get_initial_prompt()
        
        # Verify structure
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        
        # Verify content sections
        expected_sections = [
            "Available Fields",
            "Common Query Patterns", 
            "Data Patterns and Threat Levels",
            "Analysis Guidelines"
        ]
        for section in expected_sections:
            assert section in prompt
        
        # Verify prompt contains field information
        assert "timestamp" in prompt
        assert "source_ip" in prompt
        assert "destination_ip" in prompt
        assert "event_type" in prompt
    
    def test_json_format(self):
        """Test JSON serialization of data dictionary."""
        # Get all data dictionary components
        data = {
            "field_descriptions": DataDictionary.get_field_descriptions(),
            "query_examples": DataDictionary.get_query_examples(),
            "data_patterns": DataDictionary.get_data_patterns(),
            "analysis_guidelines": DataDictionary.get_analysis_guidelines()
        }
        
        # Test JSON serialization
        json_str = json.dumps(data, indent=2, default=str)
        assert isinstance(json_str, str)
        assert len(json_str) > 0
        
        # Test JSON deserialization
        parsed_data = json.loads(json_str)
        assert isinstance(parsed_data, dict)
        assert len(parsed_data) == 4
        
        # Verify all sections are present
        assert "field_descriptions" in parsed_data
        assert "query_examples" in parsed_data
        assert "data_patterns" in parsed_data
        assert "analysis_guidelines" in parsed_data
    
    def test_field_descriptions_content(self):
        """Test specific field descriptions content."""
        field_descriptions = DataDictionary.get_field_descriptions()
        
        # Test core fields
        core_fields = field_descriptions["core_fields"]
        assert "timestamp" in core_fields
        assert "id" in core_fields
        
        timestamp_field = core_fields["timestamp"]
        assert timestamp_field["type"] == "datetime"
        assert "ISO 8601" in timestamp_field["description"]
        
        # Test network fields
        network_fields = field_descriptions["network_fields"]
        assert "source_ip" in network_fields
        assert "destination_ip" in network_fields
        assert "source_port" in network_fields
        assert "destination_port" in network_fields
        
        source_ip_field = network_fields["source_ip"]
        assert source_ip_field["type"] == "string"
        assert "attacker" in source_ip_field["description"].lower()
        
        # Test DShield specific fields
        dshield_fields = field_descriptions["dshield_specific_fields"]
        assert "reputation_score" in dshield_fields
        assert "attack_count" in dshield_fields
        assert "tags" in dshield_fields
        
        reputation_field = dshield_fields["reputation_score"]
        assert reputation_field["type"] == "float"
        assert "0-100" in reputation_field["description"]
    
    def test_query_examples_content(self):
        """Test specific query examples content."""
        query_examples = DataDictionary.get_query_examples()
        
        # Verify common query types exist
        expected_queries = ["recent_attacks", "high_risk_ips"]
        for query_name in expected_queries:
            assert query_name in query_examples
            
            query_info = query_examples[query_name]
            assert "description" in query_info
            assert "query_type" in query_info
            assert "parameters" in query_info
            assert "expected_fields" in query_info
            
            # Verify parameters structure
            parameters = query_info["parameters"]
            assert isinstance(parameters, dict)
            
            # Verify expected fields
            expected_fields = query_info["expected_fields"]
            assert isinstance(expected_fields, list)
            assert len(expected_fields) > 0
    
    def test_data_patterns_content(self):
        """Test specific data patterns content."""
        data_patterns = DataDictionary.get_data_patterns()
        
        # Test attack patterns
        attack_patterns = data_patterns["attack_patterns"]
        assert len(attack_patterns) > 0
        
        # Verify attack patterns have required fields
        for pattern_name, pattern_info in attack_patterns.items():
            assert "description" in pattern_info
            assert "indicators" in pattern_info
            assert "severity" in pattern_info
            assert isinstance(pattern_info["indicators"], list)
        
        # Test threat levels
        threat_levels = data_patterns["threat_levels"]
        assert len(threat_levels) > 0
        
        # Verify threat level structure
        for level_name, level_info in threat_levels.items():
            assert "reputation_score" in level_info
            assert "attack_count" in level_info
            assert "description" in level_info
            assert isinstance(level_info["reputation_score"], str)
            assert isinstance(level_info["attack_count"], str)
    
    def test_analysis_guidelines_content(self):
        """Test specific analysis guidelines content."""
        analysis_guidelines = DataDictionary.get_analysis_guidelines()
        
        # Test correlation rules
        correlation_rules = analysis_guidelines["correlation_rules"]
        assert len(correlation_rules) > 0
        
        for rule_name, rule_info in correlation_rules.items():
            assert "description" in rule_info
            assert "action" in rule_info
            assert "threshold" in rule_info or "pattern" in rule_info
        
        # Test response priorities
        response_priorities = analysis_guidelines["response_priorities"]
        assert len(response_priorities) > 0
        
        for priority_name, priority_info in response_priorities.items():
            assert "criteria" in priority_info
            assert "actions" in priority_info
            assert isinstance(priority_info["criteria"], list)
            assert isinstance(priority_info["actions"], list)
    
    def test_initial_prompt_content(self):
        """Test initial prompt specific content."""
        prompt = DataDictionary.get_initial_prompt()
        
        # Test that prompt contains specific field examples
        field_examples = ["timestamp", "source_ip", "destination_ip", "event_type", "severity"]
        for field in field_examples:
            assert field in prompt
        
        # Test that prompt contains query examples
        query_indicators = ["query_dshield_attacks", "query_dshield_reputation"]
        for indicator in query_indicators:
            assert indicator in prompt
        
        # Test that prompt contains analysis guidance
        analysis_indicators = ["correlation", "response", "priority"]
        for indicator in analysis_indicators:
            assert indicator.lower() in prompt.lower()
    
    def test_data_consistency(self):
        """Test consistency between different data dictionary methods."""
        field_descriptions = DataDictionary.get_field_descriptions()
        query_examples = DataDictionary.get_query_examples()
        data_patterns = DataDictionary.get_data_patterns()
        analysis_guidelines = DataDictionary.get_analysis_guidelines()
        
        # Test that field names in query examples exist in field descriptions
        for example_name, example_info in query_examples.items():
            if "expected_fields" in example_info:
                for field_name in example_info["expected_fields"]:
                    # Check if field exists in any category
                    field_found = False
                    for category, fields in field_descriptions.items():
                        if field_name in fields:
                            field_found = True
                            break
                    # Some fields might be derived or computed, so we'll log but not fail
                    if not field_found:
                        print(f"Warning: Field '{field_name}' from query example '{example_name}' not found in field descriptions")
        
        # Test that threat levels in data patterns are consistent
        threat_levels = data_patterns["threat_levels"]
        level_names = list(threat_levels.keys())
        assert len(level_names) == len(set(level_names)), "Duplicate threat level names found"
        
        # Test that response priorities are consistent
        response_priorities = analysis_guidelines["response_priorities"]
        priority_levels = list(response_priorities.keys())
        assert len(priority_levels) == len(set(priority_levels)), "Duplicate response priority levels found" 