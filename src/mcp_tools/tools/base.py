"""Base tool class and interfaces for MCP tools.

This module provides the foundation for all MCP tools, including
base classes, interfaces, and common functionality.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum


class ToolCategory(Enum):
    """Categories for organizing MCP tools."""
    
    CAMPAIGN = "campaign"
    QUERY = "query"
    REPORT = "report"
    UTILITY = "utility"
    MONITORING = "monitoring"


@dataclass
class ToolDefinition:
    """Definition of an MCP tool.
    
    Attributes:
        name: The tool name
        description: Human-readable description
        category: Tool category for organization
        schema: JSON schema for tool parameters
        handler: Async function that handles tool execution
        timeout: Optional timeout in seconds
        requires_features: List of required features for tool availability
    """
    
    name: str
    description: str
    category: ToolCategory
    schema: Dict[str, Any]
    handler: str  # Method name in the MCP server
    timeout: Optional[float] = None
    requires_features: Optional[List[str]] = None


class BaseTool(ABC):
    """Abstract base class for MCP tools.
    
    All MCP tools should inherit from this class to ensure
    consistent interface and behavior.
    """
    
    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Return the tool definition.
        
        Returns:
            ToolDefinition: The complete tool definition
        """
        pass
    
    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute the tool with given arguments.
        
        Args:
            arguments: Tool arguments from MCP client
            
        Returns:
            List of result dictionaries
            
        Raises:
            ValueError: If arguments are invalid
            TimeoutError: If execution times out
            Exception: For other execution errors
        """
        pass
    
    def validate_arguments(self, arguments: Dict[str, Any]) -> None:
        """Validate tool arguments.
        
        Args:
            arguments: Arguments to validate
            
        Raises:
            ValueError: If arguments are invalid
        """
        # Basic validation can be implemented here
        # More complex validation should be done in subclasses
        pass

