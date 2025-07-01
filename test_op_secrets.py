#!/usr/bin/env python3
"""
Test script to verify 1Password secrets resolution.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.op_secrets import OnePasswordSecrets
from src.config_loader import get_config

def test_op_secrets():
    """Test 1Password secrets resolution."""
    
    print("=== Testing 1Password Secrets Resolution ===\n")
    
    # Test 1Password CLI availability
    print("1. Testing 1Password CLI availability...")
    op_secrets = OnePasswordSecrets()
    if op_secrets.op_available:
        print("✅ 1Password CLI is available")
    else:
        print("❌ 1Password CLI is not available")
        return False
    
    # Test config loading with secrets resolution
    print("\n2. Testing config loading with secrets resolution...")
    try:
        config = get_config()
        print("✅ Config loaded successfully")
        
        # Check if secrets were resolved
        es_config = config.get('elasticsearch', {})
        username = es_config.get('username', '')
        password = es_config.get('password', '')
        
        print(f"   Username: {username[:10]}..." if len(username) > 10 else f"   Username: {username}")
        print(f"   Password: {'*' * len(password)}" if password else "   Password: (empty)")
        
        # Check if op:// URLs were resolved
        if username.startswith('op://') or password.startswith('op://'):
            print("⚠️  Some op:// URLs were not resolved")
            return False
        else:
            print("✅ op:// URLs were successfully resolved")
        
    except Exception as e:
        print(f"❌ Config loading failed: {str(e)}")
        return False
    
    print("\n=== 1Password secrets resolution is working! ===")
    return True

if __name__ == "__main__":
    success = test_op_secrets()
    sys.exit(0 if success else 1) 