"""Minimal Textual app for testing TUI components.

This module provides a minimal Textual app and Pilot helper for testing
TUI components without the complexity of the full application.
"""

import asyncio
import builtins
from typing import Any
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
        self.mounted_widgets: list[Widget] = []
        # Force a headless driver class to avoid real TTY threads
        try:  # pragma: no cover - test infra
            from textual.drivers.null_driver import NullDriver  # type: ignore

            self._driver_class = NullDriver  # type: ignore[attr-defined]
        except Exception:

            class _StubDriver:
                def __init__(self, app: App) -> None:
                    self.app = app

                def start(self) -> None:
                    return None

                def stop(self) -> None:
                    return None

            self._driver_class = _StubDriver  # type: ignore[attr-defined]

    # Use a headless/null driver to avoid spawning real TTY I/O threads in tests
    # This prevents hangs and high CPU usage from background driver threads.
    def _make_driver(self, *args: Any, **kwargs: Any):  # pragma: no cover - test infra
        try:
            # Textual's null driver provides a headless environment
            from textual.drivers.null_driver import NullDriver  # type: ignore

            return NullDriver(self)
        except Exception:
            # Fallback: minimal stub driver with the interface Pilot/App expect
            class _StubDriver:  # pragma: no cover - defensive fallback
                def __init__(self, app: App) -> None:
                    self.app = app

                def start(self) -> None:
                    return None

                def stop(self) -> None:
                    return None

            return _StubDriver(self)

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

    def get_mounted_widget(self, widget_type: type[Widget]) -> Widget | None:
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

    def __init__(self, app: App | None = None) -> None:
        """Initialize the test helper.

        Args:
            app: The app to use, or None to create a MinimalTestApp
        """
        self.app = app or MinimalTestApp()
        self.pilot: Pilot | None = None

    async def __aenter__(self) -> "TextualTestHelper":
        """Async context manager entry."""
        self.pilot = await self.app.run_async()
        # Expose a convenient global for tests that reference `app`
        builtins.app = self.app  # type: ignore[attr-defined]
        # Speed up tests that spam refresh by patching to a fast no-op
        try:

            async def _fast_refresh() -> None:  # pragma: no cover - trivial
                return None

            self.app.refresh = _fast_refresh  # type: ignore[attr-defined]
        except Exception:
            pass
        # Ensure a screen exists and wait for test container before mounting widgets
        if self.pilot is not None:
            try:
                # Push a screen if none exists yet
                try:
                    _ = self.app.screen  # may raise if no screens
                except Exception:
                    from textual.screen import Screen as _Scr

                    try:
                        self.app.install_screen(_Scr(), name="__test__")
                        self.app.push_screen("__test__")
                    except Exception:
                        pass
                await self.pilot.wait_for_selector(":screen", timeout=2.0)
                await self.pilot.wait_for_selector("#test-container", timeout=2.0)
            except Exception:
                pass
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self.pilot:
            await self.pilot.exit()
        if self.app:
            await self.app.action_quit()
            # Give the app a moment to settle and stop threads
            await asyncio.sleep(0)
            # Attempt to stop the driver threads if exposed
            driver = getattr(self.app, "_driver", None)
            try:
                if driver and hasattr(driver, "stop"):
                    driver.stop()
            except Exception:
                pass
        # Clean up global reference
        if getattr(builtins, "app", None) is self.app:  # type: ignore[attr-defined]
            try:
                del builtins.app  # type: ignore[attr-defined]
            except Exception:
                pass

    async def mount_widget(self, widget: Widget, container_id: str = "test-container") -> None:
        """Mount a widget in the app.

        Args:
            widget: The widget to mount
            container_id: The ID of the container to mount in
        """
        # Ensure the container exists before mounting to avoid race conditions
        if self.pilot is not None:
            try:
                await self.pilot.wait_for_selector(f"#{container_id}", timeout=1.0)
            except Exception:
                pass

        if isinstance(self.app, MinimalTestApp):
            # Fallback: if container still isn't found, create it on the fly
            try:
                self.app.mount_widget(widget, container_id)
            except Exception:
                from textual.containers import Container as _C

                self.app.mount(_C(id=container_id))
                self.app.mount_widget(widget, container_id)
        else:
            # For other apps, try to find a container and mount
            try:
                container = self.app.query_one(f"#{container_id}", Container)
                container.mount(widget)
            except Exception:
                # Fallback: mount directly in the app
                self.app.mount(widget)

    def get_widget(self, widget_type: type[Widget]) -> Widget | None:
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

    def get_widgets(self, widget_type: type[Widget]) -> list[Widget]:
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
def create_textual_test_helper(app: App | None = None) -> TextualTestHelper:
    """Create a TextualTestHelper instance.

    Args:
        app: The app to use, or None to create a MinimalTestApp

    Returns:
        A TextualTestHelper instance
    """
    return TextualTestHelper(app)
