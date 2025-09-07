#!/bin/bash
# Build API documentation for DShield MCP
# This script generates comprehensive API documentation using pdoc

set -e  # Exit on any error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "DShield MCP API Documentation Builder"
echo "======================================"

# Check if we're in a virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "Warning: Not running in a virtual environment"
    echo "Consider activating your virtual environment first:"
    echo "  source venv/bin/activate  # or your venv path"
    echo ""
fi

# Change to project root
cd "$PROJECT_ROOT"

# Run the Python build script
python scripts/build_api_docs.py

echo ""
echo "Build completed successfully!"
echo "You can now open docs/api/index.html in your browser to view the documentation."
