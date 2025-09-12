#!/bin/bash

# DShield MCP - UV Environment Setup Script
# This script sets up the project using UV package manager

set -e  # Exit on any error

echo "=== DShield MCP UV Environment Setup ==="
echo

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "❌ Error: UV package manager is not installed"
    echo "Please install UV first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "  # or on Windows: powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\""
    echo "  # or via pip: pip install uv"
    exit 1
fi

echo "✅ UV package manager found: $(uv --version)"

# Check if Python 3.10+ is available (UV will handle the specific version)
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3.10 or higher is required but not found"
    echo "Please install Python 3.10+ or let UV install it automatically"
    exit 1
fi

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "⚠️  Warning: Python 3.10+ recommended. Found: $python_version"
    echo "UV will install the correct Python version if needed"
fi

echo "✅ Python version: $python_version"

# Install project dependencies using UV
echo "📦 Installing project dependencies with UV..."
uv sync

# Install development dependencies
echo "📥 Installing development dependencies..."
uv sync --group dev

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "⚠️  Please edit .env file with your configuration"
else
    echo "✅ .env file already exists"
fi

echo
echo "=== Setup Complete! ==="
echo
echo "To activate the UV environment:"
echo "  source .venv/bin/activate"
echo "  # or use: uv run <command>"
echo
echo "To deactivate the virtual environment:"
echo "  deactivate"
echo
echo "To run the MCP server:"
echo "  uv run python mcp_server.py"
echo "  # or: source .venv/bin/activate && python mcp_server.py"
echo
echo "To run the example:"
echo "  uv run python examples/basic_usage.py"
echo
echo "To run tests:"
echo "  uv run pytest"
echo
echo "To run the TUI interface:"
echo "  uv run python -m src.tui_launcher"
echo
echo "To run the TCP server:"
echo "  uv run python -m src.server_launcher --transport tcp"
