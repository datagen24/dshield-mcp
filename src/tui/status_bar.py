#!/usr/bin/env python3
"""Status bar for DShield MCP TUI.

This module provides a status bar widget for displaying real-time status
information including server status, connection counts, and system metrics.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional
from textual.widgets import Static  # type: ignore
from textual.reactive import reactive  # type: ignore
import structlog

logger = structlog.get_logger(__name__)


class StatusBar(Static):  # type: ignore
    """Status bar widget for displaying real-time status information.
    
    This widget shows server status, connection counts, system metrics,
    and other relevant information in a compact format.
    """
    
    def __init__(self, id: str = "status-bar") -> None:
        """Initialize the status bar.
        
        Args:
            id: Widget ID
        """
        super().__init__(id=id)
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")
        
        # Status information
        self.server_status: Dict[str, Any] = {}
        self.connection_count = reactive(0)
        self.authenticated_count = reactive(0)
        self.api_key_count = reactive(0)
        self.error_count = reactive(0)
        self.last_update = reactive(datetime.now())
    
    def on_mount(self) -> None:
        """Handle widget mount event."""
        self.logger.debug("Status bar mounted")
        self.update_display()
    
    def update_server_status(self, status: Dict[str, Any]) -> None:
        """Update server status information.
        
        Args:
            status: Server status dictionary
        """
        self.server_status = status
        self.last_update = datetime.now()
        
        # Extract connection information
        connections = status.get("connections", {})
        self.connection_count = connections.get("active", 0)
        
        # Extract API key information
        connection_manager = status.get("connection_manager", {})
        api_keys = connection_manager.get("api_keys", {})
        self.api_key_count = api_keys.get("total", 0)
        
        # Extract error information
        security = status.get("security", {})
        abuse_detection = security.get("abuse_detection", {})
        self.error_count = abuse_detection.get("total_violations", 0)
        
        self.update_display()
        self.logger.debug("Updated server status", status=status)
    
    def update_connection_count(self, total: int, authenticated: int) -> None:
        """Update connection count information.
        
        Args:
            total: Total number of connections
            authenticated: Number of authenticated connections
        """
        self.connection_count = total
        self.authenticated_count = authenticated
        self.update_display()
        self.logger.debug("Updated connection count", total=total, authenticated=authenticated)
    
    def update_api_key_count(self, count: int) -> None:
        """Update API key count information.
        
        Args:
            count: Number of API keys
        """
        self.api_key_count = count
        self.update_display()
        self.logger.debug("Updated API key count", count=count)
    
    def update_error_count(self, count: int) -> None:
        """Update error count information.
        
        Args:
            count: Number of errors
        """
        self.error_count = count
        self.update_display()
        self.logger.debug("Updated error count", count=count)
    
    def update_display(self) -> None:
        """Update the status bar display."""
        try:
            # Build status information
            status_parts = []
            
            # Server status
            server_info = self.server_status.get("server", {})
            if server_info.get("is_running", False):
                status_parts.append("🟢 Server: Running")
                port = server_info.get("port", "N/A")
                address = server_info.get("bind_address", "N/A")
                status_parts.append(f"Port: {port}")
                status_parts.append(f"Address: {address}")
            else:
                status_parts.append("🔴 Server: Stopped")
            
            # Connection information
            status_parts.append(f"Connections: {self.connection_count}")
            if self.authenticated_count > 0:
                status_parts.append(f"Auth: {self.authenticated_count}")
            
            # API key information
            if self.api_key_count > 0:
                status_parts.append(f"API Keys: {self.api_key_count}")
            
            # Error information
            if self.error_count > 0:
                status_parts.append(f"Errors: {self.error_count}")
            
            # Last update time
            update_time = self.last_update.strftime("%H:%M:%S")
            status_parts.append(f"Updated: {update_time}")
            
            # Join all parts
            status_text = " | ".join(status_parts)
            
            # Update the display
            self.update(status_text)
            
        except Exception as e:
            self.logger.error("Error updating status bar display", error=str(e))
            self.update("Status: Error")
    
    def watch_connection_count(self, count: int) -> None:
        """Watch for connection count changes.
        
        Args:
            count: New connection count
        """
        self.update_display()
    
    def watch_authenticated_count(self, count: int) -> None:
        """Watch for authenticated count changes.
        
        Args:
            count: New authenticated count
        """
        self.update_display()
    
    def watch_api_key_count(self, count: int) -> None:
        """Watch for API key count changes.
        
        Args:
            count: New API key count
        """
        self.update_display()
    
    def watch_error_count(self, count: int) -> None:
        """Watch for error count changes.
        
        Args:
            count: New error count
        """
        self.update_display()
    
    def watch_last_update(self, update_time: datetime) -> None:
        """Watch for last update time changes.
        
        Args:
            update_time: New update time
        """
        self.update_display()
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get a summary of current status information.
        
        Returns:
            Dictionary of status summary
        """
        return {
            "server_running": self.server_status.get("server", {}).get("is_running", False),
            "connection_count": self.connection_count,
            "authenticated_count": self.authenticated_count,
            "api_key_count": self.api_key_count,
            "error_count": self.error_count,
            "last_update": self.last_update.isoformat(),
            "server_status": self.server_status
        }
    
    def set_status_message(self, message: str, timeout: Optional[float] = None) -> None:
        """Set a temporary status message.
        
        Args:
            message: Status message to display
            timeout: Optional timeout in seconds to revert to normal status
        """
        self.update(message)
        
        if timeout:
            # Schedule revert to normal status
            import asyncio
            asyncio.create_task(self._revert_status_after_timeout(timeout))
        
        self.logger.debug("Set status message", message=message, timeout=timeout)
    
    async def _revert_status_after_timeout(self, timeout: float) -> None:
        """Revert status message after timeout.
        
        Args:
            timeout: Timeout in seconds
        """
        await asyncio.sleep(timeout)
        self.update_display()
    
    def add_status_indicator(self, indicator: str, value: Any) -> None:
        """Add a status indicator to the display.
        
        Args:
            indicator: Indicator name
            value: Indicator value
        """
        # This would be used to add custom status indicators
        # For now, we'll just log it
        self.logger.debug("Added status indicator", indicator=indicator, value=value)
    
    def remove_status_indicator(self, indicator: str) -> None:
        """Remove a status indicator from the display.
        
        Args:
            indicator: Indicator name to remove
        """
        # This would be used to remove custom status indicators
        # For now, we'll just log it
        self.logger.debug("Removed status indicator", indicator=indicator)
