"""Integration tests for server startup and core components."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.models import SecurityEvent, ThreatIntelligence, AttackReport
from src.data_processor import DataProcessor
from src.context_injector import ContextInjector


class TestServerIntegration:
    """Test server integration and startup components."""
    
    def test_import_validation(self):
        """Test that all required modules can be imported."""
        # Test core models
        assert SecurityEvent is not None
        assert ThreatIntelligence is not None
        assert AttackReport is not None
        
        # Test core components
        assert DataProcessor is not None
        assert ContextInjector is not None
        
        # Test clients (already tested extensively, just verify imports)
        from src.elasticsearch_client import ElasticsearchClient
        from src.dshield_client import DShieldClient
        assert ElasticsearchClient is not None
        assert DShieldClient is not None
        
        # Test config and utilities
        from src.config_loader import get_config, ConfigError
        from src.data_dictionary import DataDictionary
        from src.op_secrets import OnePasswordSecrets
        assert get_config is not None
        assert ConfigError is not None
        assert DataDictionary is not None
        assert OnePasswordSecrets is not None
    
    def test_data_processor_initialization(self):
        """Test DataProcessor initialization."""
        data_processor = DataProcessor()
        assert data_processor is not None
    
    def test_data_processor_event_processing(self):
        """Test DataProcessor event processing functionality."""
        data_processor = DataProcessor()
        
        # Create test events
        test_events = [
            {
                'id': 'test-1',
                'timestamp': '2024-01-01T12:00:00Z',
                'source_ip': '192.168.1.100',
                'destination_ip': '10.0.0.1',
                'event_type': 'authentication_failure',
                'severity': 'high',
                'category': 'authentication',
                'description': 'Failed login attempt'
            },
            {
                'id': 'test-2',
                'timestamp': '2024-01-01T12:01:00Z',
                'source_ip': '192.168.1.101',
                'destination_ip': '10.0.0.2',
                'event_type': 'port_scan',
                'severity': 'medium',
                'category': 'reconnaissance',
                'description': 'Port scan detected'
            }
        ]
        
        # Test event processing - returns List[Dict[str, Any]], not SecurityEvent objects
        processed_events = data_processor.process_security_events(test_events)
        assert len(processed_events) == 2
        assert all(isinstance(event, dict) for event in processed_events)
        
        # Test summary generation
        summary = data_processor.generate_security_summary(processed_events)
        assert summary['total_events'] == 2
        assert 'events_by_severity' in summary
        assert 'events_by_category' in summary
        assert 'top_source_ips' in summary
        assert 'top_destination_ips' in summary
    
    def test_data_processor_ip_extraction(self):
        """Test DataProcessor IP extraction functionality."""
        data_processor = DataProcessor()
        
        test_events = [
            {
                'id': 'test-1',
                'source_ip': '192.168.1.100',
                'destination_ip': '10.0.0.1',
                'event_type': 'test'
            },
            {
                'id': 'test-2',
                'source_ip': '192.168.1.101',
                'destination_ip': '10.0.0.1',  # Duplicate destination
                'event_type': 'test'
            }
        ]
        
        processed_events = data_processor.process_security_events(test_events)
        unique_ips = data_processor.extract_unique_ips(processed_events)
        
        # Should have 3 unique IPs: 192.168.1.100, 192.168.1.101, 10.0.0.1
        assert len(unique_ips) == 3
        assert '192.168.1.100' in unique_ips
        assert '192.168.1.101' in unique_ips
        assert '10.0.0.1' in unique_ips
    
    def test_context_injector_initialization(self):
        """Test ContextInjector initialization."""
        context_injector = ContextInjector()
        assert context_injector is not None
    
    def test_context_injector_context_preparation(self):
        """Test ContextInjector context preparation."""
        context_injector = ContextInjector()
        
        # Create test data
        test_events = [
            {
                'id': 'test-1',
                'timestamp': '2024-01-01T12:00:00Z',
                'event_type': 'test_event',
                'severity': 'medium',
                'description': 'Test event for context injection'
            }
        ]
        
        test_ti = {
            '192.168.1.100': {
                'ip_address': '192.168.1.100',
                'threat_level': 'medium',
                'reputation_score': 50
            }
        }
        
        # Test context preparation - returns nested structure
        context = context_injector.prepare_security_context(test_events, test_ti)
        assert context is not None
        assert 'context_type' in context
        assert 'data' in context
        assert 'events' in context['data']
        assert 'threat_intelligence' in context['data']
    
    def test_context_injector_chatgpt_formatting(self):
        """Test ContextInjector ChatGPT context formatting."""
        context_injector = ContextInjector()
        
        # Create test context with proper structure
        test_context = {
            'context_type': 'security_analysis',
            'data': {
                'events': [
                    {
                        'id': 'test-1',
                        'timestamp': '2024-01-01T12:00:00Z',
                        'event_type': 'test_event',
                        'severity': 'medium',
                        'description': 'Test event'
                    }
                ],
                'threat_intelligence': {
                    '192.168.1.100': {
                        'ip_address': '192.168.1.100',
                        'threat_level': 'medium',
                        'reputation_score': 50
                    }
                },
                'summary': {
                    'total_events': 1,
                    'severity_breakdown': {'medium': 1}
                }
            }
        }
        
        # Test ChatGPT formatting
        chatgpt_context = context_injector.inject_context_for_chatgpt(test_context)
        assert chatgpt_context is not None
        assert isinstance(chatgpt_context, str)
        assert len(chatgpt_context) > 0
    
    @patch('src.config_loader.get_config')
    @patch('src.elasticsearch_client.ElasticsearchClient')
    @patch('src.dshield_client.DShieldClient')
    def test_integration_startup(self, mock_dshield_client, mock_es_client, mock_get_config):
        """Test that all components can initialize together."""
        # Mock config
        mock_config = {
            'elasticsearch': {
                'url': 'http://localhost:9200',
                'username': 'test_user',
                'password': 'test_pass'
            },
            'dshield': {
                'api_key': 'test_api_key',
                'base_url': 'https://api.dshield.org'
            }
        }
        mock_get_config.return_value = mock_config
        
        # Mock clients
        mock_es_instance = Mock()
        mock_es_client.return_value = mock_es_instance
        
        mock_dshield_instance = Mock()
        mock_dshield_client.return_value = mock_dshield_instance
        
        # Test that all components can be imported and initialized
        from src.elasticsearch_client import ElasticsearchClient
        from src.dshield_client import DShieldClient
        from src.data_processor import DataProcessor
        from src.context_injector import ContextInjector
        
        # Initialize components
        es_client = ElasticsearchClient()
        dshield_client = DShieldClient()
        data_processor = DataProcessor()
        context_injector = ContextInjector()
        
        # Verify all components initialized successfully
        assert es_client is not None
        assert dshield_client is not None
        assert data_processor is not None
        assert context_injector is not None
        
        # Note: get_config is not called during component initialization
        # It's only called when clients need configuration
    
    def test_data_processor_empty_events(self):
        """Test DataProcessor with empty event list."""
        data_processor = DataProcessor()
        
        # Test with empty events
        processed_events = data_processor.process_security_events([])
        assert len(processed_events) == 0
        
        # Test summary with empty events
        summary = data_processor.generate_security_summary(processed_events)
        assert summary['total_events'] == 0
        # Check for expected keys in summary
        assert 'events_by_severity' in summary
        assert 'events_by_category' in summary
        assert 'top_source_ips' in summary
        assert 'top_destination_ips' in summary
    
    def test_context_injector_empty_data(self):
        """Test ContextInjector with empty data."""
        context_injector = ContextInjector()
        
        # Test with empty data
        context = context_injector.prepare_security_context([], {})
        assert context is not None
        assert 'context_type' in context
        assert 'data' in context
        assert 'events' in context['data']
        assert context['data']['events'] == []
        
        # Test ChatGPT formatting with empty context
        chatgpt_context = context_injector.inject_context_for_chatgpt(context)
        assert chatgpt_context is not None
        assert isinstance(chatgpt_context, str)
    
    def test_data_processor_invalid_events(self):
        """Test DataProcessor with invalid event data."""
        data_processor = DataProcessor()
        
        # Test with None events
        with pytest.raises(TypeError):
            data_processor.process_security_events(None)
        
        # Test with invalid event structure
        invalid_events = [{'invalid': 'data'}]
        processed_events = data_processor.process_security_events(invalid_events)
        # Should handle gracefully and create events with default values
        assert len(processed_events) == 1
        assert isinstance(processed_events[0], dict) 