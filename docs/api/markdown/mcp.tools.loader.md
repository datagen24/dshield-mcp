# loader

Tool loader system for dynamic MCP tool registration.

This module provides functionality to dynamically load and register
MCP tools from individual tool files, making the system extensible
and maintainable.

## ToolLoader

Loads and manages MCP tools from individual files.
    
    This class provides functionality to dynamically discover,
    load, and organize MCP tools from the tools directory.

#### __init__

```python
def __init__(self, tools_directory)
```

Initialize the tool loader.
        
        Args:
            tools_directory: Path to the directory containing tool files

#### load_all_tools

```python
def load_all_tools(self)
```

Load all tools from the tools directory.
        
        Returns:
            Dictionary mapping tool names to their definitions

#### _load_tool_file

```python
def _load_tool_file(self, tool_file)
```

Load tool definitions from a single file.
        
        Args:
            tool_file: Path to the tool file
            
        Returns:
            List of tool definitions found in the file
            
        Raises:
            ImportError: If the file cannot be imported
            ValueError: If the file doesn't contain valid tool definitions

#### get_tool_definition

```python
def get_tool_definition(self, tool_name)
```

Get a tool definition by name.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool definition if found, None otherwise

#### get_tools_by_category

```python
def get_tools_by_category(self, category)
```

Get all tools in a specific category.
        
        Args:
            category: Tool category to filter by
            
        Returns:
            List of tool definitions in the category

#### get_all_tool_definitions

```python
def get_all_tool_definitions(self)
```

Get all loaded tool definitions.
        
        Returns:
            List of all tool definitions

#### is_tool_available

```python
def is_tool_available(self, tool_name, available_features)
```

Check if a tool is available based on required features.
        
        Args:
            tool_name: Name of the tool to check
            available_features: List of currently available features
            
        Returns:
            True if tool is available, False otherwise

#### get_available_tools

```python
def get_available_tools(self, available_features)
```

Get all tools that are currently available.
        
        Args:
            available_features: List of currently available features
            
        Returns:
            List of available tool definitions
