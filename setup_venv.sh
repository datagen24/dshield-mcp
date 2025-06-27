#!/bin/bash

# DShield MCP - Virtual Environment Setup Script
# This script creates a virtual environment and installs all dependencies

set -e  # Exit on any error

echo "=== DShield MCP Virtual Environment Setup ==="
echo

# Check if Python 3.8+ is available
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Error: Python 3.8 or higher is required. Found: $python_version"
    exit 1
fi

echo "✅ Python version: $python_version"

# Check if virtualenv is available
if ! command -v python3 -m venv &> /dev/null; then
    echo "❌ Error: python3 -m venv is not available"
    echo "Please install python3-venv package:"
    echo "  Ubuntu/Debian: sudo apt-get install python3-venv"
    echo "  CentOS/RHEL: sudo yum install python3-venv"
    echo "  macOS: brew install python3"
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Install elasticsearch Python client with version from env or default
ELASTICSEARCH_PY_VERSION=${ELASTICSEARCH_PY_VERSION:-8.18.1}
pip install "elasticsearch==${ELASTICSEARCH_PY_VERSION}"

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
echo "To activate the virtual environment:"
echo "  source venv/bin/activate"
echo
echo "To deactivate the virtual environment:"
echo "  deactivate"
echo
echo "To run the MCP server:"
echo "  source venv/bin/activate"
echo "  python mcp_server.py"
echo
echo "To run the example:"
echo "  source venv/bin/activate"
echo "  python examples/basic_usage.py"
echo
echo "To test the installation:"
echo "  source venv/bin/activate"
echo "  python test_installation.py" 