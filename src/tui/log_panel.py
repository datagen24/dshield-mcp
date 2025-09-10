#!/usr/bin/env python3
"""Log display panel for DShield MCP TUI.

This module provides a terminal UI panel for displaying real-time logs,
including filtering, searching, and log level management with bounded buffer.
"""

from datetime import datetime
from typing import Any

import structlog
from textual.app import ComposeResult  # type: ignore
from textual.containers import Container, Horizontal, Vertical  # type: ignore
from textual.message import Message  # type: ignore
from textual.widgets import Button, Checkbox, Input, Static, TextArea  # type: ignore

from .log_buffer import LogBuffer

logger = structlog.get_logger(__name__)


class LogFilterUpdate(Message):  # type: ignore
    """Message sent when log filter is updated."""

    def __init__(self, filter_config: dict[str, Any]) -> None:
        """Initialize log filter update message.

        Args:
            filter_config: Log filter configuration

        """
        super().__init__()
        self.filter_config = filter_config


class LogClear(Message):  # type: ignore
    """Message sent when logs should be cleared."""


class LogExport(Message):  # type: ignore
    """Message sent when logs should be exported."""

    def __init__(self, export_path: str) -> None:
        """Initialize log export message.

        Args:
            export_path: Path to export logs to

        """
        super().__init__()
        self.export_path = export_path


class LogPanel(Container):  # type: ignore
    """Panel for displaying and managing logs.

    This panel provides real-time log display with filtering, searching,
    and export capabilities using a bounded log buffer.
    """

    def __init__(self, id: str = "log-panel", max_entries: int = 1000) -> None:
        """Initialize the log panel.

        Args:
            id: Panel ID
            max_entries: Maximum number of log entries to keep

        """
        super().__init__(id=id)
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")

        # Initialize bounded log buffer
        self.log_buffer = LogBuffer(
            max_size=max_entries,
            coalesce_interval_ms=100,  # 100ms burst coalescing
            render_callback=self._render_callback,
        )

        # Display configuration
        self.filter_config: dict[str, Any] = {
            "levels": {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"},
            "search_text": "",
            "case_sensitive": False,
            "show_timestamps": True,
            "show_levels": True,
            "show_sources": True,
        }

    def compose(self) -> ComposeResult:
        """Compose the log panel layout.

        Returns:
            ComposeResult: The composed UI elements

        """
        yield Static("Log Monitor", classes="panel-title")

        with Vertical(classes="panel"):
            # Log controls
            with Horizontal(classes="log-controls"):
                yield Button("Clear Logs", id="clear-logs-btn")
                yield Button("Export Logs", id="export-logs-btn")
                yield Button("Auto-scroll", id="auto-scroll-btn", variant="primary")
                yield Button("Pause", id="pause-logs-btn")

            # Filter controls
            with Horizontal(classes="filter-controls"):
                yield Static("Levels:")
                yield Checkbox("DEBUG", id="filter-debug", value=True)
                yield Checkbox("INFO", id="filter-info", value=True)
                yield Checkbox("WARNING", id="filter-warning", value=True)
                yield Checkbox("ERROR", id="filter-error", value=True)
                yield Checkbox("CRITICAL", id="filter-critical", value=True)

            with Horizontal(classes="search-controls"):
                yield Static("Search:")
                yield Input(placeholder="Search logs...", id="search-input")
                yield Checkbox("Case Sensitive", id="case-sensitive-search", value=False)
                yield Button("Clear Search", id="clear-search-btn")

            # Display options
            with Horizontal(classes="display-controls"):
                yield Checkbox("Show Timestamps", id="show-timestamps", value=True)
                yield Checkbox("Show Levels", id="show-levels", value=True)
                yield Checkbox("Show Sources", id="show-sources", value=True)

            # Log display
            yield Static("Log Entries:", classes="section-title")
            yield TextArea(id="log-display", read_only=True)

    def on_mount(self) -> None:
        """Handle panel mount event."""
        self.logger.debug("Log panel mounted")

        # Initialize log display
        log_display = self.query_one("#log-display", TextArea)
        log_display.text = "Log monitor ready. Waiting for log entries...\n"

    def add_log_entries(self, entries: list[dict[str, Any]]) -> None:
        """Add new log entries to the display.

        Args:
            entries: List of log entries to add

        """
        self.logger.debug("add_log_entries called", entries_count=len(entries), entries=entries)

        # Add entries to the bounded buffer (handles filtering and coalescing)
        self.log_buffer.add_entries(entries)

        self.logger.debug(
            "Added log entries to buffer",
            count=len(entries),
            buffer_stats=self.log_buffer.get_statistics(),
        )

    def clear_logs(self) -> None:
        """Clear all log entries."""
        self.log_buffer.clear()

        log_display = self.query_one("#log-display", TextArea)
        log_display.text = "Logs cleared.\n"

        self.logger.info("Cleared all log entries")

    def _render_callback(self) -> None:
        """Callback function for log buffer to trigger display update."""
        self._update_display()

    def _apply_filters(self) -> None:
        """Apply current filters to log entries."""
        # Update log buffer filters
        self.log_buffer.set_level_filter(self.filter_config["levels"])
        self.log_buffer.set_search_filter(
            self.filter_config["search_text"], self.filter_config["case_sensitive"]
        )

    def _update_display(self) -> None:
        """Update the log display with filtered entries."""
        log_display = self.query_one("#log-display", TextArea)

        # Get filtered entries from buffer
        filtered_entries = self.log_buffer.get_filtered_entries()

        # Build display text
        display_lines = []
        for entry in filtered_entries[-100:]:  # Show last 100 filtered entries
            line = self._format_log_entry(entry)
            display_lines.append(line)

        # Update display
        log_display.text = "\n".join(display_lines)

        # Auto-scroll to bottom if enabled
        auto_scroll_btn = self.query_one("#auto-scroll-btn", Button)
        if auto_scroll_btn.variant == "primary":
            log_display.scroll_end()

    def _format_log_entry(self, entry: dict[str, Any]) -> str:
        """Format a log entry for display.

        Args:
            entry: Log entry dictionary

        Returns:
            Formatted log entry string

        """
        parts = []

        # Add timestamp if enabled
        if self.filter_config["show_timestamps"]:
            timestamp = entry.get("timestamp", datetime.now().isoformat())
            if isinstance(timestamp, str):
                # Format timestamp for display
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    timestamp = dt.strftime("%H:%M:%S")
                except (ValueError, TypeError):
                    pass
            parts.append(f"[{timestamp}]")

        # Add level if enabled
        if self.filter_config["show_levels"]:
            level = entry.get("level", "INFO")
            parts.append(f"[{level}]")

        # Add source if enabled
        if self.filter_config["show_sources"]:
            source = entry.get("source", "")
            if source:
                parts.append(f"[{source}]")

        # Add message
        message = entry.get("message", str(entry))
        parts.append(message)

        return " ".join(parts)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: Button press event

        """
        button_id = event.button.id

        if button_id == "clear-logs-btn":
            self._clear_logs()
        elif button_id == "export-logs-btn":
            self._export_logs()
        elif button_id == "auto-scroll-btn":
            self._toggle_auto_scroll()
        elif button_id == "pause-logs-btn":
            self._toggle_pause()
        elif button_id == "clear-search-btn":
            self._clear_search()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox change events.

        Args:
            event: Checkbox change event

        """
        checkbox_id = event.checkbox.id

        if checkbox_id.startswith("filter-"):
            level = checkbox_id.replace("filter-", "").upper()
            filter_levels = self.filter_config["levels"]
            if isinstance(filter_levels, set):
                if event.checkbox.value:
                    filter_levels.add(level)
                else:
                    filter_levels.discard(level)

            self._apply_filters()
            self._update_display()

        elif checkbox_id == "show-timestamps":
            self.filter_config["show_timestamps"] = event.checkbox.value
            self._update_display()
        elif checkbox_id == "show-levels":
            self.filter_config["show_levels"] = event.checkbox.value
            self._update_display()
        elif checkbox_id == "show-sources":
            self.filter_config["show_sources"] = event.checkbox.value
            self._update_display()
        elif checkbox_id == "case-sensitive-search":
            self.filter_config["case_sensitive"] = event.checkbox.value
            self._apply_filters()
            self._update_display()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input field changes.

        Args:
            event: Input change event

        """
        if event.input.id == "search-input":
            self.filter_config["search_text"] = event.input.value
            self._apply_filters()
            self._update_display()

    def _clear_logs(self) -> None:
        """Clear all logs."""
        self.logger.info("Clearing logs")
        self.post_message(LogClear())
        self.clear_logs()

    def _export_logs(self) -> None:
        """Export logs to file."""
        # This would typically open a file dialog
        # For now, we'll use a default path
        export_path = f"dshield_mcp_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.logger.info("Exporting logs", path=export_path)
        self.post_message(LogExport(export_path))

    def _toggle_auto_scroll(self) -> None:
        """Toggle auto-scroll mode."""
        auto_scroll_btn = self.query_one("#auto-scroll-btn", Button)
        if auto_scroll_btn.variant == "primary":
            auto_scroll_btn.variant = "default"
            auto_scroll_btn.label = "Auto-scroll"
        else:
            auto_scroll_btn.variant = "primary"
            auto_scroll_btn.label = "Auto-scroll ✓"

        self.logger.debug("Toggled auto-scroll")

    def _toggle_pause(self) -> None:
        """Toggle log pause mode."""
        pause_btn = self.query_one("#pause-logs-btn", Button)
        if pause_btn.variant == "primary":
            pause_btn.variant = "default"
            pause_btn.label = "Pause"
        else:
            pause_btn.variant = "primary"
            pause_btn.label = "Paused"

        self.logger.debug("Toggled log pause")

    def _clear_search(self) -> None:
        """Clear search input."""
        search_input = self.query_one("#search-input", Input)
        search_input.value = ""
        self.filter_config["search_text"] = ""
        self._apply_filters()
        self._update_display()

    def get_log_statistics(self) -> dict[str, Any]:
        """Get log statistics.

        Returns:
            Dictionary of log statistics

        """
        buffer_stats = self.log_buffer.get_statistics()
        filtered_entries = self.log_buffer.get_filtered_entries()

        # Count by level
        level_counts: dict[str, int] = {}
        for entry in self.log_buffer.get_all_entries():
            level = entry.get("level", "INFO")
            level_counts[level] = level_counts.get(level, 0) + 1

        return {
            "total_entries": buffer_stats["buffer_size"],
            "filtered_entries": len(filtered_entries),
            "level_counts": level_counts,
            "filter_config": self.filter_config,
            "max_entries": buffer_stats["max_size"],
            "buffer_statistics": buffer_stats,
        }

    def set_max_entries(self, max_entries: int) -> None:
        """Set maximum number of log entries to keep.

        Args:
            max_entries: Maximum number of entries

        """
        # Create new buffer with new max size
        old_buffer = self.log_buffer
        self.log_buffer = LogBuffer(
            max_size=max_entries,
            coalesce_interval_ms=old_buffer.coalesce_interval_ms,
            render_callback=self._render_callback,
        )

        # Copy existing entries
        self.log_buffer.add_entries(old_buffer.get_all_entries())

        # Clean up old buffer
        old_buffer.cleanup()

        self.logger.debug("Set max log entries", max_entries=max_entries)

    def on_unmount(self) -> None:
        """Handle panel unmount event."""
        self.log_buffer.cleanup()
        self.logger.debug("Log panel unmounted and cleaned up")
