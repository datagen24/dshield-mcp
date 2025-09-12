#!/bin/bash

# DShield MCP - UV Environment Activation Script
# This script activates the UV environment and provides helpful commands

echo "=== DShield MCP UV Environment ==="
echo

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "❌ UV package manager not found!"
    echo "Please install UV first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "  # or via pip: pip install uv"
    exit 1
fi

# Check if UV environment exists
if [ ! -d ".venv" ]; then
    echo "❌ UV environment not found!"
    echo "Please run setup_venv.sh first to create the environment."
    exit 1
fi

# Activate UV environment
echo "🔧 Activating UV environment..."
source .venv/bin/activate

# Show Python version and location
echo "✅ UV environment activated!"
echo "🐍 Python: $(python --version)"
echo "📍 Location: $(which python)"
echo "📦 UV: $(uv --version)"
echo

# Show available commands
echo "📋 Available commands:"
echo "  uv run python mcp_server.py                    - Run the MCP server"
echo "  uv run python examples/basic_usage.py          - Run the example"
echo "  uv run pytest                                  - Run tests"
echo "  uv run python -m src.tui_launcher              - Run TUI interface"
echo "  uv run python -m src.server_launcher --transport tcp - Run TCP server"
echo "  uv add <package>                               - Add new dependency"
echo "  uv sync                                        - Sync dependencies"
echo "  uv run <command>                               - Run any command in environment"
echo "  deactivate                                     - Deactivate virtual environment"
echo

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "Please copy env.example to .env and configure your settings."
fi

echo "🚀 Ready to use DShield MCP with UV!"
echo "Type 'deactivate' to exit the virtual environment."
