# Output Directory Configuration

This document describes how to configure the output directory for generated files in DShield MCP.

## Overview

DShield MCP generates various output files including:
- PDF reports from LaTeX templates
- LaTeX source files
- Compilation logs
- Temporary working files

All generated files are written to a configurable output directory that is separate from the application installation directory for security and portability.

## Default Behavior

By default, all output files are written to:
- **Unix/Linux/macOS**: `~/dshield-mcp-output`
- **Windows**: `C:\Users\<username>\dshield-mcp-output`

The directory is created automatically if it doesn't exist.

## Configuration Methods

### 1. YAML Configuration File

Add the `output_directory` setting to your `user_config.yaml` file:

```yaml
# Output directory for generated files
output_directory: ~/dshield-mcp-output

# Other configuration settings...
query:
  default_page_size: 100
  # ...
```

**Examples:**

```yaml
# Use home directory (default)
output_directory: ~/dshield-mcp-output

# Use absolute path
output_directory: /var/log/dshield-mcp/outputs

# Use relative path (relative to home directory)
output_directory: ~/Documents/security-reports

# Windows example
output_directory: C:\Users\username\Documents\dshield-outputs
```

### 2. Environment Variable

Set the `DMC_OUTPUT_DIRECTORY` environment variable:

```bash
# Unix/Linux/macOS
export DMC_OUTPUT_DIRECTORY=/custom/path/to/outputs

# Windows (Command Prompt)
set DMC_OUTPUT_DIRECTORY=C:\custom\path\to\outputs

# Windows (PowerShell)
$env:DMC_OUTPUT_DIRECTORY = "C:\custom\path\to\outputs"
```

### 3. Configuration Precedence

Settings are applied in the following order (highest to lowest priority):

1. **Environment Variable**: `DMC_OUTPUT_DIRECTORY`
2. **YAML Config**: `output_directory` in `user_config.yaml`
3. **Default**: `~/dshield-mcp-output`

## Platform-Specific Examples

### macOS

```yaml
# user_config.yaml
output_directory: ~/Documents/dshield-reports
```

```bash
# Environment variable
export DMC_OUTPUT_DIRECTORY=~/Documents/dshield-reports
```

### Linux

```yaml
# user_config.yaml
output_directory: /var/log/dshield-mcp/outputs
```

```bash
# Environment variable
export DMC_OUTPUT_DIRECTORY=/var/log/dshield-mcp/outputs
```

### Windows

```yaml
# user_config.yaml
output_directory: C:\Users\username\Documents\dshield-outputs
```

```cmd
# Command Prompt
set DMC_OUTPUT_DIRECTORY=C:\Users\username\Documents\dshield-outputs
```

```powershell
# PowerShell
$env:DMC_OUTPUT_DIRECTORY = "C:\Users\username\Documents\dshield-outputs"
```

## Security Considerations

### File Permissions

Ensure the output directory has appropriate permissions:

```bash
# Create directory with restricted permissions
mkdir -p ~/dshield-mcp-output
chmod 700 ~/dshield-mcp-output

# For shared systems, consider group permissions
chmod 750 ~/dshield-mcp-output
chgrp security-team ~/dshield-mcp-output
```

### Path Validation

The system validates the output directory path:
- Expands user home directory (`~`)
- Expands environment variables (`$VAR`)
- Converts to absolute path
- Creates directory if it doesn't exist

### Security Best Practices

1. **Avoid System Directories**: Don't use `/tmp`, `/var/tmp`, or other system directories
2. **User-Owned**: Use directories owned by the running user
3. **Restricted Access**: Limit access to the output directory
4. **Regular Cleanup**: Implement regular cleanup of old output files

## Integration with LaTeX Tools

The output directory is used by all LaTeX template tools:

```python
from src.latex_template_tools import LaTeXTemplateTools

# Uses configured output directory
tools = LaTeXTemplateTools()

# Generate document (outputs to configured directory)
result = await tools.generate_document(
    template_name="Attack_Report",
    document_data={"title": "Security Analysis"},
    output_format="pdf"
)
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   # Check directory permissions
   ls -la ~/dshield-mcp-output
   
   # Fix permissions
   chmod 755 ~/dshield-mcp-output
   ```

2. **Directory Not Created**
   ```bash
   # Check if parent directory exists
   ls -la ~/
   
   # Create manually if needed
   mkdir -p ~/dshield-mcp-output
   ```

3. **Path Expansion Issues**
   ```bash
   # Test path expansion
   echo ~/dshield-mcp-output
   echo $DMC_OUTPUT_DIRECTORY
   ```

### Debugging

Enable debug logging to see output directory resolution:

```yaml
# user_config.yaml
logging:
  log_level: DEBUG
```

### Validation

Test your configuration:

```python
from src.user_config import get_user_config

config = get_user_config()
print(f"Output directory: {config.output_directory}")
```

## Migration from Previous Versions

If you were previously using the `output/` directory in the project root:

1. **Backup existing files**:
   ```bash
   cp -r output/ ~/dshield-mcp-output/
   ```

2. **Update configuration**:
   ```yaml
   # user_config.yaml
   output_directory: ~/dshield-mcp-output
   ```

3. **Remove old directory** (optional):
   ```bash
   rm -rf output/
   ```

## Related Documentation

- [User Configuration Management](README.md#user-configuration-management)
- [LaTeX Template Tools](../src/latex_template_tools.py)
- [API Documentation](API_DOCUMENTATION.md) 