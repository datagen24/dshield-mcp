# latex_template_tools

LaTeX Template Automation MCP Tools.

MCP tools for LaTeX template automation and document generation.
Provides functionality to generate complete and fully referenced documents
using modular LaTeX templates.

## LaTeXTemplateTools

MCP tools for LaTeX template automation and document generation.

    Output files are always written to the user-configured output directory (default: ~/dshield-mcp-output).

#### __init__

```python
def __init__(self, template_base_path, output_directory, error_handler)
```

Initialize LaTeXTemplateTools.

        Args:
            template_base_path: Base path for LaTeX templates. Defaults to templates/Attack_Report.
            output_directory: Directory for generated outputs. If None, uses user config.
            error_handler: Optional MCPErrorHandler for structured error responses

#### _find_project_root

```python
def _find_project_root(self)
```

Find the project root directory by looking for setup.py or pyproject.toml.

        Returns:
            Path to the project root directory.

        Raises:
            FileNotFoundError: If project root cannot be found.

#### _check_circuit_breaker

```python
def _check_circuit_breaker(self, operation)
```

Check if circuit breaker allows execution.

        Args:
            operation: Name of the operation being performed

        Returns:
            True if execution is allowed, False if circuit breaker is open

#### _record_circuit_breaker_success

```python
def _record_circuit_breaker_success(self)
```

Record successful operation with circuit breaker.

#### _record_circuit_breaker_failure

```python
def _record_circuit_breaker_failure(self, exception)
```

Record failed operation with circuit breaker.

        Args:
            exception: The exception that occurred

#### get_circuit_breaker_status

```python
def get_circuit_breaker_status(self)
```

Get the current status of the LaTeX compilation circuit breaker.

        Returns:
            Circuit breaker status dictionary or None if not enabled

#### _get_template_path

```python
def _get_template_path(self, template_name)
```

Get the path to a specific template.

        Args:
            template_name: Name of the template

        Returns:
            Path to the template directory

#### _load_template_config

```python
def _load_template_config(self, template_path)
```

Load template configuration from template_info.json.

        Args:
            template_path: Path to the template directory

        Returns:
            Template configuration dictionary

#### _validate_document_data

```python
def _validate_document_data(self, document_data, template_config)
```

Validate document data against template requirements.

        Args:
            document_data: Document data to validate
            template_config: Template configuration

        Returns:
            Validation results

#### _substitute_variables

```python
def _substitute_variables(self, content, document_data)
```

Substitute variables in template content.

        Args:
            content: Template content
            document_data: Data to substitute

        Returns:
            Processed content with variables substituted

#### _copy_template_files

```python
def _copy_template_files(self, template_path, temp_path, include_assets)
```

Copy template files to temporary directory.

        Args:
            template_path: Source template directory
            temp_path: Destination temporary directory
            include_assets: Whether to include assets

#### _copy_output_files

```python
def _copy_output_files(self, temp_path, template_name)
```

Copy output files from temp_path to the configured output directory.

#### _infer_variable_types

```python
def _infer_variable_types(self, template_config)
```

Infer variable types from template configuration.

        Args:
            template_config: Template configuration

        Returns:
            Dictionary mapping variable names to inferred types

#### _get_section_descriptions

```python
def _get_section_descriptions(self, template_path)
```

Get descriptions for template sections.

        Args:
            template_path: Path to template directory

        Returns:
            Dictionary mapping section names to descriptions

#### _generate_example_data

```python
def _generate_example_data(self, template_config)
```

Generate example data for template.

        Args:
            template_config: Template configuration

        Returns:
            Example data dictionary
