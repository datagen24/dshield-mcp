#!/usr/bin/env python3
"""
Build API documentation for DShield MCP using pdoc.

This script generates comprehensive API documentation from the source code,
including all modules, classes, functions, and their docstrings.
Generates both HTML and Markdown formats.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Optional


def run_command(cmd: list[str], cwd: Optional[Path] = None) -> int:
    """
    Run a command and return the exit code.
    
    Args:
        cmd: Command to run as a list of strings
        cwd: Working directory for the command
        
    Returns:
        Exit code of the command
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True
        )
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
            
        return result.returncode
    except Exception as e:
        print(f"Error running command {' '.join(cmd)}: {e}", file=sys.stderr)
        return 1


def check_pdoc_installed() -> bool:
    """
    Check if pdoc is installed in the current environment.
    
    Returns:
        True if pdoc is available, False otherwise
    """
    return run_command([sys.executable, "-m", "pdoc", "--version"]) == 0


def install_pdoc() -> bool:
    """
    Install pdoc using pip.
    
    Returns:
        True if installation was successful, False otherwise
    """
    print("Installing pdoc...")
    return run_command([sys.executable, "-m", "pip", "install", "pdoc>=14.0.0"]) == 0


def clean_output_directory(output_dir: Path) -> None:
    """
    Clean the output directory before generating new documentation.
    
    Args:
        output_dir: Path to the output directory
    """
    if output_dir.exists():
        print(f"Cleaning output directory: {output_dir}")
        shutil.rmtree(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)


def generate_html_documentation(project_root: Path, output_dir: Path) -> bool:
    """
    Generate HTML API documentation using pdoc (v15+ CLI syntax).
    
    Args:
        project_root: Path to the project root directory
        output_dir: Path to the output directory for documentation
        
    Returns:
        True if generation was successful, False otherwise
    """
    print(f"Generating HTML API documentation to: {output_dir}")
    
    # Build the pdoc command for v15+ HTML generation
    cmd = [
        sys.executable, "-m", "pdoc",
        str(project_root / "src"),
        "--output-dir", str(output_dir)
    ]
    
    return run_command(cmd, cwd=project_root) == 0


def generate_markdown_documentation(project_root: Path, output_dir: Path) -> bool:
    """
    Generate Markdown API documentation using pydoc-markdown.
    
    Args:
        project_root: Path to the project root directory
        output_dir: Path to the output directory for documentation
        
    Returns:
        True if generation was successful, False otherwise
    """
    markdown_dir = output_dir / "markdown"
    print(f"Generating Markdown API documentation to: {markdown_dir}")
    
    # Create markdown directory
    markdown_dir.mkdir(parents=True, exist_ok=True)
    
    # Try using pydoc-markdown with the current Python executable
    config_file = project_root / "pydoc-markdown.yml"
    cmd = [
        sys.executable, "-m", "pydoc_markdown",
        str(config_file)
    ]
    
    result = run_command(cmd, cwd=project_root)
    if result == 0:
        return True
    
    # Fallback: try direct pydoc-markdown command
    print("Fallback: trying direct pydoc-markdown command...")
    cmd = [
        "pydoc-markdown",
        str(config_file)
    ]
    
    return run_command(cmd, cwd=project_root) == 0


def create_index_file(output_dir: Path) -> None:
    """
    Create an index.html file that redirects to the main documentation.
    
    Args:
        output_dir: Path to the output directory
    """
    index_content = """<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>DShield MCP API Documentation</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            line-height: 1.6;
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        .nav {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-bottom: 30px;
        }
        .nav a {
            display: inline-block;
            padding: 12px 24px;
            background-color: #007acc;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 500;
        }
        .nav a:hover {
            background-color: #005a9e;
        }
        .description {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
        }
        .features {
            background-color: #f5f5f5;
            padding: 20px;
            border-radius: 8px;
            margin-top: 30px;
        }
        .features h3 {
            margin-top: 0;
        }
        .features ul {
            margin-bottom: 0;
        }
    </style>
</head>
<body>
    <div class=\"header\">
        <h1>DShield MCP API Documentation</h1>
        <p>Comprehensive API reference for DShield MCP - Elastic SIEM Integration Package</p>
    </div>
    
    <div class=\"nav\">
        <a href=\"src/index.html\">HTML Documentation</a>
        <a href=\"markdown/src/index.md\">Markdown Documentation</a>
    </div>
    
    <div class=\"description\">
        <p>Choose your preferred format:</p>
        <ul style=\"list-style: none; padding: 0;\">
            <li><strong>HTML:</strong> Interactive, searchable documentation with navigation</li>
            <li><strong>Markdown:</strong> Plain text format ideal for AI ingestion and version control</li>
        </ul>
    </div>
    
    <div class=\"features\">
        <h3>Documentation Features</h3>
        <ul>
            <li>Complete API reference for all modules and functions</li>
            <li>Type annotations and parameter descriptions</li>
            <li>Usage examples and code snippets</li>
            <li>Cross-references between modules</li>
            <li>Search functionality (HTML version)</li>
            <li>AI-friendly Markdown format</li>
        </ul>
    </div>
</body>
</html>"""
    
    index_file = output_dir / "index.html"
    index_file.write_text(index_content)
    print(f"Created index file: {index_file}")


def create_markdown_index(output_dir: Path) -> None:
    """
    Create a Markdown index file for the documentation.
    
    Args:
        output_dir: Path to the output directory
    """
    markdown_index_content = """# DShield MCP API Documentation

This directory contains the complete API documentation for the DShield MCP package in Markdown format.

## Overview

The DShield MCP package provides a Model Context Protocol (MCP) server that integrates with DShield's threat intelligence platform and Elasticsearch for security information and event management (SIEM) operations.

## Documentation Structure

- `src/` - Main package documentation
  - `index.md` - Package overview and main entry point
  - `campaign_analyzer.md` - Campaign analysis tools
  - `data_processor.md` - Data processing utilities
  - `elasticsearch_client.md` - Elasticsearch integration
  - `dshield_client.md` - DShield API integration
  - And more...

## Usage

This Markdown documentation is designed for:
- AI ingestion and analysis
- Version control integration
- Plain text processing
- Documentation generation tools

## Quick Reference

### Core Modules

- **MCP Server**: Main server implementation (`mcp_server.py`)
- **Campaign Analyzer**: Threat campaign analysis (`campaign_analyzer.py`)
- **Data Processor**: Data processing and validation (`data_processor.py`)
- **Elasticsearch Client**: SIEM data operations (`elasticsearch_client.py`)
- **DShield Client**: Threat intelligence integration (`dshield_client.py`)

### Configuration

- **Config Loader**: YAML configuration with 1Password integration (`config_loader.py`)
- **User Config**: User preferences and settings (`user_config.py`)
- **1Password Secrets**: Secure secrets management (`op_secrets.py`)

### Utilities

- **Data Dictionary**: Schema management (`data_dictionary.py`)
- **Context Injector**: AI context utilities (`context_injector.py`)
- **Models**: Pydantic data models (`models.py`)

## Building Documentation

To regenerate this documentation:

```bash
./scripts/build_api_docs.sh
```

This will create both HTML and Markdown versions of the API documentation.
"""
    
    markdown_index_file = output_dir / "README.md"
    markdown_index_file.write_text(markdown_index_content)
    print(f"Created Markdown index: {markdown_index_file}")


def main() -> int:
    """
    Main function to build API documentation.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Get project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Define output directory
    output_dir = project_root / "docs" / "api"
    
    print("DShield MCP API Documentation Builder")
    print("=" * 40)
    
    # Check if pdoc is installed
    if not check_pdoc_installed():
        print("pdoc not found. Attempting to install...")
        if not install_pdoc():
            print("Failed to install pdoc. Please install it manually:")
            print("  pip install pdoc>=14.0.0")
            return 1
    
    # Clean output directory
    clean_output_directory(output_dir)
    
    # Generate HTML documentation
    if not generate_html_documentation(project_root, output_dir):
        print("Failed to generate HTML API documentation", file=sys.stderr)
        return 1
    
    # Generate Markdown documentation
    if not generate_markdown_documentation(project_root, output_dir):
        print("Failed to generate Markdown API documentation", file=sys.stderr)
        return 1
    
    # Create index files
    create_index_file(output_dir)
    create_markdown_index(output_dir)
    
    print("\n" + "=" * 40)
    print("API documentation generated successfully!")
    print(f"Documentation location: {output_dir}")
    print(f"HTML documentation: {output_dir / 'index.html'}")
    print(f"Markdown documentation: {output_dir / 'markdown'}")
    print("\nFormats available:")
    print("- HTML: Interactive, searchable documentation")
    print("- Markdown: AI-friendly plain text format")
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 