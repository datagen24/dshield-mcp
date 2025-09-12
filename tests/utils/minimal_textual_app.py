"""Minimal Textual app for testing TUI components.

This module provides a minimal Textual app and Pilot helper for testing
TUI components without the complexity of the full application.
"""

from typing import Any, Dict, List, Optional, Type, Union
from unittest.mock import MagicMock

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.pilot import Pilot
from textual.widget import Widget


class MinimalTestApp(App):
    """Minimal Textual app for testing TUI components.
    
    This app provides a simple container that can mount any widget
    for testing purposes.
    """
    
    def __init__(self, **kwargs: Any) -> None:
        """Initialize the minimal test app."""
        super().__init__(**kwargs)
        self.mounted_widgets: List[Widget] = []
    
    def compose(self) -> ComposeResult:
        """Compose the minimal app layout."""
        yield Container(id="test-container")
    
    def mount_widget(self, widget: Widget, container_id: str = "test-container") -> None:
        """Mount a widget in the specified container.
        
        Args:
            widget: The widget to mount
            container_id: The ID of the container to mount in
        """
        container = self.query_one(f"#{container_id}", Container)
        container.mount(widget)
        self.mounted_widgets.append(widget)
    
    def get_mounted_widget(self, widget_type: Type[Widget]) -> Optional[Widget]:
        """Get the first mounted widget of the specified type.
        
        Args:
            widget_type: The type of widget to find
            
        Returns:
            The first widget of the specified type, or None if not found
        """
        for widget in self.mounted_widgets:
            if isinstance(widget, widget_type):
                return widget
        return None


class TextualTestHelper:
    """Helper class for testing Textual components with Pilot."""
    
    def __init__(self, app: Optional[App] = None) -> None:
        """Initialize the test helper.
        
        Args:
            app: The app to use, or None to create a MinimalTestApp
        """
        self.app = app or MinimalTestApp()
        self.pilot: Optional[Pilot] = None
    
    async def __aenter__(self) -> "TextualTestHelper":
        """Async context manager entry."""
        self.pilot = await self.app.run_async()
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self.pilot:
            await self.pilot.exit()
        if self.app:
            await self.app.action_quit()
    
    async def mount_widget(self, widget: Widget, container_id: str = "test-container") -> None:
        """Mount a widget in the app.
        
        Args:
            widget: The widget to mount
            container_id: The ID of the container to mount in
        """
        if isinstance(self.app, MinimalTestApp):
            self.app.mount_widget(widget, container_id)
        else:
            # For other apps, try to find a container and mount
            try:
                container = self.app.query_one(f"#{container_id}", Container)
                container.mount(widget)
            except Exception:
                # Fallback: mount directly in the app
                self.app.mount(widget)
    
    def get_widget(self, widget_type: Type[Widget]) -> Optional[Widget]:
        """Get a widget of the specified type.
        
        Args:
            widget_type: The type of widget to find
            
        Returns:
            The first widget of the specified type, or None if not found
        """
        if isinstance(self.app, MinimalTestApp):
            return self.app.get_mounted_widget(widget_type)
        else:
            try:
                return self.app.query_one(widget_type)
            except Exception:
                return None
    
    def get_widgets(self, widget_type: Type[Widget]) -> List[Widget]:
        """Get all widgets of the specified type.
        
        Args:
            widget_type: The type of widget to find
            
        Returns:
            List of widgets of the specified type
        """
        if isinstance(self.app, MinimalTestApp):
            return [w for w in self.app.mounted_widgets if isinstance(w, widget_type)]
        else:
            try:
                return list(self.app.query(widget_type))
            except Exception:
                return []
    
    async def press(self, *keys: str) -> None:
        """Press keys in the app.
        
        Args:
            *keys: The keys to press
        """
        if self.pilot:
            await self.pilot.press(*keys)
    
    async def click(self, selector: str) -> None:
        """Click on an element.
        
        Args:
            selector: CSS selector for the element to click
        """
        if self.pilot:
            await self.pilot.click(selector)
    
    async def wait_for_selector(self, selector: str, timeout: float = 1.0) -> bool:
        """Wait for a selector to appear.
        
        Args:
            selector: CSS selector to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if the selector was found, False if timeout
        """
        if self.pilot:
            try:
                await self.pilot.wait_for_selector(selector, timeout=timeout)
                return True
            except Exception:
                return False
        return False
    
    def create_mock_connection_manager(self) -> MagicMock:
        """Create a mock connection manager for testing.
        
        Returns:
            A mock connection manager
        """
        mock_manager = MagicMock()
        mock_manager.api_keys = {"test_key": "test_value"}
        mock_manager.connections = []
        mock_manager.get_connection_count.return_value = 0
        mock_manager.get_connections_info.return_value = []
        return mock_manager
    
    def create_mock_tcp_server(self) -> MagicMock:
        """Create a mock TCP server for testing.
        
        Returns:
            A mock TCP server
        """
        mock_server = MagicMock()
        mock_server.is_running = False
        mock_server.connection_manager = self.create_mock_connection_manager()
        return mock_server


# Convenience function for creating a test helper
def create_textual_test_helper(app: Optional[App] = None) -> TextualTestHelper:
    """Create a TextualTestHelper instance.
    
    Args:
        app: The app to use, or None to create a MinimalTestApp
        
    Returns:
        A TextualTestHelper instance
    """
    return TextualTestHelper(app)
