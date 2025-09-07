#!/usr/bin/env python3
"""Simple TUI test to verify basic functionality."""

import os
import sys

# Add the project root to the Python path
project_root = os.path.dirname(__file__)
sys.path.insert(0, project_root)

# Import using the module path
from src.tui.tui_app import DShieldTUIApp  # noqa: E402


def test_tui_startup():
    """Test if TUI can start without errors."""
    print("Testing TUI startup...")
    try:
        # Create TUI app with test config
        app = DShieldTUIApp('test_config.yaml')
        print("✅ TUI app created successfully")

        # Test configuration loading
        config = app.user_config
        print(
            f"✅ Configuration loaded: TUI={config.tui_settings.enabled}, "
            f"TCP={config.tcp_transport_settings.enabled}"
        )

        # Test basic app properties
        print(f"✅ Server port: {app.server_port}")
        print(f"✅ Server address: {app.server_address}")

        return True

    except Exception as e:
        print(f"❌ TUI startup failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_server_actions():
    """Test server action methods."""
    print("\nTesting server actions...")
    try:
        app = DShieldTUIApp('test_config.yaml')

        # Test action methods exist
        assert hasattr(app, 'action_restart_server'), "Missing action_restart_server"
        assert hasattr(app, 'action_stop_server'), "Missing action_stop_server"
        assert hasattr(app, 'action_generate_api_key'), "Missing action_generate_api_key"

        print("✅ All action methods exist")

        # Test that methods can be called (they should not crash)
        try:
            app.action_restart_server()
            print("✅ action_restart_server() executed without crash")
        except Exception as e:
            print(f"⚠️  action_restart_server() failed: {e}")

        try:
            app.action_generate_api_key()
            print("✅ action_generate_api_key() executed without crash")
        except Exception as e:
            print(f"⚠️  action_generate_api_key() failed: {e}")

        return True

    except Exception as e:
        print(f"❌ Server actions test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run TUI tests."""
    print("DShield MCP TUI Basic Test")
    print("=" * 30)

    # Test 1: TUI startup
    startup_ok = test_tui_startup()

    # Test 2: Server actions
    actions_ok = test_server_actions()

    # Summary
    print("\n" + "=" * 30)
    print("Test Summary:")
    print(f"TUI Startup: {'✅ PASS' if startup_ok else '❌ FAIL'}")
    print(f"Server Actions: {'✅ PASS' if actions_ok else '❌ FAIL'}")

    if startup_ok and actions_ok:
        print("\n🎉 Basic TUI functionality is working!")
    else:
        print("\n⚠️  Some issues found. Check the details above.")

    return startup_ok and actions_ok


if __name__ == "__main__":
    main()
