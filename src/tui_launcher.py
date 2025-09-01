#!/usr/bin/env python3
"""TUI launcher for DShield MCP Server.

This module provides the main entry point for the terminal user interface,
handling server process management and TUI integration.
"""

import asyncio
import os
import subprocess
import sys
from typing import Any, Dict, Optional

import structlog

from .tui.tui_app import DShieldTUIApp
from .user_config import UserConfigManager

logger = structlog.get_logger(__name__)


class TUIProcessManager:
    """Manages the MCP server process for the TUI.
    
    This class handles starting, stopping, and monitoring the MCP server
    process when running in TUI mode.
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize the TUI process manager.
        
        Args:
            config_path: Optional path to configuration file

        """
        self.config_path = config_path
        self.user_config = UserConfigManager(config_path)
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")

        # Process management
        self.server_process: Optional[subprocess.Popen] = None
        self.server_running = False
        self.server_restart_pending = False

        # Server configuration
        self.server_config = {
            "port": self.user_config.tcp_transport_settings.port,
            "bind_address": self.user_config.tcp_transport_settings.bind_address,
            "max_connections": self.user_config.tcp_transport_settings.max_connections,
            "connection_timeout_seconds": self.user_config.tcp_transport_settings.connection_timeout_seconds,
            "connection_management": {
                "api_key_management": self.user_config.tcp_transport_settings.api_key_management,
                "permissions": self.user_config.tcp_transport_settings.permissions,
            },
            "security": {
                "global_rate_limit": 1000,
                "global_burst_limit": 100,
                "client_rate_limit": self.user_config.tcp_transport_settings.api_key_management.get("rate_limit_per_key", 60),
                "client_burst_limit": 10,
                "abuse_threshold": 10,
                "block_duration_seconds": 3600,
                "max_connection_attempts": 5,
                "connection_window_seconds": 300,
                "input_validation": {
                    "max_message_size": 1048576,
                    "max_field_length": 10000,
                    "allowed_methods": [
                        "initialize", "initialized", "tools/list", "tools/call",
                        "resources/list", "resources/read", "prompts/list", "prompts/get",
                        "authenticate",
                    ],
                },
            },
            "authentication": {
                "session_timeout_seconds": 3600,
                "max_sessions_per_key": 5,
            },
        }

    async def start_server(self) -> bool:
        """Start the MCP server process.
        
        Returns:
            True if server started successfully, False otherwise

        """
        try:
            if self.server_running:
                self.logger.warning("Server is already running")
                return True

            self.logger.info("Starting MCP server process")

            # Set environment variable to indicate TUI mode
            env = os.environ.copy()
            env["DSHIELD_TUI_MODE"] = "true"
            env["DSHIELD_MCP_TCP_MODE"] = "true"

            # Build server command
            server_cmd = [
                sys.executable, "-m", "src.server_launcher",
            ]

            if self.config_path:
                server_cmd.append(self.config_path)

            # Start server process
            self.server_process = subprocess.Popen(
                server_cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Wait a moment to check if process started successfully
            await asyncio.sleep(1)

            if self.server_process.poll() is None:
                self.server_running = True
                self.logger.info("MCP server process started successfully", pid=self.server_process.pid)
                return True
            self.logger.error("MCP server process failed to start")
            return False

        except Exception as e:
            self.logger.error("Error starting MCP server process", error=str(e))
            return False

    async def stop_server(self) -> bool:
        """Stop the MCP server process.
        
        Returns:
            True if server stopped successfully, False otherwise

        """
        try:
            if not self.server_running or not self.server_process:
                self.logger.warning("Server is not running")
                return True

            self.logger.info("Stopping MCP server process", pid=self.server_process.pid)

            # Send SIGTERM to the process
            self.server_process.terminate()

            # Wait for graceful shutdown
            try:
                self.server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # Force kill if graceful shutdown fails
                self.logger.warning("Server did not shut down gracefully, forcing kill")
                self.server_process.kill()
                self.server_process.wait()

            self.server_running = False
            self.server_process = None

            self.logger.info("MCP server process stopped successfully")
            return True

        except Exception as e:
            self.logger.error("Error stopping MCP server process", error=str(e))
            return False

    async def restart_server(self) -> bool:
        """Restart the MCP server process.
        
        Returns:
            True if server restarted successfully, False otherwise

        """
        try:
            self.logger.info("Restarting MCP server process")

            # Stop existing server
            if self.server_running:
                await self.stop_server()

            # Start new server
            return await self.start_server()

        except Exception as e:
            self.logger.error("Error restarting MCP server process", error=str(e))
            return False

    def is_server_running(self) -> bool:
        """Check if the server process is running.
        
        Returns:
            True if server is running, False otherwise

        """
        if not self.server_process:
            return False

        return self.server_process.poll() is None

    def get_server_status(self) -> Dict[str, Any]:
        """Get server process status.
        
        Returns:
            Dictionary of server status information

        """
        return {
            "running": self.server_running,
            "pid": self.server_process.pid if self.server_process else None,
            "config": self.server_config,
            "restart_pending": self.server_restart_pending,
        }

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self.server_running:
                await self.stop_server()
        except Exception as e:
            self.logger.error("Error during cleanup", error=str(e))


class DShieldTUILauncher:
    """Main launcher for the DShield MCP TUI.
    
    This class coordinates the TUI application and server process management.
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize the TUI launcher.
        
        Args:
            config_path: Optional path to configuration file

        """
        self.config_path = config_path
        self.user_config = UserConfigManager(config_path)
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")

        # Components
        self.process_manager = TUIProcessManager(config_path)
        self.tui_app: Optional[DShieldTUIApp] = None

    def run(self) -> None:
        """Run the TUI application with server management.
        
        This method starts the TUI application and manages the server process.
        """
        try:
            self.logger.info("Starting DShield MCP TUI")

            # Check if TUI is enabled
            if not self.user_config.tui_settings.enabled:
                self.logger.error("TUI is disabled in configuration")
                return

            # Start server if auto-start is enabled (run in sync context)
            if self.user_config.tui_settings.server_management.get("auto_start_server", True):
                self.logger.info("Auto-starting server")
                # Start server in a separate thread to avoid blocking
                import threading
                def start_server_sync():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.process_manager.start_server())
                    loop.close()

                server_thread = threading.Thread(target=start_server_sync)
                server_thread.start()
                server_thread.join(timeout=5)  # Wait up to 5 seconds

            # Create and run TUI application
            self.tui_app = DShieldTUIApp(self.config_path)

            # Override server management methods to use process manager
            self.tui_app._start_server = self._start_server_sync
            self.tui_app._stop_server = self._stop_server_sync
            self.tui_app._restart_server = self._restart_server_sync

            # Run the TUI application
            self.tui_app.run()

        except KeyboardInterrupt:
            self.logger.info("TUI interrupted by user")
        except Exception as e:
            self.logger.error("Error running TUI", error=str(e))
            raise
        finally:
            # Cleanup in sync context
            self.cleanup_sync()

    def _start_server_sync(self) -> None:
        """Start the server (called by TUI app)."""
        import threading
        def start_server_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success = loop.run_until_complete(self.process_manager.start_server())
                if success:
                    self.tui_app.server_running = True
                    self.tui_app.notify("Server started successfully", timeout=3)
                else:
                    self.tui_app.notify("Failed to start server", timeout=5)
            finally:
                loop.close()

        thread = threading.Thread(target=start_server_async)
        thread.start()

    def _stop_server_sync(self) -> None:
        """Stop the server (called by TUI app)."""
        import threading
        def stop_server_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success = loop.run_until_complete(self.process_manager.stop_server())
                if success:
                    self.tui_app.server_running = False
                    self.tui_app.notify("Server stopped successfully", timeout=3)
                else:
                    self.tui_app.notify("Failed to stop server", timeout=5)
            finally:
                loop.close()

        thread = threading.Thread(target=stop_server_async)
        thread.start()

    def _restart_server_sync(self) -> None:
        """Restart the server (called by TUI app)."""
        import threading
        def restart_server_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success = loop.run_until_complete(self.process_manager.restart_server())
                if success:
                    self.tui_app.server_running = True
                    self.tui_app.notify("Server restarted successfully", timeout=3)
                else:
                    self.tui_app.notify("Failed to restart server", timeout=5)
            finally:
                loop.close()

        thread = threading.Thread(target=restart_server_async)
        thread.start()

    def cleanup_sync(self) -> None:
        """Clean up resources in sync context."""
        try:
            self.logger.info("Cleaning up TUI launcher")

            # Stop server if running
            if self.process_manager.server_running:
                import threading
                def stop_server_async():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(self.process_manager.stop_server())
                    finally:
                        loop.close()

                thread = threading.Thread(target=stop_server_async)
                thread.start()
                thread.join(timeout=5)

            # Clean up process manager
            import threading
            def cleanup_async():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.process_manager.cleanup())
                finally:
                    loop.close()

            thread = threading.Thread(target=cleanup_async)
            thread.start()
            thread.join(timeout=5)

            self.logger.info("TUI launcher cleanup completed")

        except Exception as e:
            self.logger.error("Error during TUI launcher cleanup", error=str(e))

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            self.logger.info("Cleaning up TUI launcher")

            # Clean up process manager
            await self.process_manager.cleanup()

            self.logger.info("TUI launcher cleanup completed")

        except Exception as e:
            self.logger.error("Error during TUI launcher cleanup", error=str(e))


def run_tui(config_path: Optional[str] = None) -> None:
    """Run the TUI application.
    
    Args:
        config_path: Optional path to configuration file

    """
    # Configure logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logger = structlog.get_logger(__name__)

    try:
        # Create and run the TUI launcher
        launcher = DShieldTUILauncher(config_path)
        launcher.run()

    except KeyboardInterrupt:
        logger.info("TUI interrupted by user")
    except Exception as e:
        logger.error("TUI failed to start", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    # Get configuration path from command line
    config_path = None
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    elif os.getenv("DSHIELD_MCP_CONFIG"):
        config_path = os.getenv("DSHIELD_MCP_CONFIG")

    run_tui(config_path)
