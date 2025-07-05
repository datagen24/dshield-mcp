#!/usr/bin/env python3
"""
Test script to verify pagination functionality in the DShield MCP service.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.elasticsearch_client import ElasticsearchClient
from src.data_processor import DataProcessor


async def test_pagination():
    """Test pagination functionality."""
    
    print("=== Testing Pagination Functionality ===\n")
    
    try:
        # Initialize components
        es_client = ElasticsearchClient()
        data_processor = DataProcessor()
        
        # Connect to Elasticsearch
        await es_client.connect()
        print("✅ Connected to Elasticsearch")
        
        # Test 1: Query with pagination
        print("\n1. Testing paginated events query...")
        try:
            events, total_count = await es_client.query_dshield_events(
                time_range_hours=24, 
                page=1,
                page_size=10
            )
            print(f"✅ Query returned {len(events)} events out of {total_count} total")
            
            # Generate pagination info
            pagination_info = es_client._generate_pagination_info(1, 10, total_count)
            print(f"Pagination info: {json.dumps(pagination_info, indent=2)}")
            
            if events:
                print("Sample event structure:")
                print(json.dumps(events[0], indent=2, default=str)[:500] + "...")
                
        except Exception as e:
            print(f"❌ Paginated events query failed: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Test 2: Query second page
        print("\n2. Testing second page...")
        try:
            events_page2, total_count = await es_client.query_dshield_events(
                time_range_hours=24, 
                page=2,
                page_size=10
            )
            print(f"✅ Second page returned {len(events_page2)} events")
            
            pagination_info = es_client._generate_pagination_info(2, 10, total_count)
            print(f"Page 2 pagination info: {json.dumps(pagination_info, indent=2)}")
            
        except Exception as e:
            print(f"❌ Second page query failed: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Test 3: Query with larger page size
        print("\n3. Testing larger page size...")
        try:
            events_large, total_count = await es_client.query_dshield_events(
                time_range_hours=24, 
                page=1,
                page_size=50
            )
            print(f"✅ Large page returned {len(events_large)} events out of {total_count} total")
            
            pagination_info = es_client._generate_pagination_info(1, 50, total_count)
            print(f"Large page pagination info: {json.dumps(pagination_info, indent=2)}")
            
        except Exception as e:
            print(f"❌ Large page query failed: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Test 4: Test attacks pagination
        print("\n4. Testing attacks pagination...")
        try:
            attacks, total_attacks = await es_client.query_dshield_attacks(
                time_range_hours=24, 
                page=1,
                page_size=5
            )
            print(f"✅ Attacks query returned {len(attacks)} attacks out of {total_attacks} total")
            
            if total_attacks > 0:
                pagination_info = es_client._generate_pagination_info(1, 5, total_attacks)
                print(f"Attacks pagination info: {json.dumps(pagination_info, indent=2)}")
            else:
                print("⚠️ No attacks found in the time range")
                
        except Exception as e:
            print(f"❌ Attacks pagination failed: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Test 5: Test edge cases
        print("\n5. Testing edge cases...")
        try:
            # Test with page size larger than max_results
            events_max, total_count = await es_client.query_dshield_events(
                time_range_hours=24, 
                page=1,
                page_size=2000  # Larger than max_results
            )
            print(f"✅ Max page size query returned {len(events_max)} events (should be capped)")
            
            # Test with very large page number
            events_large_page, total_count = await es_client.query_dshield_events(
                time_range_hours=24, 
                page=1000,  # Very large page number
                page_size=10
            )
            print(f"✅ Large page number query returned {len(events_large_page)} events")
            
        except Exception as e:
            print(f"❌ Edge case test failed: {str(e)}")
            import traceback
            traceback.print_exc()
        
        await es_client.close()
        print("\n✅ All pagination tests completed")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_pagination()) 