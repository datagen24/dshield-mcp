# DShield MCP Documentation

This folder contains comprehensive documentation for the DShield MCP service.

## 📚 Documentation Index

### **Core Documentation**
- **[README.md](../README.md)** - Main project overview and quick start guide (in root directory)

### **Implementation Guides**
- **[PAGINATION_IMPLEMENTATION.md](PAGINATION_IMPLEMENTATION.md)** - Detailed guide for pagination implementation
- **[STREAMING_IMPLEMENTATION.md](STREAMING_IMPLEMENTATION.md)** - Comprehensive streaming functionality guide
- **[CAMPAIGN_ANALYSIS_IMPLEMENTATION.md](CAMPAIGN_ANALYSIS_IMPLEMENTATION.md)** - Advanced campaign analysis and correlation engine (multi-stage, MCP tools, production scale)

### **User Guides**
- **[USAGE.md](USAGE.md)** - Detailed usage examples and API reference
- **[OUTPUT_DIRECTORY_CONFIGURATION.md](OUTPUT_DIRECTORY_CONFIGURATION.md)** - Output directory configuration and security considerations
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and changes
- **[RELEASE_NOTES_v1.0.md](RELEASE_NOTES_v1.0.md)** - Release notes for version 1.0

### **Development & Planning**
- **[Enhancements.md](Enhancements.md)** - Planned features and enhancement roadmap

## 🚀 Quick Navigation

### **Getting Started**
1. Start with the main **[README.md](../README.md)** for installation and basic setup
2. Review **[USAGE.md](USAGE.md)** for detailed usage examples
3. Check **[CHANGELOG.md](CHANGELOG.md)** for recent updates

### **Development**
1. Review **[Enhancements.md](Enhancements.md)** for planned features
2. Check implementation guides for technical details:
   - **[PAGINATION_IMPLEMENTATION.md](PAGINATION_IMPLEMENTATION.md)**
   - **[STREAMING_IMPLEMENTATION.md](STREAMING_IMPLEMENTATION.md)**
   - **[CAMPAIGN_ANALYSIS_IMPLEMENTATION.md](CAMPAIGN_ANALYSIS_IMPLEMENTATION.md)**
   - **[performance_metrics.md](performance_metrics.md)**

### **Releases**
1. **[RELEASE_NOTES_v1.0.md](RELEASE_NOTES_v1.0.md)** - Current release information
2. **[CHANGELOG.md](CHANGELOG.md)** - Complete version history

## 📖 Documentation Structure

```
docs/
├── README.md                    # This documentation index
├── USAGE.md                     # Detailed usage guide
├── OUTPUT_DIRECTORY_CONFIGURATION.md # Output directory configuration guide
├── CHANGELOG.md                 # Version history
├── RELEASE_NOTES_v1.0.md        # Release notes
├── Enhancements.md              # Feature roadmap
├── PAGINATION_IMPLEMENTATION.md # Pagination technical guide
├── STREAMING_IMPLEMENTATION.md  # Streaming technical guide
├── CAMPAIGN_ANALYSIS_IMPLEMENTATION.md # Campaign analysis implementation guide
```

## Dependencies

- **Python Packages:**
  - `elasticsearch` (for Elasticsearch queries and backend integration)
  - `structlog` (for structured logging and error reporting)
  - `aiohttp` / `httpx` (for async HTTP requests; current code uses aiohttp)
  - `pydantic` (for data validation and typing)
  - `pytest` (for running tests)
  - `ruff` (for linting and docstring compliance)
  - `pdoc` (for HTML API documentation generation)
  - `pydoc-markdown` (for Markdown API documentation generation)
- **Elasticsearch:**
  - Requires a running Elasticsearch instance (version 7.x, 8.x, or 9.x; see compatibility notes below)
- **Testing and Documentation Tools:**
  - `pytest` for test automation
  - `ruff` for linting and docstring checks
  - `pdoc` for HTML API docs
  - `pydoc-markdown` for Markdown API docs

See `requirements.txt` and `requirements-dev.txt` for full dependency lists and version constraints.

## 🔗 Related Resources

- **Main Project**: [README.md](../README.md)
- **Development Tools**: [dev_tools/](../dev_tools/)
- **Examples**: [examples/](../examples/)
- **Source Code**: [src/](../src/)

## 📝 Contributing to Documentation

When adding new documentation:

1. **Create new .md files** in this `docs/` folder
2. **Update this index** to include new documents
3. **Follow the naming convention**: `DESCRIPTIVE_NAME.md`
4. **Include cross-references** to related documentation
5. **Keep the main README.md** focused on quick start and overview

## 🎯 Documentation Categories

### **User-Facing**
- Installation and setup
- Usage examples
- API reference
- Troubleshooting

### **Developer-Facing**
- Implementation details
- Architecture decisions
- Enhancement planning
- Technical guides

### **Release Management**
- Version history
- Release notes
- Migration guides
- Breaking changes

## User Configuration Management

DShield MCP supports robust user configuration management, allowing you to customize query, pagination, streaming, performance, security, and logging settings. This system uses a layered approach:

- **user_config.yaml**: Place this file in the project root, `config/`, or `~/.dshield-mcp/`. See `user_config.example.yaml` for all available options and documentation.
- **Environment Variables**: Any setting in `user_config.yaml` can be overridden by an environment variable (see the example file for variable names).
- **Precedence**: Environment variables > user_config.yaml > built-in defaults.
- **Validation**: All settings are validated for correctness. Invalid values are rejected with clear errors.

### Example: user_config.yaml

```yaml
# Output directory for generated files (PDF reports, LaTeX outputs, etc.)
output_directory: ~/dshield-mcp-output

query:
  default_page_size: 100
  max_page_size: 1000
  enable_smart_optimization: true
  fallback_strategy: "aggregate"
  # ...
pagination:
  default_method: "page"
  # ...
# See user_config.example.yaml for all options
```

### Example: Environment Variable Override

```bash
# Output directory
export DMC_OUTPUT_DIRECTORY=/custom/path/to/outputs

# Query settings
export DEFAULT_PAGE_SIZE=50
export ENABLE_SMART_OPTIMIZATION=false
```

### Integration
- All core MCP components (Elasticsearch client, DShield client, server) use the user configuration system for their settings.
- You can update settings at runtime via the `UserConfigManager` API.
- Configuration is validated on load and update; errors are reported immediately.

### Template
- Copy `user_config.example.yaml` to `user_config.yaml` and customize as needed.
- See inline comments in the example file for documentation of each setting.

### Testing
- Run `python dev_tools/test_user_configuration.py` to verify configuration management and integration.

## Transports and OS Targets

- Default transport: STDIO (recommended for analyst workstations)
- Advanced transports: TCP server and Textual TUI
- TCP mode targets: macOS hosts and Red Hat UBI container (planned; container support to be finalized)

## Elasticsearch Configuration

> **Important:**
> The Python Elasticsearch client version in your `requirements.txt` **must match the major version of your Elasticsearch server** for best compatibility. If you are running Elasticsearch 7.x, use the `elasticsearch7` package. For 8.x, use `elasticsearch` v8.x or v9.x with `compatibility_mode` as needed. For 9.x, use `elasticsearch` v9.x.
>
> **To upgrade to a new major version:**
> 1. Upgrade your Elasticsearch server first.
> 2. Then upgrade the Python client in your requirements file.
>
> | Elasticsearch Server | Python Client Package      | Version Constraint Example         |
> |---------------------|---------------------------|------------------------------------|
> | 7.x                 | elasticsearch7            | elasticsearch7>=7.17,<8.0          |
> | 8.x                 | elasticsearch             | elasticsearch>=8.7,<9.0            |
> | 8.x                 | elasticsearch             | elasticsearch>=9.0,<10.0 + compat. |
> | 9.x                 | elasticsearch             | elasticsearch>=9.0,<10.0           |
>
> - If using a newer client with an older server (e.g., 9.x client with 8.x server), set `compatibility_mode: true` in your config.
> - Only pass `compatibility_mode` if your client version is >=8.7.0.

The `elasticsearch` section in `mcp_config.yaml` supports a new option:

- `compatibility_mode` (bool, default: false):
    - If set to `true`, the Python Elasticsearch client will use compatibility headers (e.g., `Accept: application/vnd.elasticsearch+json; compatible-with=8`) to ensure compatibility with Elasticsearch 8.x servers when using a v9 client library.
    - Set this to `true` if you see errors about incompatible Accept headers or if your Elasticsearch server only supports compatibility with version 8 or below.
    - Example:
      ```yaml
      elasticsearch:
        url: "https://your-es-server:9200"
        username: "..."
        password: "..."
        verify_ssl: true
        compatibility_mode: true
        # ... other options ...
      ```
    - If your server and client are the same major version, or you are using an 8.x client, you can leave this as `false`.
