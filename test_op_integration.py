#!/usr/bin/env python3
"""
Test script for 1Password integration in DShield MCP.
This script tests the op:// URL resolution functionality.
"""

from src.op_secrets import OnePasswordSecrets

def test_op_integration():
    """Test the 1Password integration."""
    print("=== Testing 1Password Integration ===\n")
    op_secrets = OnePasswordSecrets()
    print(f"1Password CLI available: {op_secrets.op_available}")
    if not op_secrets.op_available:
        print("⚠️  1Password CLI not available. Install it from: https://1password.com/downloads/command-line/")
        print("   Then run: op signin to authenticate")
        return
    # Test direct op:// URL resolution
    test_op_urls = [
        "op://DevSecOps/es-data01-elastic/username",
        "op://DevSecOps/es-data01-elastic/password"
    ]
    print("\n--- Direct op:// URL Resolution ---")
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