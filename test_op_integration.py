#!/usr/bin/env python3
"""
Test script for 1Password integration in DShield MCP.
This script tests the op:// URL resolution functionality.
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from op_secrets import get_env_with_op_resolution, op_secrets


def test_op_integration():
    """Test the 1Password integration."""
    print("=== Testing 1Password Integration ===\n")
    
    # Load environment variables
    load_dotenv()
    
    # Test 1Password CLI availability
    print(f"1Password CLI available: {op_secrets.op_available}")
    
    if not op_secrets.op_available:
        print("⚠️  1Password CLI not available. Install it from: https://1password.com/downloads/command-line/")
        print("   Then run: op signin to authenticate")
        return
    
    # Test environment variables that might contain op:// URLs
    test_vars = [
        "ELASTICSEARCH_PASSWORD",
        "DSHIELD_API_KEY",
        "ELASTICSEARCH_USERNAME",
        "ELASTICSEARCH_URL"
    ]
    
    print("\n--- Environment Variable Resolution ---")
    for var_name in test_vars:
        original_value = os.getenv(var_name, "NOT_SET")
        resolved_value = get_env_with_op_resolution(var_name, "NOT_SET")
        
        print(f"\n{var_name}:")
        print(f"  Original: {original_value[:20]}{'...' if len(original_value) > 20 else ''}")
        print(f"  Resolved: {resolved_value[:20]}{'...' if len(resolved_value) > 20 else ''}")
        
        if original_value != resolved_value:
            print(f"  ✅ Successfully resolved op:// URL")
        elif original_value.startswith("op://"):
            print(f"  ❌ Failed to resolve op:// URL")
        else:
            print(f"  ℹ️  No op:// URL to resolve")
    
    # Test specific op:// URL resolution
    print("\n--- Direct op:// URL Resolution ---")
    test_op_urls = [
        "op://vault/elasticsearch/password",
        "op://vault/dshield/api-key",
        "not-an-op-url",
        "op://invalid/url/format"
    ]
    
    for op_url in test_op_urls:
        print(f"\nTesting: {op_url}")
        try:
            resolved = op_secrets.resolve_op_url(op_url)
            if resolved:
                print(f"  ✅ Resolved: {resolved[:20]}{'...' if len(resolved) > 20 else ''}")
            else:
                print(f"  ❌ Failed to resolve")
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
    
    print("\n=== Test Complete ===")


if __name__ == "__main__":
    test_op_integration() 