#!/usr/bin/env python3
"""Metrics subscription system for DShield MCP TUI.

This module provides a subscription system for periodic metrics updates
with stable formatting and no flicker during updates.
"""

import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import Any

import structlog
from textual.message import Message  # type: ignore

from .metrics_formatter import MetricsFormatter, ServerMetrics

logger = structlog.get_logger(__name__)


class MetricsUpdate(Message):
    """Message sent when metrics are updated.

    Attributes:
        metrics: Updated metrics data
        timestamp: When the update occurred
    """

    def __init__(self, metrics: ServerMetrics, timestamp: datetime) -> None:
        """Initialize metrics update message.

        Args:
            metrics: Updated metrics data
            timestamp: When the update occurred
        """
        super().__init__()
        self.metrics = metrics
        self.timestamp = timestamp


class MetricsSubscriber:
    """Subscription system for periodic metrics updates.

    This class manages subscriptions to metrics updates, handles periodic
    collection of metrics data, and ensures stable formatting without flicker.
    """

    def __init__(self, update_interval: float = 1.0, max_subscribers: int = 100) -> None:
        """Initialize the metrics subscriber.

        Args:
            update_interval: Interval between metrics updates in seconds
            max_subscribers: Maximum number of subscribers allowed
        """
        self.update_interval = update_interval
        self.max_subscribers = max_subscribers
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")

        # Subscription management
        self.subscribers: set[Callable[[MetricsUpdate], None]] = set()
        self.is_running = False
        self.update_task: asyncio.Task | None = None

        # Metrics collection
        self.formatter = MetricsFormatter()
        self.last_metrics: ServerMetrics | None = None
        self.metrics_collector: Callable[[], dict[str, Any]] | None = None

        # Performance tracking
        self.update_count = 0
        self.last_update_time = datetime.now()
        self.average_update_duration = 0.0

    def set_metrics_collector(self, collector: Callable[[], dict[str, Any]]) -> None:
        """Set the metrics collection function.

        Args:
            collector: Function that returns raw metrics data
        """
        self.metrics_collector = collector
        self.logger.debug("Metrics collector set")

    def subscribe(self, callback: Callable[[MetricsUpdate], None]) -> bool:
        """Subscribe to metrics updates.

        Args:
            callback: Function to call when metrics are updated

        Returns:
            True if subscription was successful, False if at capacity
        """
        if len(self.subscribers) >= self.max_subscribers:
            self.logger.warning(
                "Cannot subscribe: maximum subscribers reached",
                current_count=len(self.subscribers),
                max_subscribers=self.max_subscribers,
            )
            return False

        self.subscribers.add(callback)
        self.logger.debug("Subscribed to metrics updates", subscriber_count=len(self.subscribers))
        return True

    def unsubscribe(self, callback: Callable[[MetricsUpdate], None]) -> bool:
        """Unsubscribe from metrics updates.

        Args:
            callback: Function to remove from subscriptions

        Returns:
            True if unsubscribed successfully, False if not found
        """
        if callback in self.subscribers:
            self.subscribers.remove(callback)
            self.logger.debug(
                "Unsubscribed from metrics updates", subscriber_count=len(self.subscribers)
            )
            return True

        self.logger.warning("Attempted to unsubscribe unknown callback")
        return False

    async def start(self) -> None:
        """Start the metrics subscription system."""
        if self.is_running:
            self.logger.warning("Metrics subscriber is already running")
            return

        if not self.metrics_collector:
            self.logger.error("Cannot start: no metrics collector set")
            return

        self.is_running = True
        self.update_task = asyncio.create_task(self._update_loop())
        self.logger.info("Metrics subscriber started", interval=self.update_interval)

    async def stop(self) -> None:
        """Stop the metrics subscription system."""
        if not self.is_running:
            self.logger.warning("Metrics subscriber is not running")
            return

        self.is_running = False

        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
            self.update_task = None

        self.logger.info("Metrics subscriber stopped")

    async def _update_loop(self) -> None:
        """Main update loop for metrics collection and distribution."""
        while self.is_running:
            try:
                start_time = datetime.now()

                # Collect and format metrics
                await self._collect_and_distribute_metrics()

                # Track performance
                update_duration = (datetime.now() - start_time).total_seconds()
                self._update_performance_stats(update_duration)

                # Wait for next update
                await asyncio.sleep(self.update_interval)

            except asyncio.CancelledError:
                self.logger.debug("Metrics update loop cancelled")
                break
            except Exception as e:
                self.logger.error("Error in metrics update loop", error=str(e))
                # Continue running even if one update fails
                await asyncio.sleep(self.update_interval)

    async def _collect_and_distribute_metrics(self) -> None:
        """Collect metrics and distribute to subscribers."""
        if not self.metrics_collector:
            return

        try:
            # Collect raw metrics
            raw_metrics = self.metrics_collector()

            # Format metrics
            formatted_metrics = self.formatter.format_all_metrics(raw_metrics)

            # Check if metrics have changed significantly
            if self._should_update_subscribers(formatted_metrics):
                self.last_metrics = formatted_metrics

                # Create update message
                update_message = MetricsUpdate(formatted_metrics, datetime.now())

                # Distribute to subscribers
                await self._distribute_to_subscribers(update_message)

                self.update_count += 1
                self.last_update_time = datetime.now()

        except Exception as e:
            self.logger.error("Error collecting metrics", error=str(e))

    def _should_update_subscribers(self, new_metrics: ServerMetrics) -> bool:
        """Determine if metrics have changed enough to notify subscribers.

        Args:
            new_metrics: Newly formatted metrics

        Returns:
            True if subscribers should be notified
        """
        if not self.last_metrics:
            return True

        # Check for significant changes in key metrics
        significant_changes = []

        # Check connection changes
        for key in ["total", "authenticated", "violations"]:
            if key in new_metrics.connections and key in self.last_metrics.connections:
                old_value = self.last_metrics.connections[key].value
                new_value = new_metrics.connections[key].value
                if abs(new_value - old_value) >= 1:  # At least 1 connection change
                    significant_changes.append(f"connections.{key}")

        # Check RPS changes
        for key in ["average", "peak"]:
            if key in new_metrics.rps and key in self.last_metrics.rps:
                old_value = self.last_metrics.rps[key].value
                new_value = new_metrics.rps[key].value
                if abs(new_value - old_value) >= 0.1:  # At least 0.1 RPS change
                    significant_changes.append(f"rps.{key}")

        # Check violation changes
        for key in ["total", "rate_limit", "abuse"]:
            if key in new_metrics.violations and key in self.last_metrics.violations:
                old_value = self.last_metrics.violations[key].value
                new_value = new_metrics.violations[key].value
                if new_value != old_value:  # Any violation change
                    significant_changes.append(f"violations.{key}")

        # Check server state changes
        for key in ["uptime_hours", "error_rate", "memory_usage"]:
            if key in new_metrics.server_state and key in self.last_metrics.server_state:
                old_value = self.last_metrics.server_state[key].value
                new_value = new_metrics.server_state[key].value
                if abs(new_value - old_value) >= 0.1:  # At least 0.1 change
                    significant_changes.append(f"server_state.{key}")

        if significant_changes:
            self.logger.debug("Significant metrics changes detected", changes=significant_changes)
            return True

        return False

    async def _distribute_to_subscribers(self, update_message: MetricsUpdate) -> None:
        """Distribute metrics update to all subscribers.

        Args:
            update_message: Metrics update message to distribute
        """
        if not self.subscribers:
            return

        # Create tasks for all subscribers to run concurrently
        tasks = []
        for subscriber in self.subscribers.copy():  # Copy to avoid modification during iteration
            task = asyncio.create_task(self._notify_subscriber(subscriber, update_message))
            tasks.append(task)

        # Wait for all notifications to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _notify_subscriber(
        self, subscriber: Callable[[MetricsUpdate], None], update_message: MetricsUpdate
    ) -> None:
        """Notify a single subscriber of metrics update.

        Args:
            subscriber: Subscriber callback function
            update_message: Metrics update message
        """
        try:
            # Run subscriber callback
            if asyncio.iscoroutinefunction(subscriber):
                await subscriber(update_message)
            else:
                subscriber(update_message)

        except Exception as e:
            self.logger.error(
                "Error notifying subscriber", error=str(e), subscriber=str(subscriber)
            )

    def _update_performance_stats(self, update_duration: float) -> None:
        """Update performance statistics.

        Args:
            update_duration: Duration of the last update in seconds
        """
        # Calculate rolling average of update duration
        if self.average_update_duration == 0.0:
            self.average_update_duration = update_duration
        else:
            # Simple exponential moving average
            alpha = 0.1
            self.average_update_duration = (
                alpha * update_duration + (1 - alpha) * self.average_update_duration
            )

    def get_performance_stats(self) -> dict[str, Any]:
        """Get performance statistics for the metrics subscriber.

        Returns:
            Dictionary of performance statistics
        """
        return {
            "is_running": self.is_running,
            "subscriber_count": len(self.subscribers),
            "update_count": self.update_count,
            "last_update_time": self.last_update_time.isoformat(),
            "average_update_duration": self.average_update_duration,
            "update_interval": self.update_interval,
        }

    def get_current_metrics(self) -> ServerMetrics | None:
        """Get the most recent metrics.

        Returns:
            Most recent ServerMetrics or None if no metrics collected yet
        """
        return self.last_metrics

    def force_update(self) -> None:
        """Force an immediate metrics update.

        This can be called to trigger an immediate update outside the normal
        update interval, useful for testing or manual refresh.
        """
        if self.is_running and self.metrics_collector:
            asyncio.create_task(self._collect_and_distribute_metrics())
            self.logger.debug("Forced metrics update")
