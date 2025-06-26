#!/usr/bin/env python3
"""
Test script to verify DShield MCP installation and basic functionality.
"""

import sys
import asyncio
from pathlib import Path

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        # Test core imports
        from src.models import SecurityEvent, ThreatIntelligence, AttackReport
        print("✓ Core models imported successfully")
        
        from src.elasticsearch_client import ElasticsearchClient
        print("✓ Elasticsearch client imported successfully")
        
        from src.dshield_client import DShieldClient
        print("✓ DShield client imported successfully")
        
        from src.data_processor import DataProcessor
        print("✓ Data processor imported successfully")
        
        from src.context_injector import ContextInjector
        print("✓ Context injector imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_environment():
    """Test environment configuration."""
    print("\nTesting environment configuration...")
    
    try:
        from dotenv import load_dotenv
        import os
        
        # Load environment variables
        load_dotenv()
        
        # Check required environment variables
        required_vars = [
            "ELASTICSEARCH_URL",
            "ELASTICSEARCH_USERNAME"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"⚠ Missing environment variables: {', '.join(missing_vars)}")
            print("  Run 'python config.py setup' to configure")
            return False
        else:
            print("✓ Environment variables configured")
            return True
            
    except Exception as e:
        print(f"✗ Environment test error: {e}")
        return False

async def test_elasticsearch_connection():
    """Test Elasticsearch connection."""
    print("\nTesting Elasticsearch connection...")
    
    try:
        from src.elasticsearch_client import ElasticsearchClient
        
        es_client = ElasticsearchClient()
        await es_client.connect()
        
        # Test basic query
        events = await es_client.query_security_events(time_range_hours=1, size=1)
        print(f"✓ Elasticsearch connection successful (queried {len(events)} events)")
        
        await es_client.close()
        return True
        
    except Exception as e:
        print(f"✗ Elasticsearch connection failed: {e}")
        print("  Check your Elasticsearch configuration and connectivity")
        return False

async def test_dshield_connection():
    """Test DShield API connection."""
    print("\nTesting DShield API connection...")
    
    try:
        from src.dshield_client import DShieldClient
        
        dshield_client = DShieldClient()
        await dshield_client.connect()
        
        # Test with a known IP (Google DNS)
        test_ip = "8.8.8.8"
        reputation = await dshield_client.get_ip_reputation(test_ip)
        
        if reputation:
            print(f"✓ DShield API connection successful (tested IP: {test_ip})")
        else:
            print("⚠ DShield API responded but no reputation data returned")
        
        await dshield_client.close()
        return True
        
    except Exception as e:
        print(f"✗ DShield API connection failed: {e}")
        print("  Check your DShield API configuration")
        return False

def test_data_processing():
    """Test data processing functionality."""
    print("\nTesting data processing...")
    
    try:
        from src.data_processor import DataProcessor
        from src.models import SecurityEvent
        
        # Create test data
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
            }
        ]
        
        data_processor = DataProcessor()
        
        # Test event processing
        processed_events = data_processor.process_security_events(test_events)
        print(f"✓ Event processing successful ({len(processed_events)} events processed)")
        
        # Test summary generation
        summary = data_processor.generate_security_summary(processed_events)
        print(f"✓ Summary generation successful (total events: {summary['total_events']})")
        
        # Test IP extraction
        unique_ips = data_processor.extract_unique_ips(processed_events)
        print(f"✓ IP extraction successful ({len(unique_ips)} unique IPs)")
        
        return True
        
    except Exception as e:
        print(f"✗ Data processing test failed: {e}")
        return False

def test_context_injection():
    """Test context injection functionality."""
    print("\nTesting context injection...")
    
    try:
        from src.context_injector import ContextInjector
        
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
        
        context_injector = ContextInjector()
        
        # Test context preparation
        context = context_injector.prepare_security_context(test_events, test_ti)
        print("✓ Context preparation successful")
        
        # Test ChatGPT formatting
        chatgpt_context = context_injector.inject_context_for_chatgpt(context)
        print("✓ ChatGPT context formatting successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Context injection test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("=== DShield MCP Installation Test ===\n")
    
    tests = [
        ("Import Test", test_imports),
        ("Environment Test", test_environment),
        ("Elasticsearch Connection", test_elasticsearch_connection),
        ("DShield API Connection", test_dshield_connection),
        ("Data Processing", test_data_processing),
        ("Context Injection", test_context_injection)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n=== Test Summary ===")
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your DShield MCP installation is working correctly.")
        print("\nNext steps:")
        print("1. Run 'python mcp_server.py' to start the MCP server")
        print("2. Configure your ChatGPT client to use the MCP server")
        print("3. Try the example scripts in the examples/ directory")
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Please check the configuration and try again.")
        print("\nTroubleshooting:")
        print("1. Run 'python config.py setup' to configure environment variables")
        print("2. Run 'python config.py test' to test connections")
        print("3. Check the README.md and USAGE.md files for more information")

if __name__ == "__main__":
    asyncio.run(main()) 