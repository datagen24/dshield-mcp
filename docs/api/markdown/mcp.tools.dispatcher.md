# dispatcher

Tool dispatcher for routing MCP tool calls to appropriate handlers.

This module provides a dispatcher pattern for handling tool execution,
making it easy to add new tools and maintain clean separation of concerns.

## ToolDispatcher

Dispatches MCP tool calls to appropriate handlers.
    
    This class provides a clean way to route tool calls to their
    respective handlers while maintaining error handling and logging.

#### __init__

```python
def __init__(self, tool_loader)
```

Initialize the tool dispatcher.
        
        Args:
            tool_loader: Tool loader instance for getting tool definitions

#### register_handler

```python
def register_handler(self, tool_name, handler)
```

Register a handler for a specific tool.
        
        Args:
            tool_name: Name of the tool
            handler: Async function that handles the tool call

#### register_category_handler

```python
def register_category_handler(self, category, handler)
```

Register a handler for a tool category.
        
        Args:
            category: Tool category
            handler: Async function that handles tools in this category

#### get_available_tools

```python
def get_available_tools(self, available_features)
```

Get all available tools based on feature availability.
        
        Args:
            available_features: List of currently available features
            
        Returns:
            List of available tool definitions

#### is_tool_available

```python
def is_tool_available(self, tool_name, available_features)
```

Check if a tool is available.
        
        Args:
            tool_name: Name of the tool
            available_features: List of currently available features
            
        Returns:
            True if tool is available, False otherwise

#### get_tools_by_category

```python
def get_tools_by_category(self, category)
```

Get tools in a specific category.
        
        Args:
            category: Tool category
            
        Returns:
            List of tool definitions in the category
