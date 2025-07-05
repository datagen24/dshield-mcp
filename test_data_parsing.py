#!/usr/bin/env python3
"""
Test script to check data parsing issues in the DShield MCP service.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.elasticsearch_client import ElasticsearchClient
from src.data_processor import DataProcessor


async def test_data_parsing():
    """Test data parsing and identify issues."""
    
    print("=== Testing Data Parsing Issues ===\n")
    
    try:
        # Initialize components
        es_client = ElasticsearchClient()
        data_processor = DataProcessor()
        
        # Connect to Elasticsearch
        await es_client.connect()
        print("✅ Connected to Elasticsearch")
        
        # Test 1: Query DShield events
        print("\n1. Testing DShield events query...")
        try:
            events = await es_client.query_dshield_events(
                time_range_hours=1, 
                size=5
            )
            print(f"✅ Query returned {len(events)} events")
            
            if events:
                print("Sample event structure:")
                print(json.dumps(events[0], indent=2, default=str)[:800] + "...")
                
                # Test data processing
                print("\n2. Testing data processing...")
                processed_events = data_processor.process_security_events(events)
                print(f"✅ Processed {len(processed_events)} events")
                
                if processed_events:
                    print("Sample processed event:")
                    print(json.dumps(processed_events[0], indent=2, default=str)[:800] + "...")
                    
                    # Test summary generation
                    print("\n3. Testing summary generation...")
                    summary = data_processor.generate_security_summary(processed_events)
                    print(f"✅ Generated summary with {len(summary)} fields")
                    print("Summary keys:", list(summary.keys()))
                    
            else:
                print("⚠️ No events returned from query")
                
        except Exception as e:
            print(f"❌ Events query failed: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Test 2: Query specific DShield attacks
        print("\n4. Testing DShield attacks query...")
        try:
            attacks = await es_client.query_dshield_attacks(
                time_range_hours=1, 
                size=3
            )
            print(f"✅ Attacks query returned {len(attacks)} attacks")
            
            if attacks:
                print("Sample attack structure:")
                print(json.dumps(attacks[0], indent=2, default=str)[:800] + "...")
                
                # Test attack processing
                print("\n5. Testing attack processing...")
                processed_attacks = data_processor.process_dshield_attacks(attacks)
                print(f"✅ Processed {len(processed_attacks)} attacks")
                
            else:
                print("⚠️ No attacks returned from query")
                
        except Exception as e:
            print(f"❌ Attacks query failed: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Test 3: Query by IP
        print("\n6. Testing IP-based query...")
        try:
            # Use a sample IP from the data
            test_ips = ["8.8.8.8", "1.1.1.1"]
            ip_events = await es_client.query_events_by_ip(
                ip_addresses=test_ips,
                time_range_hours=1
            )
            print(f"✅ IP query returned {len(ip_events)} events")
            
            if ip_events:
                print("Sample IP event structure:")
                print(json.dumps(ip_events[0], indent=2, default=str)[:800] + "...")
                
        except Exception as e:
            print(f"❌ IP query failed: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Test 4: Check field mapping
        print("\n7. Testing field mapping...")
        try:
            # Get a sample document to check field mapping
            response = await es_client.client.search(
                index="cowrie.dshield-2025.06.28-000001",
                body={
                    "query": {"match_all": {}},
                    "size": 1
                }
            )
            
            if response['hits']['hits']:
                sample_doc = response['hits']['hits'][0]['_source']
                print("Sample document fields:")
                print(list(sample_doc.keys())[:20])
                
                # Test field extraction
                print("\nTesting field extraction...")
                for field_type, field_names in es_client.dshield_field_mappings.items():
                    value = es_client._extract_field_mapped(sample_doc, field_type)
                    if value:
                        print(f"  {field_type}: {value}")
                
        except Exception as e:
            print(f"❌ Field mapping test failed: {str(e)}")
            import traceback
            traceback.print_exc()
        
        await es_client.close()
        print("\n✅ All tests completed")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_data_parsing()) 