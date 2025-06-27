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
    
    # Test specific op:// URL resolution with more realistic examples
    print("\n--- Direct op:// URL Resolution ---")
    print("Note: These tests use example URLs. Replace with your actual vault/item names.")
    
    # Get actual vault names from 1Password
    try:
        import subprocess
        result = subprocess.run(
            ["op", "vault", "list", "--format=json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            import json
            vaults = json.loads(result.stdout)
            if vaults:
                actual_vault = vaults[0].get('name', 'DevSecOps')  # Use first vault or default
                print(f"Using vault: {actual_vault}")
                
                test_op_urls = [
                    f"op://{actual_vault}/elasticsearch/password",
                    f"op://{actual_vault}/dshield/api-key",
                    "not-an-op-url",
                    "op://invalid/url/format"
                ]
            else:
                test_op_urls = [
                    "op://DevSecOps/elasticsearch/password",
                    "op://DevSecOps/dshield/api-key",
                    "not-an-op-url",
                    "op://invalid/url/format"
                ]
        else:
            test_op_urls = [
                "op://DevSecOps/elasticsearch/password",
                "op://DevSecOps/dshield/api-key",
                "not-an-op-url",
                "op://invalid/url/format"
            ]
    except Exception:
        test_op_urls = [
            "op://DevSecOps/elasticsearch/password",
            "op://DevSecOps/dshield/api-key",
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
    
    print("\n--- How to Test with Your Actual Vault ---")
    print("1. List your vaults:")
    print("   op vault list")
    print("\n2. List items in a vault:")
    print("   op item list --vault=DevSecOps")
    print("\n3. Test a specific item:")
    print("   op read op://DevSecOps/your-item-name/password")
    print("\n4. Update your .env file with correct URLs:")
    print("   ELASTICSEARCH_PASSWORD=op://DevSecOps/your-elasticsearch-item/password")
    print("   DSHIELD_API_KEY=op://DevSecOps/your-dshield-item/password")
    
    print("\n=== Test Complete ===")


if __name__ == "__main__":
    test_op_integration() 