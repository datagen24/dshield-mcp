"""Tool dispatcher for routing MCP tool calls to appropriate handlers.

This module provides a dispatcher pattern for handling tool execution,
making it easy to add new tools and maintain clean separation of concerns.
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable, Awaitable
import structlog

from .base import ToolCategory
from .loader import ToolLoader, ToolDefinition

logger = structlog.get_logger(__name__)


class ToolDispatcher:
    """Dispatches MCP tool calls to appropriate handlers.
    
    This class provides a clean way to route tool calls to their
    respective handlers while maintaining error handling and logging.
    """
    
    def __init__(self, tool_loader: ToolLoader):
        """Initialize the tool dispatcher.
        
        Args:
            tool_loader: Tool loader instance for getting tool definitions
        """
        self.tool_loader = tool_loader
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[List[Dict[str, Any]]]]] = {}
        self._category_handlers: Dict[ToolCategory, Callable[[str, Dict[str, Any]], Awaitable[List[Dict[str, Any]]]]] = {}
    
    def register_handler(self, tool_name: str, handler: Callable[[Dict[str, Any]], Awaitable[List[Dict[str, Any]]]]) -> None:
        """Register a handler for a specific tool.
        
        Args:
            tool_name: Name of the tool
            handler: Async function that handles the tool call
        """
        self._handlers[tool_name] = handler
        logger.debug("Registered tool handler", tool=tool_name)
    
    def register_category_handler(self, category: ToolCategory, handler: Callable[[str, Dict[str, Any]], Awaitable[List[Dict[str, Any]]]]) -> None:
        """Register a handler for a tool category.
        
        Args:
            category: Tool category
            handler: Async function that handles tools in this category
        """
        self._category_handlers[category] = handler
        logger.debug("Registered category handler", category=category.value)
    
    async def dispatch_tool_call(self, tool_name: str, arguments: Dict[str, Any], 
                                timeout: Optional[float] = None) -> List[Dict[str, Any]]:
        """Dispatch a tool call to the appropriate handler.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            timeout: Optional timeout in seconds
            
        Returns:
            List of result dictionaries
            
        Raises:
            ValueError: If tool is not found or arguments are invalid
            TimeoutError: If execution times out
            Exception: For other execution errors
        """
        logger.info("Dispatching tool call", tool=tool_name)
        
        # Get tool definition
        tool_def = self.tool_loader.get_tool_definition(tool_name)
        if not tool_def:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        # Determine timeout
        execution_timeout = timeout or tool_def.timeout or 120.0
        
        try:
            # Try specific handler first
            if tool_name in self._handlers:
                handler = self._handlers[tool_name]
                result = await asyncio.wait_for(
                    handler(arguments),
                    timeout=execution_timeout
                )
                logger.debug("Tool call completed", tool=tool_name, result_count=len(result))
                return result
            
            # Try category handler
            elif tool_def.category in self._category_handlers:
                handler = self._category_handlers[tool_def.category]
                result = await asyncio.wait_for(
                    handler(tool_name, arguments),
                    timeout=execution_timeout
                )
                logger.debug("Tool call completed via category handler", 
                           tool=tool_name, category=tool_def.category.value, result_count=len(result))
                return result
            
            else:
                raise ValueError(f"No handler registered for tool: {tool_name}")
                
        except asyncio.TimeoutError:
            logger.error("Tool call timed out", tool=tool_name, timeout=execution_timeout)
            raise TimeoutError(f"Tool '{tool_name}' timed out after {execution_timeout} seconds")
        except Exception as e:
            logger.error("Tool call failed", tool=tool_name, error=str(e))
            raise
    
    def get_available_tools(self, available_features: List[str]) -> List[ToolDefinition]:
        """Get all available tools based on feature availability.
        
        Args:
            available_features: List of currently available features
            
        Returns:
            List of available tool definitions
        """
        return self.tool_loader.get_available_tools(available_features)
    
    def is_tool_available(self, tool_name: str, available_features: List[str]) -> bool:
        """Check if a tool is available.
        
        Args:
            tool_name: Name of the tool
            available_features: List of currently available features
            
        Returns:
            True if tool is available, False otherwise
        """
        return self.tool_loader.is_tool_available(tool_name, available_features)
    
    def get_tools_by_category(self, category: ToolCategory) -> List[ToolDefinition]:
        """Get tools in a specific category.
        
        Args:
            category: Tool category
            
        Returns:
            List of tool definitions in the category
        """
        return self.tool_loader.get_tools_by_category(category)

