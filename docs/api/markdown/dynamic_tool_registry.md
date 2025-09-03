# dynamic_tool_registry

Dynamic tool registry for DShield MCP server.

## DynamicToolRegistry

Registers tools based on feature availability.

#### __init__

```python
def __init__(self, feature_manager)
```

Initialize the dynamic tool registry.

        Args:
            feature_manager: Feature manager instance

#### register_tools

```python
def register_tools(self, all_tools)
```

Register tools based on available features.

        Args:
            all_tools: List of all available tool names

        Returns:
            List[str]: List of available tool names

#### get_tool_availability

```python
def get_tool_availability(self)
```

Get availability status for all tools.

        Returns:
            Dict[str, bool]: Dictionary mapping tool names to availability status

#### get_disabled_tools_info

```python
def get_disabled_tools_info(self, all_tools)
```

Get information about disabled tools and reasons.

        Args:
            all_tools: List of all tool names

        Returns:
            List[Dict[str, str]]: List of disabled tool information

#### get_tool_details

```python
def get_tool_details(self, tool_name)
```

Get detailed information about a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Optional[Dict[str, Any]]: Tool details or None if not found

#### get_all_tool_details

```python
def get_all_tool_details(self)
```

Get details for all tools.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of all tool details

#### get_tool_summary

```python
def get_tool_summary(self)
```

Get a summary of tool availability.

        Returns:
            Dict[str, Any]: Tool availability summary

#### is_tool_available

```python
def is_tool_available(self, tool_name)
```

Check if a specific tool is available.

        Args:
            tool_name: Name of the tool to check

        Returns:
            bool: True if tool is available, False otherwise

#### refresh_tool_status

```python
def refresh_tool_status(self)
```

Refresh tool status based on current feature availability.

        This method can be called to update tool availability
        without re-registering all tools.

#### is_initialized

```python
def is_initialized(self)
```

Check if the tool registry has been initialized.

        Returns:
            bool: True if initialized, False otherwise
