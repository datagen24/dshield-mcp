#!/usr/bin/env python3
"""
Test script to verify server startup and connection handling.
"""

import asyncio
import sys
import json
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.elasticsearch_client import ElasticsearchClient

async def test_server_startup():
    """Test that the server components can initialize properly."""
    
    print("=== Testing Server Startup ===\n")
    
    try:
        # Test Elasticsearch client initialization
        print("1. Testing Elasticsearch client initialization...")
        es_client = ElasticsearchClient()
        print("✅ Elasticsearch client initialized successfully")
        
        # Test connection (this should fail gracefully)
        print("\n2. Testing Elasticsearch connection...")
        try:
            await es_client.connect()
            print("✅ Connected to Elasticsearch successfully")
        except Exception as e:
            print(f"⚠️  Expected connection failure: {str(e)}")
            print("   This is expected if Elasticsearch is not running or not accessible")
        
        # Test configuration loading
        print("\n3. Testing configuration loading...")
        from src.config_loader import get_config
        config = get_config()
        print(f"✅ Configuration loaded successfully")
        print(f"   Elasticsearch URL: {config['elasticsearch']['url']}")
        
        # Test data processor initialization
        print("\n4. Testing data processor initialization...")
        from src.data_processor import DataProcessor
        data_processor = DataProcessor()
        print("✅ Data processor initialized successfully")
        
        # Test DShield client initialization
        print("\n5. Testing DShield client initialization...")
        from src.dshield_client import DShieldClient
        dshield_client = DShieldClient()
        print("✅ DShield client initialized successfully")
        
        print("\n=== All components initialized successfully! ===")
        print("The server should be able to start without crashing.")
        print("Connection errors will be handled gracefully when tools are called.")
        
    except Exception as e:
        print(f"❌ Startup test failed: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_server_startup())
    sys.exit(0 if success else 1) 