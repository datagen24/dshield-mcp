"""Tool loader system for dynamic MCP tool registration.

This module provides functionality to dynamically load and register
MCP tools from individual tool files, making the system extensible
and maintainable.
"""

import importlib.util
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Type

import structlog

from .base import BaseTool, ToolCategory, ToolDefinition

logger = structlog.get_logger(__name__)


class ToolLoader:
    """Loads and manages MCP tools from individual files.

    This class provides functionality to dynamically discover,
    load, and organize MCP tools from the tools directory.
    """

    def __init__(self, tools_directory: Path):
        """Initialize the tool loader.

        Args:
            tools_directory: Path to the directory containing tool files
        """
        self.tools_directory = tools_directory
        self._tools: Dict[str, ToolDefinition] = {}
        logger.info("Initialized ToolLoader", directory=str(tools_directory))

    def load_all_tools(self) -> Dict[str, ToolDefinition]:
        """Load all tools from the tools directory.

        Returns:
            Dictionary mapping tool names to their definitions
        """
        logger.info("Loading tools from directory", directory=str(self.tools_directory))

        if not self.tools_directory.exists():
            logger.error("Tools directory does not exist", directory=str(self.tools_directory))
            return {}

        # Find all Python files in the tools directory (excluding __init__.py, base.py, dispatcher.py, loader.py)
        excluded_files = {"__init__.py", "base.py", "dispatcher.py", "loader.py"}
        tool_files = [
            f for f in self.tools_directory.glob("*.py")
            if f.name not in excluded_files and not f.name.startswith("_")
        ]

        logger.info("Found tool files", count=len(tool_files), files=[f.name for f in tool_files])

        # Load each tool file
        for tool_file in tool_files:
            try:
                tool_defs = self._load_tool_file(tool_file)
                for tool_def in tool_defs:
                    self._tools[tool_def.name] = tool_def
                    logger.debug("Loaded tool", name=tool_def.name, category=tool_def.category.value)
            except Exception as e:
                logger.error("Failed to load tool file", file=tool_file.name, error=str(e))

        logger.info("Finished loading tools", total_count=len(self._tools))
        return self._tools

    def _load_tool_file(self, tool_file: Path) -> List[ToolDefinition]:
        """Load tool definitions from a single file.

        Args:
            tool_file: Path to the tool file

        Returns:
            List of tool definitions found in the file

        Raises:
            ImportError: If the file cannot be imported
            ValueError: If the file doesn't contain valid tool definitions
        """
        logger.debug("Loading tool file", file=tool_file.name)

        # Import the module dynamically
        module_name = f"src.mcp_tools.tools.{tool_file.stem}"
        spec = importlib.util.spec_from_file_location(module_name, tool_file)

        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load spec for {tool_file}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find all classes that inherit from BaseTool
        tool_definitions = []
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Check if it's a BaseTool subclass (but not BaseTool itself)
            if issubclass(obj, BaseTool) and obj is not BaseTool:
                try:
                    # Instantiate the tool to get its definition
                    tool_instance = obj()
                    tool_def = tool_instance.definition
                    tool_definitions.append(tool_def)
                    logger.debug(
                        "Found tool class",
                        file=tool_file.name,
                        class_name=name,
                        tool_name=tool_def.name
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to instantiate tool class",
                        file=tool_file.name,
                        class_name=name,
                        error=str(e)
                    )

        if not tool_definitions:
            logger.warning("No tool definitions found in file", file=tool_file.name)

        return tool_definitions

    def get_tool_definition(self, tool_name: str) -> Optional[ToolDefinition]:
        """Get a tool definition by name.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool definition if found, None otherwise
        """
        return self._tools.get(tool_name)

    def get_tools_by_category(self, category: ToolCategory) -> List[ToolDefinition]:
        """Get all tools in a specific category.

        Args:
            category: Tool category to filter by

        Returns:
            List of tool definitions in the category
        """
        return [
            tool_def for tool_def in self._tools.values()
            if tool_def.category == category
        ]

    def get_all_tool_definitions(self) -> List[ToolDefinition]:
        """Get all loaded tool definitions.

        Returns:
            List of all tool definitions
        """
        return list(self._tools.values())

    def is_tool_available(self, tool_name: str, available_features: List[str]) -> bool:
        """Check if a tool is available based on required features.

        Args:
            tool_name: Name of the tool to check
            available_features: List of currently available features

        Returns:
            True if tool is available, False otherwise
        """
        tool_def = self.get_tool_definition(tool_name)
        if not tool_def:
            return False

        # If tool has no feature requirements, it's always available
        if not tool_def.requires_features:
            return True

        # Check if all required features are available
        return all(
            feature in available_features
            for feature in tool_def.requires_features
        )

    def get_available_tools(self, available_features: List[str]) -> List[ToolDefinition]:
        """Get all available tools based on feature availability.

        Args:
            available_features: List of currently available features

        Returns:
            List of available tool definitions
        """
        return [
            tool_def for tool_def in self._tools.values()
            if self.is_tool_available(tool_def.name, available_features)
        ]
