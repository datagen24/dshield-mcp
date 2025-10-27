#!/usr/bin/env python3
"""Live metrics panel for DShield MCP TUI.

This module provides a live metrics panel that displays real-time metrics
with stable formatting and threshold cues.
"""

from datetime import datetime
from typing import Any

import structlog
from textual.containers import Container, Horizontal, Vertical  # type: ignore
from textual.reactive import reactive  # type: ignore
from textual.widgets import Static  # type: ignore

from .metrics_formatter import ServerMetrics
from .metrics_subscriber import MetricsSubscriber, MetricsUpdate

logger = structlog.get_logger(__name__)


class LiveMetricsPanel(Container):
    """Live metrics panel for displaying real-time server metrics.

    This panel subscribes to metrics updates and displays them with
    stable formatting and threshold cues.
    """

    def __init__(
        self, metrics_subscriber: MetricsSubscriber | None = None, id: str = "live-metrics-panel"
    ) -> None:
        """Initialize the live metrics panel.

        Args:
            metrics_subscriber: Metrics subscriber instance
            id: Widget ID
        """
        super().__init__(id=id)
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")

        # Metrics management
        self.metrics_subscriber = metrics_subscriber
        self.current_metrics: ServerMetrics | None = None
        self.last_update_time = reactive(datetime.now())

        # Display components
        self.header_widget: Static | None = None
        self.connections_widget: Static | None = None
        self.rps_widget: Static | None = None
        self.violations_widget: Static | None = None
        self.server_state_widget: Static | None = None

        # Performance tracking
        self.update_count = 0
        self.display_updates = 0

    def on_mount(self) -> None:
        """Handle widget mount event."""
        self.logger.debug("Live metrics panel mounted")

        # Subscribe to metrics updates if subscriber is available
        if self.metrics_subscriber:
            self.metrics_subscriber.subscribe(self._on_metrics_update)
            self.logger.debug("Subscribed to metrics updates")

        # Initialize display
        self._initialize_display()
        self._update_display()

    def on_unmount(self) -> None:
        """Handle widget unmount event."""
        self.logger.debug("Live metrics panel unmounted")

        # Unsubscribe from metrics updates
        if self.metrics_subscriber:
            self.metrics_subscriber.unsubscribe(self._on_metrics_update)
            self.logger.debug("Unsubscribed from metrics updates")

    def _initialize_display(self) -> None:
        """Initialize the display components."""
        # Create header
        self.header_widget = Static("Live Metrics", id="metrics-header")

        # Create metric sections
        self.connections_widget = Static("Connections: Loading...", id="connections-metrics")
        self.rps_widget = Static("RPS: Loading...", id="rps-metrics")
        self.violations_widget = Static("Violations: Loading...", id="violations-metrics")
        self.server_state_widget = Static("Server State: Loading...", id="server-state-metrics")

        # Build layout
        self.mount(
            Vertical(
                self.header_widget,
                Horizontal(
                    Vertical(
                        self.connections_widget,
                        self.rps_widget,
                    ),
                    Vertical(
                        self.violations_widget,
                        self.server_state_widget,
                    ),
                ),
                id="metrics-content",
            )
        )

    def _on_metrics_update(self, update: MetricsUpdate) -> None:
        """Handle metrics update from subscriber.

        Args:
            update: Metrics update message
        """
        try:
            self.current_metrics = update.metrics
            self.last_update_time = update.timestamp
            self.update_count += 1

            # Update display
            self._update_display()

            self.logger.debug(
                "Received metrics update",
                timestamp=update.timestamp.isoformat(),
                update_count=self.update_count,
            )

        except Exception as e:
            self.logger.error("Error handling metrics update", error=str(e))

    def _update_display(self) -> None:
        """Update the display with current metrics."""
        try:
            if not self.current_metrics:
                self._display_loading_state()
                return

            # Update header with timestamp
            if self.header_widget:
                timestamp_str = self.current_metrics.timestamp.strftime("%H:%M:%S")
                self.header_widget.update(f"Live Metrics [{timestamp_str}]")

            # Update connections section
            self._update_connections_display()

            # Update RPS section
            self._update_rps_display()

            # Update violations section
            self._update_violations_display()

            # Update server state section
            self._update_server_state_display()

            self.display_updates += 1

        except Exception as e:
            self.logger.error("Error updating display", error=str(e))
            self._display_error_state(str(e))

    def _display_loading_state(self) -> None:
        """Display loading state when no metrics are available."""
        if self.connections_widget:
            self.connections_widget.update("Connections: Loading...")
        if self.rps_widget:
            self.rps_widget.update("RPS: Loading...")
        if self.violations_widget:
            self.violations_widget.update("Violations: Loading...")
        if self.server_state_widget:
            self.server_state_widget.update("Server State: Loading...")

    def _display_error_state(self, error_message: str) -> None:
        """Display error state when metrics update fails.

        Args:
            error_message: Error message to display
        """
        error_text = f"Error: {error_message[:50]}..."
        try:
            if self.connections_widget:
                self.connections_widget.update(f"Connections: {error_text}")
        except Exception:
            pass  # Ignore errors when displaying error state
        try:
            if self.rps_widget:
                self.rps_widget.update(f"RPS: {error_text}")
        except Exception:
            pass  # Ignore errors when displaying error state
        try:
            if self.violations_widget:
                self.violations_widget.update(f"Violations: {error_text}")
        except Exception:
            pass  # Ignore errors when displaying error state
        try:
            if self.server_state_widget:
                self.server_state_widget.update(f"Server State: {error_text}")
        except Exception:
            pass  # Ignore errors when displaying error state

    def _update_connections_display(self) -> None:
        """Update the connections metrics display."""
        if not self.connections_widget or not self.current_metrics:
            return

        lines = ["Connections:"]
        for _key, metric in self.current_metrics.connections.items():
            lines.append(f"  {metric.threshold_cue} {metric.label}: {metric.formatted_value}")

        self.connections_widget.update("\n".join(lines))

    def _update_rps_display(self) -> None:
        """Update the RPS metrics display."""
        if not self.rps_widget or not self.current_metrics:
            return

        lines = ["RPS:"]
        for _key, metric in self.current_metrics.rps.items():
            lines.append(f"  {metric.threshold_cue} {metric.label}: {metric.formatted_value}")

        self.rps_widget.update("\n".join(lines))

    def _update_violations_display(self) -> None:
        """Update the violations metrics display."""
        if not self.violations_widget or not self.current_metrics:
            return

        lines = ["Violations:"]
        for _key, metric in self.current_metrics.violations.items():
            lines.append(f"  {metric.threshold_cue} {metric.label}: {metric.formatted_value}")

        self.violations_widget.update("\n".join(lines))

    def _update_server_state_display(self) -> None:
        """Update the server state metrics display."""
        if not self.server_state_widget or not self.current_metrics:
            return

        lines = ["Server State:"]
        for _key, metric in self.current_metrics.server_state.items():
            lines.append(f"  {metric.threshold_cue} {metric.label}: {metric.formatted_value}")

        self.server_state_widget.update("\n".join(lines))

    def get_display_statistics(self) -> dict[str, Any]:
        """Get display statistics for monitoring.

        Returns:
            Dictionary of display statistics
        """
        return {
            "update_count": self.update_count,
            "display_updates": self.display_updates,
            "last_update_time": self.last_update_time.isoformat(),
            "has_metrics": self.current_metrics is not None,
            "subscriber_connected": self.metrics_subscriber is not None,
        }

    def force_refresh(self) -> None:
        """Force a refresh of the metrics display."""
        if self.metrics_subscriber:
            self.metrics_subscriber.force_update()
            self.logger.debug("Forced metrics refresh")

    def set_metrics_subscriber(self, subscriber: MetricsSubscriber) -> None:
        """Set the metrics subscriber for this panel.

        Args:
            subscriber: Metrics subscriber instance
        """
        # Unsubscribe from old subscriber if exists
        if self.metrics_subscriber:
            self.metrics_subscriber.unsubscribe(self._on_metrics_update)

        # Set new subscriber
        self.metrics_subscriber = subscriber
        subscriber.subscribe(self._on_metrics_update)

        self.logger.debug("Metrics subscriber updated")

    def cleanup(self) -> None:
        """Cleanup resources when panel is destroyed."""
        if self.metrics_subscriber:
            self.metrics_subscriber.unsubscribe(self._on_metrics_update)

        self.logger.debug("Live metrics panel cleaned up")
