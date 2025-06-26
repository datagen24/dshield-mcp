#!/bin/bash

# DShield MCP - Virtual Environment Activation Script
# This script activates the virtual environment and provides helpful commands

echo "=== DShield MCP Virtual Environment ==="
echo

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run setup_venv.sh first to create the virtual environment."
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Show Python version and location
echo "✅ Virtual environment activated!"
echo "🐍 Python: $(python --version)"
echo "📍 Location: $(which python)"
echo

# Show available commands
echo "📋 Available commands:"
echo "  python mcp_server.py          - Run the MCP server"
echo "  python examples/basic_usage.py - Run the example"
echo "  python test_installation.py   - Test the installation"
echo "  python config.py              - Configure settings"
echo "  deactivate                    - Deactivate virtual environment"
echo

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "Please copy .env.example to .env and configure your settings."
fi

echo "🚀 Ready to use DShield MCP!"
echo "Type 'deactivate' to exit the virtual environment." 