#!/usr/bin/env python3
"""Bounded log buffer with filtering and burst coalescing for DShield MCP TUI.

This module provides a ring buffer implementation for log entries with level filtering,
substring search, and burst coalescing to optimize rendering performance.
"""

import asyncio
import threading
import time
from collections import deque
from collections.abc import Callable
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class LogBuffer:
    """Bounded log buffer with filtering and burst coalescing.

    This class implements a ring buffer for log entries with the following features:
    - Ring buffer capped at log_history_size
    - Level filtering (DEBUG/INFO/WARN/ERROR)
    - Substring search (case-insensitive)
    - Burst coalescing (≤1 render per N ms)
    - Thread-safe operations
    """

    def __init__(
        self,
        max_size: int = 1000,
        coalesce_interval_ms: int = 100,
        render_callback: Callable[[], None] | None = None,
    ) -> None:
        """Initialize the log buffer.

        Args:
            max_size: Maximum number of log entries to keep
            coalesce_interval_ms: Minimum interval between renders in milliseconds
            render_callback: Callback function to call when rendering is needed
        """
        self.max_size = max_size
        self.coalesce_interval_ms = coalesce_interval_ms
        self.render_callback = render_callback

        # Ring buffer using deque for efficient operations
        self._buffer: deque[dict[str, Any]] = deque(maxlen=max_size)

        # Filtering state
        self._enabled_levels: set[str] = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        self._search_text: str = ""
        self._case_sensitive: bool = False

        # Burst coalescing state
        self._last_render_time: float = 0.0
        self._pending_render: bool = False
        self._render_lock = threading.Lock()
        self._render_timer: asyncio.Task[None] | None = None

        # Statistics
        self._total_added: int = 0
        self._total_filtered: int = 0
        self._total_rendered: int = 0

        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")

    def add_entry(self, entry: dict[str, Any]) -> None:
        """Add a log entry to the buffer.

        Args:
            entry: Log entry dictionary with at least 'level' and 'message' keys
        """
        # Normalize entry
        normalized_entry = self._normalize_entry(entry)

        # Add to buffer (deque automatically handles maxlen)
        self._buffer.append(normalized_entry)
        self._total_added += 1

        # Check if entry passes current filters
        if self._passes_filters(normalized_entry):
            self._total_filtered += 1
            self._schedule_render()

        self.logger.debug(
            "Added log entry",
            level=normalized_entry.get("level"),
            message=normalized_entry.get("message", "")[:50],
            total_added=self._total_added,
            buffer_size=len(self._buffer),
        )

    def add_entries(self, entries: list[dict[str, Any]]) -> None:
        """Add multiple log entries to the buffer.

        Args:
            entries: List of log entry dictionaries
        """
        for entry in entries:
            self.add_entry(entry)

    def get_filtered_entries(self) -> list[dict[str, Any]]:
        """Get all entries that pass current filters.

        Returns:
            List of filtered log entries
        """
        return [entry for entry in self._buffer if self._passes_filters(entry)]

    def get_all_entries(self) -> list[dict[str, Any]]:
        """Get all entries in the buffer.

        Returns:
            List of all log entries
        """
        return list(self._buffer)

    def clear(self) -> None:
        """Clear all entries from the buffer."""
        self._buffer.clear()
        self._total_added = 0
        self._total_filtered = 0
        self._total_rendered = 0
        self.logger.info("Cleared log buffer")

    def set_level_filter(self, levels: set[str]) -> None:
        """Set the level filter.

        Args:
            levels: Set of log levels to include (e.g., {"DEBUG", "INFO", "ERROR"})
        """
        self._enabled_levels = levels.copy()
        self.logger.debug("Updated level filter", levels=levels)
        self._schedule_render()

    def set_search_filter(self, search_text: str, case_sensitive: bool = False) -> None:
        """Set the search filter.

        Args:
            search_text: Text to search for in log entries
            case_sensitive: Whether search should be case-sensitive
        """
        self._search_text = search_text
        self._case_sensitive = case_sensitive
        self.logger.debug(
            "Updated search filter", search_text=search_text, case_sensitive=case_sensitive
        )
        self._schedule_render()

    def get_statistics(self) -> dict[str, Any]:
        """Get buffer statistics.

        Returns:
            Dictionary containing buffer statistics
        """
        return {
            "buffer_size": len(self._buffer),
            "max_size": self.max_size,
            "total_added": self._total_added,
            "total_filtered": self._total_filtered,
            "total_rendered": self._total_rendered,
            "enabled_levels": self._enabled_levels,
            "search_text": self._search_text,
            "case_sensitive": self._case_sensitive,
            "coalesce_interval_ms": self.coalesce_interval_ms,
        }

    def _normalize_entry(self, entry: dict[str, Any]) -> dict[str, Any]:
        """Normalize a log entry for consistent processing.

        Args:
            entry: Raw log entry

        Returns:
            Normalized log entry
        """
        normalized = entry.copy()

        # Ensure level is uppercase string
        level = normalized.get("level", "INFO")
        if not isinstance(level, str):
            level = str(level)
        normalized["level"] = level.upper()

        # Ensure message is string
        message = normalized.get("message", "")
        if not isinstance(message, str):
            message = str(message)
        normalized["message"] = message

        # Add timestamp if missing
        if "timestamp" not in normalized:
            normalized["timestamp"] = time.time()

        return normalized

    def _passes_filters(self, entry: dict[str, Any]) -> bool:
        """Check if an entry passes current filters.

        Args:
            entry: Log entry to check

        Returns:
            True if entry passes all filters
        """
        # Check level filter
        level = entry.get("level", "INFO")
        if level not in self._enabled_levels:
            return False

        # Check search filter
        if self._search_text:
            search_text = self._search_text
            if not self._case_sensitive:
                search_text = search_text.lower()

            # Search in message and other text fields
            text_to_search = str(entry).lower() if not self._case_sensitive else str(entry)
            if search_text not in text_to_search:
                return False

        return True

    def _schedule_render(self) -> None:
        """Schedule a render operation with burst coalescing."""
        with self._render_lock:
            if self._pending_render:
                return  # Already scheduled

            current_time = time.time()
            time_since_last_render = (current_time - self._last_render_time) * 1000

            if time_since_last_render >= self.coalesce_interval_ms:
                # Render immediately
                self._render_immediately()
            else:
                # Schedule delayed render using threading instead of asyncio
                self._pending_render = True
                if self._render_timer:
                    self._render_timer.cancel()

                delay = (self.coalesce_interval_ms - time_since_last_render) / 1000.0
                self._render_timer = threading.Timer(delay, self._delayed_render_sync)
                self._render_timer.start()

    def _render_immediately(self) -> None:
        """Render immediately without delay."""
        self._last_render_time = time.time()
        self._total_rendered += 1

        if self.render_callback:
            try:
                self.render_callback()
            except Exception as e:
                self.logger.error("Error in render callback", error=str(e))

    def _delayed_render_sync(self) -> None:
        """Render after a delay for burst coalescing (synchronous version)."""
        with self._render_lock:
            if self._pending_render:
                self._pending_render = False
                self._render_immediately()

    def cleanup(self) -> None:
        """Clean up resources and cancel pending operations."""
        with self._render_lock:
            if self._render_timer:
                self._render_timer.cancel()
                self._render_timer = None
            self._pending_render = False

        self.logger.debug("Cleaned up log buffer resources")
