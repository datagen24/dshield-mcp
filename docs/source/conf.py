# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
from pathlib import Path

# -- Path setup --------------------------------------------------------------
# Add the project source directory to the Python path so autodoc can find modules
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'DShield MCP'
copyright = '2025, DShield MCP Team'
author = 'DShield MCP Team'
release = '1.0.0'
version = '1.0.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',           # Auto-generate API docs from docstrings
    'sphinx.ext.napoleon',          # Support for Google-style docstrings
    'sphinx.ext.viewcode',          # Add links to highlighted source code
    'sphinx.ext.intersphinx',       # Link to other project's documentation
    'sphinx.ext.autosummary',       # Generate autodoc summaries
    'sphinx.ext.coverage',          # Check documentation coverage
    'sphinx.ext.githubpages',       # Create .nojekyll file for GitHub Pages
    'myst_parser',                  # Support for Markdown files
]

# Napoleon settings for Google-style docstrings (as specified in your .cursorrules)
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}
autodoc_typehints = 'description'
autodoc_typehints_description_target = 'documented'

# Mock imports for modules that can't be imported during doc build
autodoc_mock_imports = [
    'elasticsearch',
    'aiohttp',
    'httpx',
    'structlog',
    'pydantic',
    'pydantic_settings',
    'dotenv',
    'asyncio_mqtt',
    'dateutil',
    'numpy',
    'scipy',
    'sklearn',
    'textual',
    'rich',
    'psutil',
    'cryptography',
    'yaml',
    'mcp',
    'networkx',
]

# Autosummary settings
autosummary_generate = True
autosummary_imported_members = False

# MyST (Markdown) parser settings
myst_enable_extensions = [
    "colon_fence",      # ::: fences for directives
    "deflist",          # Definition lists
    "fieldlist",        # Field lists
    "html_admonition",  # HTML admonitions
    "html_image",       # HTML images
    "linkify",          # Auto-detect URLs
    "replacements",     # Text replacements
    "smartquotes",      # Smart quotes
    "strikethrough",    # ~~strikethrough~~
    "substitution",     # Variable substitution
    "tasklist",         # Task lists
]

# Support both .rst and .md files
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# Templates path
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = []

# The master document (main table of contents)
master_doc = 'index'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Theme options
html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'includehidden': True,
    'titles_only': False,
    'display_version': True,
}

# HTML context
html_context = {
    'display_github': True,
    'github_user': 'datagen24',
    'github_repo': 'dshield-mcp',
    'github_version': 'main',
    'conf_py_path': '/docs/source/',
}

# Output file base name for HTML help builder
htmlhelp_basename = 'DShieldMCPdoc'

# -- Options for intersphinx extension ---------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html#configuration

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'elasticsearch': ('https://elasticsearch-py.readthedocs.io/en/stable/', None),
    'aiohttp': ('https://docs.aiohttp.org/en/stable/', None),
    'pydantic': ('https://docs.pydantic.dev/latest/', None),
}

# -- Options for coverage extension ------------------------------------------
coverage_show_missing_items = True
