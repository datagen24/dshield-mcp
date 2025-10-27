#!/bin/bash

# TCP/TUI System Validation Script
# This script provides step-by-step validation of the TCP/TUI system
# Run each section in separate terminal sessions as needed

set -e

echo "=== DShield MCP TCP/TUI System Validation ==="
echo ""

# Check if we're in the virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "❌ ERROR: Virtual environment not activated!"
    echo "Please run: source venv/bin/activate"
    exit 1
fi

echo "✅ Virtual environment activated: $VIRTUAL_ENV"
echo ""

# Check if TUI is enabled in config
echo "=== Step 1: Configuration Check ==="
python -c "
from src.user_config import UserConfigManager
config = UserConfigManager()
print(f'TUI enabled: {config.tui_settings.enabled}')
print(f'TCP port: {config.tcp_transport_settings.port}')
print(f'TCP bind address: {config.tcp_transport_settings.bind_address}')
"

echo ""
echo "=== Step 2: TUI Launch Test ==="
echo "To test TUI launch, run in a separate terminal:"
echo "  source venv/bin/activate"
echo "  python -m src.tui_launcher"
echo ""
echo "Expected behavior:"
echo "  - TUI should launch without errors"
echo "  - All panels should render correctly"
echo "  - Server should auto-start if configured"
echo ""

echo "=== Step 3: TCP Connectivity Test ==="
echo "After TUI is running, test TCP connectivity in another terminal:"
echo ""
echo "# Test if port is listening:"
echo "lsof -i :3000"
echo ""
echo "# Test basic connection:"
echo "nc -v localhost 3000"
echo ""
echo "# Test MCP initialize message:"
echo "echo '{\"jsonrpc\":\"2.0\",\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"0.1.0\",\"capabilities\":{}},\"id\":1}' | nc localhost 3000"
echo ""

echo "=== Step 4: API Key Generation Test ==="
echo "In the TUI:"
echo "  - Press 'g' or click 'Generate API Key'"
echo "  - Verify key appears in connection panel"
echo "  - Check if key is stored properly"
echo ""

echo "=== Step 5: Server Control Test ==="
echo "In the TUI:"
echo "  - Press 's' to stop server"
echo "  - Verify status changes to 'Stopped'"
echo "  - Press 'r' to restart"
echo "  - Verify server comes back up"
echo ""

echo "=== Step 6: Manual Server Test (Alternative) ==="
echo "To test server without TUI, run:"
echo "  python -c \"
import asyncio
import sys
sys.path.insert(0, '.')
from src.server_launcher import DShieldServerLauncher

async def test_server():
    launcher = DShieldServerLauncher()
    await launcher.initialize_server()
    print('Server initialized successfully')
    # Start TCP mode
    await launcher.start_tcp_mode()

asyncio.run(test_server())
\""
echo ""

echo "=== Validation Checklist ==="
echo "□ TUI launches successfully"
echo "□ Server starts from TUI"
echo "□ TCP port 3000 accepts connections"
echo "□ MCP messages get responses"
echo "□ API keys can be generated"
echo "□ Server stop/restart works"
echo ""

echo "=== Troubleshooting ==="
echo "If TUI fails to launch:"
echo "  - Check if textual is installed: pip list | grep textual"
echo "  - Check virtual environment: echo \$VIRTUAL_ENV"
echo "  - Check configuration: python -c \"from src.user_config import UserConfigManager; print(UserConfigManager().tui_settings.enabled)\""
echo ""
echo "If server fails to start:"
echo "  - Check 1Password CLI: op --version"
echo "  - Check Elasticsearch connectivity"
echo "  - Check configuration files"
echo ""

echo "=== Test Complete ==="
echo "Run the TUI in a separate terminal to begin validation."
