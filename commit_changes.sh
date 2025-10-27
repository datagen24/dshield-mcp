#!/bin/bash

# Script to commit changes and prepare for merge

echo "=== Committing Changes ==="

# Check git status
echo "1. Checking git status..."
git status --porcelain

# Add all changes
echo "2. Adding all changes..."
git add .

# Check what will be committed
echo "3. Changes to be committed:"
git diff --cached --name-only

# Commit with descriptive message
echo "4. Committing changes..."
git commit -m "Fix Elasticsearch connection and restore 1Password secrets resolution

- Fix missing structlog dependency by ensuring virtual environment is used
- Restore 1Password CLI secrets resolution in config_loader.py
- Add lazy connection to Elasticsearch client to prevent startup failures
- Add better error handling for connection issues
- Add test_elasticsearch_connection tool for debugging
- Create test scripts for server startup and secrets resolution
- Preserve original Elasticsearch configuration and credentials"

# Show the commit
echo "5. Commit details:"
git log --oneline -1

echo "=== Changes committed successfully! ==="
echo "You can now push to your branch or create a pull request."
