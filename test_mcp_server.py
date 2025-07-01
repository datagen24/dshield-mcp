#!/usr/bin/env python3
"""
Test script for DShield MCP Server Components
Tests the server components directly without MCP protocol.
"""

import asyncio
import json
import sys
import os
from pathlib import Path
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set up environment for relative imports
os.environ['PYTHONPATH'] = str(Path(__file__).parent / "src")

# Import components
try:
    from elasticsearch_client import ElasticsearchClient
    from dshield_client import DShieldClient
    from data_processor import DataProcessor
    from context_injector import ContextInjector
except ImportError as e:
    print(f"Import error: {e}")
    print("Trying alternative import method...")
    # Try direct import from src directory
    sys.path.insert(0, str(Path(__file__).parent))
    from src.elasticsearch_client import ElasticsearchClient
    from src.dshield_client import DShieldClient
    from src.data_processor import DataProcessor
    from src.context_injector import ContextInjector


@pytest.mark.asyncio
async def test_server_components():
    """Test the server components directly."""
    
    print("=== Testing DShield MCP Server Components ===\n")
    
    try:
        # Initialize components
        print("Initializing server components...")
        es_client = ElasticsearchClient()
        dshield_client = DShieldClient()
        data_processor = DataProcessor()
        context_injector = ContextInjector()
        
        # Test Elasticsearch connection
        print("Testing Elasticsearch connection...")
        try:
            await es_client.connect()
            print("✅ Elasticsearch connection successful")
            
            # Test getting available indices
            indices = await es_client.get_available_indices()
            print(f"✅ Found {len(indices)} available indices")
            
            # Test querying DShield events
            print("Testing DShield events query...")
            events = await es_client.query_dshield_events(time_range_hours=1, size=5)
            print(f"✅ Query returned {len(events)} events")
            
            if events:
                print("Sample event structure:")
                print(json.dumps(events[0], indent=2, default=str)[:500] + "...")
            
            # Test querying DShield attacks
            print("\nTesting DShield attacks query...")
            attacks = await es_client.query_dshield_attacks(time_range_hours=1, size=3)
            print(f"✅ Query returned {len(attacks)} attacks")
            
            # Test getting DShield statistics
            print("\nTesting DShield statistics...")
            stats = await es_client.get_dshield_statistics(time_range_hours=1)
            print(f"✅ Statistics query successful")
            print(f"   Total events: {stats.get('total_events', 'N/A')}")
            print(f"   Unique IPs: {stats.get('unique_ips', 'N/A')}")
            
            # Test data processing
            print("\nTesting data processing...")
            unique_ips = []  # Initialize empty list
            if events:
                processed_events = data_processor.process_security_events(events)
                print(f"✅ Processed {len(processed_events)} events")
                
                summary = data_processor.generate_security_summary(processed_events)
                print(f"✅ Generated security summary")
                print(f"   Total events: {summary.get('total_events', 'N/A')}")
                print(f"   High risk events: {summary.get('high_risk_events', 'N/A')}")
                
                unique_ips = data_processor.extract_unique_ips(processed_events)
                print(f"✅ Extracted {len(unique_ips)} unique IPs")
            else:
                print("⚠️ No events found for data processing")
            
            # Test DShield client (with a safe IP)
            print("\nTesting DShield client...")
            try:
                ti_data = await dshield_client.get_ip_reputation("8.8.8.8")
                print(f"✅ DShield reputation query successful")
                print(f"   Threat level: {ti_data.get('threat_level', 'N/A')}")
                print(f"   Country: {ti_data.get('country', 'N/A')}")
            except Exception as e:
                print(f"⚠️ DShield reputation query failed (expected for test IP): {str(e)}")
            
            # Test context injection
            print("\nTesting context injection...")
            if events:
                context = context_injector.prepare_security_context(
                    processed_events[:5],  # Use first 5 events
                    {},  # Empty threat intelligence for test
                    summary
                )
                print(f"✅ Context injection successful")
                print(f"   Context length: {len(context)} characters")
            else:
                print("⚠️ No events found for context injection")
            
            # Test specific tool functions
            print("\n=== Testing Tool Functions ===")
            
            # Test query_events_by_ip
            print("Testing query_events_by_ip...")
            if unique_ips:
                ip_events = await es_client.query_events_by_ip(
                    ip_addresses=unique_ips[:3],  # Test with first 3 IPs
                    time_range_hours=1
                )
                print(f"✅ IP events query returned {len(ip_events)} events")
            else:
                print("⚠️ No unique IPs found for IP events query")
            
            # Test query_dshield_top_attackers
            print("Testing query_dshield_top_attackers...")
            attackers = await es_client.query_dshield_top_attackers(hours=1, limit=5)
            print(f"✅ Top attackers query returned {len(attackers)} attackers")
            
            # Test query_dshield_geographic_data
            print("Testing query_dshield_geographic_data...")
            geo_data = await es_client.query_dshield_geographic_data(size=5)
            print(f"✅ Geographic data query returned {len(geo_data)} records")
            
            # Test query_dshield_port_data
            print("Testing query_dshield_port_data...")
            port_data = await es_client.query_dshield_port_data(size=5)
            print(f"✅ Port data query returned {len(port_data)} records")
            
            # Test query_dshield_reputation
            print("Testing query_dshield_reputation...")
            rep_data = await es_client.query_dshield_reputation(size=5)
            print(f"✅ Reputation data query returned {len(rep_data)} records")
            
            await es_client.close()
            print("\n✅ All component tests completed successfully!")
            
        except Exception as e:
            print(f"❌ Elasticsearch test failed: {str(e)}")
            raise
            
    except Exception as e:
        print(f"❌ Component test failed: {str(e)}")
        raise


@pytest.mark.asyncio
async def test_mcp_server_tools():
    """Test the MCP server tool functions directly."""
    
    print("\n=== Testing MCP Server Tool Functions ===\n")
    
    try:
        # Import the server class
        from mcp_server import DShieldMCPServer
        
        # Create server instance
        server = DShieldMCPServer()
        
        # Initialize server
        print("Initializing MCP server...")
        await server.initialize()
        print("✅ MCP server initialized")
        
        # Test tool functions
        print("\nTesting tool functions...")
        
        # Test _get_dshield_statistics
        print("Testing _get_dshield_statistics...")
        result = await server._get_dshield_statistics({"time_range_hours": 1})
        print(f"✅ Statistics tool returned {len(result)} content items")
        
        # Test _query_dshield_events
        print("Testing _query_dshield_events...")
        result = await server._query_dshield_events({"time_range_hours": 1, "size": 5})
        print(f"✅ Events tool returned {len(result)} content items")
        
        # Test _query_dshield_attacks
        print("Testing _query_dshield_attacks...")
        result = await server._query_dshield_attacks({"time_range_hours": 1, "size": 3})
        print(f"✅ Attacks tool returned {len(result)} content items")
        
        # Test _get_security_summary
        print("Testing _get_security_summary...")
        result = await server._get_security_summary({"include_threat_intelligence": False})
        print(f"✅ Security summary tool returned {len(result)} content items")
        
        # Test _enrich_ip_with_dshield
        print("Testing _enrich_ip_with_dshield...")
        result = await server._enrich_ip_with_dshield({"ip_address": "8.8.8.8"})
        print(f"✅ IP enrichment tool returned {len(result)} content items")
        
        # Cleanup
        await server.cleanup()
        print("\n✅ All MCP server tool tests completed successfully!")
        
    except Exception as e:
        print(f"❌ MCP server tool test failed: {str(e)}")
        raise


async def main():
    """Run all tests."""
    try:
        await test_server_components()
        await test_mcp_server_tools()
        print("\n🎉 All tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 