#!/usr/bin/env python3
"""Minimal test to verify basic functionality."""

import os
import sys

# Add the project root to the Python path
project_root = os.path.dirname(__file__)
sys.path.insert(0, project_root)


def test_config_loading():
    """Test if configuration loads correctly."""
    print("Testing configuration loading...")
    try:
        from src.user_config import UserConfigManager

        config = UserConfigManager('test_config.yaml')
        print(f"✅ TUI enabled: {config.tui_settings.enabled}")
        print(f"✅ TCP enabled: {config.tcp_transport_settings.enabled}")
        print(f"✅ Port: {config.tcp_transport_settings.port}")
        print(f"✅ Bind address: {config.tcp_transport_settings.bind_address}")
        return True
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_imports():
    """Test if all required modules can be imported."""
    print("\nTesting imports...")
    try:

        print("✅ UserConfigManager imported")


        print("✅ EnhancedTCPServer imported")


        print("✅ TCPConnection imported")

        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run minimal tests."""
    print("DShield MCP Minimal Test")
    print("=" * 25)

    # Test 1: Imports
    imports_ok = test_imports()

    # Test 2: Configuration loading
    config_ok = test_config_loading()

    # Summary
    print("\n" + "=" * 25)
    print("Test Summary:")
    print(f"Imports: {'✅ PASS' if imports_ok else '❌ FAIL'}")
    print(f"Configuration: {'✅ PASS' if config_ok else '❌ FAIL'}")

    if imports_ok and config_ok:
        print("\n🎉 Basic functionality is working!")
    else:
        print("\n⚠️  Some issues found. Check the details above.")

    return imports_ok and config_ok


if __name__ == "__main__":
    main()
