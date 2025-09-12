#!/usr/bin/env python3
"""
Build API documentation for DShield MCP using pdoc with incremental updates.

This script generates comprehensive API documentation from the source code,
including all modules, classes, functions, and their docstrings.

Key improvements:
- Generates into a temporary staging directory and synchronizes only changed files
  into ``docs/api`` to avoid scorched-earth updates and oversized Git commits.
- Deletes files in the target only when they no longer exist in the staged output.
- Supports ``--dry-run`` to preview changes and ``--force`` to do a full rebuild.

Outputs both HTML and Markdown formats.
"""

import argparse
import ast
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def run_command(cmd: list[str], cwd: Path | None = None) -> int:
    """
    Run a command and return the exit code.

    Args:
        cmd: Command to run as a list of strings
        cwd: Working directory for the command

    Returns:
        Exit code of the command
    """
    try:
        result = subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)

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


def _sha256_file(path: Path) -> str:
    """Compute the SHA-256 hash of a file.

    Args:
        path: Path to file

    Returns:
        Hex digest string
    """
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _files_differ(src: Path, dst: Path) -> bool:
    """Return True if files differ by size or content hash."""
    if not dst.exists():
        return True
    if src.stat().st_size != dst.stat().st_size:
        return True
    return _sha256_file(src) != _sha256_file(dst)


def _write_if_changed(path: Path, content: str) -> bool:
    """Write content to path only if changed.

    Args:
        path: Target file path
        content: Text content

    Returns:
        True if file was written/updated, False if unchanged
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            existing = path.read_text(encoding="utf-8")
            if existing == content:
                return False
        except Exception:
            # If we cannot read, attempt to overwrite
            pass
    path.write_text(content, encoding="utf-8")
    return True


def sync_directories(
    staged_dir: Path,
    output_dir: Path,
    *,
    dry_run: bool = False,
    delete_removed: bool = True,
) -> dict:
    """Synchronize staged docs to target, updating changed files and removing stale ones.

    Args:
        staged_dir: Temporary staging directory with freshly generated docs
        output_dir: Final documentation directory (docs/api)
        dry_run: If True, only print actions without performing them
        delete_removed: If True, remove files absent in staged_dir

    Returns:
        Summary dictionary with counts of copied, deleted, unchanged files
    """
    copied = 0
    deleted = 0
    unchanged = 0

    output_dir.mkdir(parents=True, exist_ok=True)

    # Build file lists
    staged_files = {
        p.relative_to(staged_dir)
        for p in staged_dir.rglob("*")
        if p.is_file()
    }

    output_files = {
        p.relative_to(output_dir)
        for p in output_dir.rglob("*")
        if p.is_file()
    }

    # Copy new/changed files
    for rel in sorted(staged_files):
        src = staged_dir / rel
        dst = output_dir / rel
        if _files_differ(src, dst):
            print(f"UPDATE: {rel}")
            if not dry_run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            copied += 1
        else:
            unchanged += 1

    # Delete removed files
    if delete_removed:
        for rel in sorted(output_files - staged_files):
            target = output_dir / rel
            print(f"REMOVE: {rel}")
            if not dry_run:
                try:
                    target.unlink()
                except FileNotFoundError:
                    pass
            deleted += 1

    return {"copied": copied, "deleted": deleted, "unchanged": unchanged}


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
    cmd = [sys.executable, "-m", "pdoc", str(project_root / "src"), "--output-dir", str(output_dir)]

    return run_command(cmd, cwd=project_root) == 0


def generate_markdown_documentation(project_root: Path, output_dir: Path) -> bool:
    """
    Generate Markdown API documentation by extracting docstrings from source files.

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

    try:
        # Add src to Python path
        src_path = str(project_root / "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        # Generate documentation for all modules in src
        src_dir = project_root / "src"
        created_files = 0

        # Find all Python modules
        for py_file in src_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            try:
                # Read the source file
                source_code = py_file.read_text(encoding="utf-8")

                # Parse the AST
                tree = ast.parse(source_code)

                # Generate markdown content
                markdown_content = generate_module_markdown(py_file, tree, source_code)

                # Create output file path
                rel_path = py_file.relative_to(src_dir)
                module_name = str(rel_path.with_suffix("")).replace("/", ".")
                output_file = markdown_dir / f"{module_name}.md"
                output_file.parent.mkdir(parents=True, exist_ok=True)

                # Write markdown content
                # Only write if changed to keep staging clean and deterministic
                _write_if_changed(output_file, markdown_content)
                created_files += 1

            except Exception as e:
                print(f"Warning: Could not document {py_file}: {e}")
                continue

        if created_files == 0:
            print(f"ERROR: No markdown files created in {markdown_dir}")
            return False

        print(f"Created {created_files} markdown files")
        return True

    except Exception as e:
        print(f"ERROR: Failed to generate markdown documentation: {e}")
        return False


def generate_module_markdown(file_path: Path, tree: ast.Module, source_code: str) -> str:
    """
    Generate markdown documentation for a single module.

    Args:
        file_path: Path to the Python file
        tree: Parsed AST of the file
        source_code: Raw source code

    Returns:
        Markdown content for the module
    """
    lines = []

    # Module header
    module_name = file_path.stem
    lines.append(f"# {module_name}")
    lines.append("")

    # Module docstring
    if (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
    ):
        if isinstance(tree.body[0].value.value, str):
            docstring = tree.body[0].value.value.strip()
            if docstring:
                lines.append(docstring)
                lines.append("")

    # Process classes and functions
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            lines.extend(generate_class_markdown(node))
        elif isinstance(node, ast.FunctionDef):
            lines.extend(generate_function_markdown(node))

    return "\n".join(lines)


def generate_class_markdown(node: ast.ClassDef) -> list[str]:
    """Generate markdown for a class definition."""
    lines = []
    lines.append(f"## {node.name}")
    lines.append("")

    # Class docstring
    if (
        node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    ):
        if isinstance(node.body[0].value.value, str):
            docstring = node.body[0].value.value.strip()
            if docstring:
                lines.append(docstring)
                lines.append("")

    # Methods
    for item in node.body:
        if isinstance(item, ast.FunctionDef):
            lines.extend(generate_method_markdown(item))

    return lines


def generate_function_markdown(node: ast.FunctionDef) -> list[str]:
    """Generate markdown for a function definition."""
    lines = []
    lines.append(f"### {node.name}")
    lines.append("")

    # Function signature
    args = []
    for arg in node.args.args:
        args.append(arg.arg)
    signature = f"def {node.name}({', '.join(args)})"
    lines.append("```python")
    lines.append(signature)
    lines.append("```")
    lines.append("")

    # Function docstring
    if (
        node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    ):
        if isinstance(node.body[0].value.value, str):
            docstring = node.body[0].value.value.strip()
            if docstring:
                lines.append(docstring)
                lines.append("")

    return lines


def generate_method_markdown(node: ast.FunctionDef) -> list[str]:
    """Generate markdown for a method definition."""
    lines = []
    lines.append(f"#### {node.name}")
    lines.append("")

    # Method signature
    args = []
    for arg in node.args.args:
        args.append(arg.arg)
    signature = f"def {node.name}({', '.join(args)})"
    lines.append("```python")
    lines.append(signature)
    lines.append("```")
    lines.append("")

    # Method docstring
    if (
        node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    ):
        if isinstance(node.body[0].value.value, str):
            docstring = node.body[0].value.value.strip()
            if docstring:
                lines.append(docstring)
                lines.append("")

    return lines


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
            <li><strong>Markdown:</strong> Plain text format ideal for AI ingestion and
            version control</li>
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
    if _write_if_changed(index_file, index_content):
        print(f"Created/updated index file: {index_file}")


def verify_documentation_exists(output_dir: Path) -> dict:
    """
    Verify documentation was actually created.

    Args:
        output_dir: Path to the output directory

    Returns:
        Dictionary with verification results
    """
    results = {"html_files": 0, "markdown_files": 0, "total_size": 0}

    # Check HTML files
    html_dir = output_dir / "src"
    if html_dir.exists():
        html_files = list(html_dir.glob("**/*.html"))
        results["html_files"] = len(html_files)

    # Check Markdown files
    md_dir = output_dir / "markdown"
    if md_dir.exists():
        md_files = list(md_dir.glob("**/*.md"))
        results["markdown_files"] = len(md_files)

        # Calculate total size
        for md_file in md_files:
            results["total_size"] += md_file.stat().st_size

    return results


def create_markdown_index(output_dir: Path) -> None:
    """
    Create a Markdown index file for the documentation.

    Args:
        output_dir: Path to the output directory
    """
    markdown_index_content = """# DShield MCP API Documentation

This directory contains the complete API documentation for the DShield MCP package in
Markdown format.

## Overview

The DShield MCP package provides a Model Context Protocol (MCP) server that integrates
with DShield's threat intelligence platform and Elasticsearch for security information and
event management (SIEM) operations.

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
    if _write_if_changed(markdown_index_file, markdown_index_content):
        print(f"Created/updated Markdown index: {markdown_index_file}")


def main() -> int:
    """
    Main function to build API documentation.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(description="Build API docs with incremental updates.")
    parser.add_argument("--force", action="store_true", help="Force full rebuild (clean target before syncing)")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying files")
    parser.add_argument(
        "--no-delete",
        action="store_true",
        help="Do not delete files from target that are missing in staged output",
    )
    args = parser.parse_args()

    # Env var overrides for CI or scripted usage
    force = args.force or os.environ.get("DOCS_FORCE_REBUILD") == "1"
    dry_run = args.dry_run or os.environ.get("DOCS_DRY_RUN") == "1"
    delete_removed = not args.no_delete and os.environ.get("DOCS_NO_DELETE") != "1"

    # Get project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Define output directory (final location)
    output_dir = project_root / "docs" / "api"

    print("DShield MCP API Documentation Builder")
    print("=" * 40)
    print(f"Target directory: {output_dir}")
    print(f"Options: force={force}, dry_run={dry_run}, delete_removed={delete_removed}")

    # Check if pdoc is installed
    if not check_pdoc_installed():
        print("pdoc not found. Attempting to install...")
        if not install_pdoc():
            print("Failed to install pdoc. Please install it manually:")
            print("  pip install pdoc>=14.0.0")
            return 1

    # Full clean if forced
    if force and not dry_run and output_dir.exists():
        print(f"Force clean: removing {output_dir}")
        shutil.rmtree(output_dir)

    # Always build into a staging directory first
    with TemporaryDirectory(prefix="dshield-docs-") as tmp:
        staged_dir = Path(tmp)

        # Generate HTML documentation into staging
        if not generate_html_documentation(project_root, staged_dir):
            print("Failed to generate HTML API documentation", file=sys.stderr)
            return 1

        # Generate Markdown documentation into staging
        if not generate_markdown_documentation(project_root, staged_dir):
            print("Failed to generate Markdown API documentation", file=sys.stderr)
            return 1

        # Create index files in staging
        create_index_file(staged_dir)
        create_markdown_index(staged_dir)

        # VERIFY staged files were actually created
        verification = verify_documentation_exists(staged_dir)

        if verification["html_files"] == 0:
            print("ERROR: No HTML files were generated!")
            return 1

        if verification["markdown_files"] == 0:
            print("ERROR: No Markdown files were generated!")
            return 1

        print("Synchronizing staged documentation → target directory...")
        summary = sync_directories(staged_dir, output_dir, dry_run=dry_run, delete_removed=delete_removed)

    # Final verification on target
    verification = verify_documentation_exists(output_dir)

    print("\n" + "=" * 40)
    print("API documentation generated successfully!" if not dry_run else "Dry-run completed.")
    print(f"Documentation location: {output_dir}")
    print(f"HTML documentation: {output_dir / 'index.html'}")
    print(f"Markdown documentation: {output_dir / 'markdown'}")

    print("\nVerification Results:")
    print(f"  HTML files present: {verification['html_files']}")
    print(f"  Markdown files present: {verification['markdown_files']}")
    print(f"  Total documentation size: {verification['total_size'] / 1024:.1f} KB")

    print("\nSync Summary:")
    print(f"  Files updated: {summary['copied']}")
    print(f"  Files unchanged: {summary['unchanged']}")
    if delete_removed:
        print(f"  Files removed: {summary['deleted']}")
    else:
        print("  Files removed: (skipped)")

    print("\nFormats available:")
    print("- HTML: Interactive, searchable documentation")
    print("- Markdown: AI-friendly plain text format")

    return 0


if __name__ == "__main__":
    sys.exit(main())
