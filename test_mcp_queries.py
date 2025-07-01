#!/usr/bin/env python3
"""
Test script to query the MCP server directly and debug data issues.
"""

import asyncio
import json
import subprocess
from mcp import ClientSession
from mcp.server.stdio import stdio_server
import pytest


@pytest.mark.asyncio
async def test_mcp_server():
    """Test the MCP server directly."""
    
    print("=== Testing MCP Server Directly ===")
    
    # Start the MCP server process
    process = subprocess.Popen(
        ["python", "mcp_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Connect to the MCP server
        async with ClientSession(stdio_server(process.stdout, process.stdin)) as session:
            print("✅ Connected to MCP server")
            
            # List available tools
            tools = await session.list_tools()
            print(f"📋 Available tools: {len(tools.tools)}")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")
            
            print("\n=== Testing Each Tool ===")
            
            # Test events tool
            print("\n🔍 Testing events tool...")
            try:
                result = await session.call_tool("_query_dshield_events", {
                    "time_range_hours": 24,
                    "limit": 5
                })
                print(f"✅ Events tool returned: {len(result.content)} items")
                if result.content:
                    print(f"Sample event: {json.dumps(result.content[0].text[:500], indent=2)}")
            except Exception as e:
                print(f"❌ Events tool failed: {e}")
            
            # Test attacks tool
            print("\n🔍 Testing attacks tool...")
            try:
                result = await session.call_tool("_query_dshield_attacks", {
                    "time_range_hours": 24,
                    "limit": 3
                })
                print(f"✅ Attacks tool returned: {len(result.content)} items")
                if result.content:
                    print(f"Sample attack: {json.dumps(result.content[0].text[:500], indent=2)}")
            except Exception as e:
                print(f"❌ Attacks tool failed: {e}")
            
            # Test security summary tool
            print("\n🔍 Testing security summary tool...")
            try:
                result = await session.call_tool("_get_security_summary", {
                    "time_range_hours": 24
                })
                print(f"✅ Security summary tool returned: {len(result.content)} items")
                if result.content:
                    print(f"Summary: {json.dumps(result.content[0].text[:500], indent=2)}")
            except Exception as e:
                print(f"❌ Security summary tool failed: {e}")
            
            # Test IP enrichment tool
            print("\n🔍 Testing IP enrichment tool...")
            try:
                result = await session.call_tool("_enrich_ip_with_dshield", {
                    "ip_address": "8.8.8.8"
                })
                print(f"✅ IP enrichment tool returned: {len(result.content)} items")
                if result.content:
                    print(f"Enrichment: {json.dumps(result.content[0].text[:500], indent=2)}")
            except Exception as e:
                print(f"❌ IP enrichment tool failed: {e}")
    
    finally:
        # Clean up the process
        process.terminate()
        process.wait()


if __name__ == "__main__":
    asyncio.run(test_mcp_server()) 