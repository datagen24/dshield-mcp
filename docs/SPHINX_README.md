# Sphinx Documentation Setup

This directory contains the Sphinx documentation configuration for DShield MCP, designed for Read the Docs hosting.

## Overview

The project now supports two documentation systems:

1. **Sphinx** (this setup) - For Read the Docs hosting with comprehensive user and developer guides
2. **pdoc** (existing) - For local API documentation generation

## Directory Structure

```
docs/
├── source/              # Sphinx source files
│   ├── conf.py         # Sphinx configuration
│   ├── index.rst       # Main documentation entry point
│   ├── api/            # API reference documentation
│   ├── user-guide/     # User documentation
│   ├── developer-guide/ # Developer documentation
│   └── implementation/ # Implementation guides
├── build/              # Generated HTML output (gitignored)
├── requirements.txt    # Sphinx dependencies for RTD
└── SPHINX_README.md    # This file
```

## Building Documentation Locally

### Prerequisites

Install Sphinx and dependencies:

```bash
# Using UV (recommended)
uv sync --group dev

# Or using pip
pip install -r docs/requirements.txt
```

### Build HTML Documentation

```bash
# Build HTML documentation
uv run sphinx-build -b html docs/source docs/build/html

# Or use make (if available)
cd docs
make html
```

### View Documentation

```bash
# Open in browser (macOS)
open docs/build/html/index.html

# Or Linux
xdg-open docs/build/html/index.html
```

### Clean Build

```bash
# Remove build artifacts
rm -rf docs/build/

# Or use make
cd docs
make clean
```

## Read the Docs Configuration

The `.readthedocs.yaml` file in the project root configures how RTD builds the documentation:

```yaml
version: 2

build:
  os: ubuntu-22.04
  tools:
    python: "3.12"

sphinx:
  configuration: docs/source/conf.py
  fail_on_warning: false

formats:
  - pdf
  - epub

python:
  install:
    - method: pip
      path: .
      extra_requirements:
        - dev
    - requirements: docs/requirements.txt
```

## Sphinx Configuration Highlights

### Extensions Enabled

- `sphinx.ext.autodoc` - Auto-generate API docs from docstrings
- `sphinx.ext.napoleon` - Support for Google-style docstrings
- `sphinx.ext.viewcode` - Add links to highlighted source code
- `sphinx.ext.intersphinx` - Link to other project documentation
- `sphinx.ext.autosummary` - Generate autodoc summaries
- `myst_parser` - Support for Markdown files

### Theme

- **sphinx_rtd_theme** - Read the Docs theme for consistent appearance

### Mock Imports

External dependencies are mocked during doc build to avoid import errors:

- elasticsearch, aiohttp, structlog, pydantic, etc.

See `docs/source/conf.py` for the complete list.

## Documentation Structure

### User Guide

Located in `docs/source/user-guide/`:

- `usage.md` - Detailed usage examples
- `configuration.md` - Configuration and setup
- `error-handling.md` - Error handling guide
- `output-directory.md` - Output directory configuration

### Developer Guide

Located in `docs/source/developer-guide/`:

- `architecture.md` - System architecture overview
- `testing.md` - Testing guide and best practices
- `contributing.md` - Contributing guidelines
- `changelog.md` - Change history

### Implementation Guides

Located in `docs/source/implementation/`:

- `pagination.md` - Pagination implementation
- `streaming.md` - Streaming implementation
- `campaign-analysis.md` - Campaign analysis system
- `statistical-analysis.md` - Statistical analysis tools
- `threat-intelligence.md` - Threat intelligence integration

### API Reference

Located in `docs/source/api/`:

- `modules.rst` - Module overview
- `tools.rst` - MCP tools reference
- `clients.rst` - Client reference
- `analyzers.rst` - Analyzer reference
- `utilities.rst` - Utilities reference

## Markdown Support

Sphinx can parse both reStructuredText (`.rst`) and Markdown (`.md`) files via the MyST parser.

### Including Existing Markdown Files

Use the `include` directive to incorporate existing documentation:

```markdown
# My Page

\```{include} ../../EXISTING_DOC.md
:relative-docs: docs/
:relative-images:
\```
```

## Publishing to Read the Docs

### Setup

1. Create an account on [readthedocs.org](https://readthedocs.org)
2. Import your GitHub repository
3. RTD will automatically detect `.readthedocs.yaml`
4. Builds will trigger automatically on each push

### Build Status

Monitor builds at: `https://readthedocs.org/projects/your-project-name/builds/`

### Documentation URL

Once published, docs will be available at:
- Latest: `https://your-project-name.readthedocs.io/en/latest/`
- Stable: `https://your-project-name.readthedocs.io/en/stable/`

## Continuous Integration

Sphinx builds can be added to your CI pipeline:

```yaml
# GitHub Actions example
- name: Build Sphinx docs
  run: |
    pip install -r docs/requirements.txt
    sphinx-build -W -b html docs/source docs/build/html
```

The `-W` flag treats warnings as errors.

## Troubleshooting

### Build Warnings

```bash
# Build with verbose output
sphinx-build -v -b html docs/source docs/build/html

# Show full traceback on errors
sphinx-build -T -b html docs/source docs/build/html
```

### Import Errors

If you see import errors during build:

1. Check that the module is in `autodoc_mock_imports` in `conf.py`
2. Verify the module path is correct
3. Ensure Python can find the `src/` directory

### Missing Dependencies

```bash
# Reinstall Sphinx dependencies
pip install -r docs/requirements.txt

# Or with UV
uv sync --group dev
```

## Comparison: Sphinx vs pdoc

| Feature | Sphinx | pdoc |
|---------|--------|------|
| **RTD Integration** | Native, seamless | Custom build commands |
| **Markdown Support** | Yes (via MyST) | Limited |
| **User Guides** | Excellent | Not designed for this |
| **API Docs** | Good | Excellent |
| **Customization** | Extensive | Limited |
| **Build Speed** | Slower | Faster |
| **Search** | Built-in | Basic |
| **Cross-references** | Powerful | Limited |

**Recommendation**: Use Sphinx for RTD and comprehensive docs, keep pdoc for quick local API reference.

## Maintenance

### Updating Dependencies

```bash
# Update Sphinx and extensions
uv sync --group dev

# Or update requirements.txt
pip install --upgrade -r docs/requirements.txt
```

### Adding New Pages

1. Create `.rst` or `.md` file in appropriate directory
2. Add to `toctree` in parent index file
3. Rebuild documentation

Example `toctree`:

```rst
.. toctree::
   :maxdepth: 2
   :caption: Section Name

   page1
   page2
   subdirectory/page3
```

## Resources

- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [Read the Docs Documentation](https://docs.readthedocs.io/)
- [MyST Parser](https://myst-parser.readthedocs.io/)
- [sphinx_rtd_theme](https://sphinx-rtd-theme.readthedocs.io/)

## Support

For questions or issues:

1. Check the [Sphinx FAQ](https://www.sphinx-doc.org/en/master/faq.html)
2. Review [RTD documentation](https://docs.readthedocs.io/)
3. Open an issue in the project repository
