#!/usr/bin/env python3
"""
Debug script for Elasticsearch DShield data investigation
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import components
try:
    from elasticsearch_client import ElasticsearchClient
except ImportError as e:
    print(f"Import error: {e}")
    print("Trying alternative import method...")
    # Try direct import from src directory
    sys.path.insert(0, str(Path(__file__).parent))
    from src.elasticsearch_client import ElasticsearchClient


async def debug_elasticsearch():
    """Debug Elasticsearch connection and data."""
    
    print("=== Elasticsearch DShield Data Debug ===\n")
    
    try:
        # Initialize client
        es_client = ElasticsearchClient()
        await es_client.connect()
        
        print("✅ Connected to Elasticsearch")
        
        # 1. Check all available indices
        print("\n1. Checking all available indices...")
        try:
            all_indices = await es_client.client.cat.indices(format='json')
            print(f"Total indices found: {len(all_indices)}")
            
            # Show first 20 indices
            for i, index in enumerate(all_indices[:20]):
                print(f"  {i+1:2d}. {index['index']} (docs: {index['docs.count']}, size: {index['store.size']})")
            
            if len(all_indices) > 20:
                print(f"  ... and {len(all_indices) - 20} more indices")
                
        except Exception as e:
            print(f"❌ Failed to get indices: {str(e)}")
        
        # 2. Check for DShield-specific indices
        print("\n2. Checking for DShield indices...")
        try:
            dshield_indices = await es_client.get_available_indices()
            print(f"DShield indices found: {len(dshield_indices)}")
            for idx, index in enumerate(dshield_indices):
                print(f"  {idx+1}. {index}")
        except Exception as e:
            print(f"❌ Failed to get DShield indices: {str(e)}")
        
        # 3. Try a broader search without time constraints
        print("\n3. Testing broad search without time constraints...")
        try:
            # Search in all indices for any document
            response = await es_client.client.search(
                index="*",
                body={
                    "query": {"match_all": {}},
                    "size": 5
                }
            )
            print(f"Total documents in cluster: {response['hits']['total']['value']}")
            print(f"Sample documents found: {len(response['hits']['hits'])}")
            
            if response['hits']['hits']:
                print("Sample document structure:")
                sample = response['hits']['hits'][0]['_source']
                print(json.dumps(sample, indent=2, default=str)[:500] + "...")
                
        except Exception as e:
            print(f"❌ Failed to search all indices: {str(e)}")
        
        # 4. Check for documents with @timestamp field
        print("\n4. Checking for documents with @timestamp field...")
        try:
            response = await es_client.client.search(
                index="*",
                body={
                    "query": {
                        "exists": {"field": "@timestamp"}
                    },
                    "size": 5
                }
            )
            print(f"Documents with @timestamp: {response['hits']['total']['value']}")
            
            if response['hits']['hits']:
                print("Sample document with @timestamp:")
                sample = response['hits']['hits'][0]['_source']
                print(f"  @timestamp: {sample.get('@timestamp', 'N/A')}")
                print(f"  Index: {response['hits']['hits'][0]['_index']}")
                
        except Exception as e:
            print(f"❌ Failed to search for @timestamp: {str(e)}")
        
        # 5. Check for documents with source.ip field
        print("\n5. Checking for documents with source.ip field...")
        try:
            response = await es_client.client.search(
                index="*",
                body={
                    "query": {
                        "exists": {"field": "source.ip"}
                    },
                    "size": 5
                }
            )
            print(f"Documents with source.ip: {response['hits']['total']['value']}")
            
            if response['hits']['hits']:
                print("Sample document with source.ip:")
                sample = response['hits']['hits'][0]['_source']
                print(f"  source.ip: {sample.get('source', {}).get('ip', 'N/A')}")
                print(f"  Index: {response['hits']['hits'][0]['_index']}")
                
        except Exception as e:
            print(f"❌ Failed to search for source.ip: {str(e)}")
        
        # 6. Check recent documents (last 7 days)
        print("\n6. Checking for recent documents (last 7 days)...")
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=7)
            
            response = await es_client.client.search(
                index="*",
                body={
                    "query": {
                        "range": {
                            "@timestamp": {
                                "gte": start_time.isoformat(),
                                "lte": end_time.isoformat()
                            }
                        }
                    },
                    "size": 5
                }
            )
            print(f"Recent documents (7 days): {response['hits']['total']['value']}")
            
            if response['hits']['hits']:
                print("Sample recent document:")
                sample = response['hits']['hits'][0]['_source']
                print(f"  @timestamp: {sample.get('@timestamp', 'N/A')}")
                print(f"  Index: {response['hits']['hits'][0]['_index']}")
                
        except Exception as e:
            print(f"❌ Failed to search for recent documents: {str(e)}")
        
        # 7. Check specific index patterns that might contain DShield data
        print("\n7. Checking specific index patterns...")
        patterns_to_check = [
            "dshield*",
            "security*", 
            "logs*",
            "alerts*",
            "zeek*",
            "suricata*",
            "firewall*",
            "ids*",
            "ips*"
        ]
        
        for pattern in patterns_to_check:
            try:
                response = await es_client.client.search(
                    index=pattern,
                    body={
                        "query": {"match_all": {}},
                        "size": 1
                    }
                )
                count = response['hits']['total']['value']
                if count > 0:
                    print(f"  {pattern}: {count} documents")
                    sample = response['hits']['hits'][0]['_source']
                    print(f"    Sample fields: {list(sample.keys())[:10]}")
                else:
                    print(f"  {pattern}: 0 documents")
            except Exception as e:
                print(f"  {pattern}: Error - {str(e)}")
        
        # 8. Check cluster health and stats
        print("\n8. Checking cluster health...")
        try:
            health = await es_client.client.cluster.health()
            print(f"Cluster status: {health['status']}")
            print(f"Number of nodes: {health['number_of_nodes']}")
            print(f"Active shards: {health['active_shards']}")
            
            stats = await es_client.client.cluster.stats()
            print(f"Total indices: {stats['indices']['count']}")
            print(f"Total documents: {stats['indices']['docs']['count']}")
            
        except Exception as e:
            print(f"❌ Failed to get cluster health: {str(e)}")
        
        await es_client.close()
        print("\n✅ Debug completed")
        
    except Exception as e:
        print(f"❌ Debug failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(debug_elasticsearch()) 