# metrics_subscriber

Metrics subscription system for DShield MCP TUI.

This module provides a subscription system for periodic metrics updates
with stable formatting and no flicker during updates.

## MetricsUpdate

Message sent when metrics are updated.

    Attributes:
        metrics: Updated metrics data
        timestamp: When the update occurred

#### __init__

```python
def __init__(self, metrics, timestamp)
```

Initialize metrics update message.

        Args:
            metrics: Updated metrics data
            timestamp: When the update occurred

## MetricsSubscriber

Subscription system for periodic metrics updates.

    This class manages subscriptions to metrics updates, handles periodic
    collection of metrics data, and ensures stable formatting without flicker.

#### __init__

```python
def __init__(self, update_interval, max_subscribers)
```

Initialize the metrics subscriber.

        Args:
            update_interval: Interval between metrics updates in seconds
            max_subscribers: Maximum number of subscribers allowed

#### set_metrics_collector

```python
def set_metrics_collector(self, collector)
```

Set the metrics collection function.

        Args:
            collector: Function that returns raw metrics data

#### subscribe

```python
def subscribe(self, callback)
```

Subscribe to metrics updates.

        Args:
            callback: Function to call when metrics are updated

        Returns:
            True if subscription was successful, False if at capacity

#### unsubscribe

```python
def unsubscribe(self, callback)
```

Unsubscribe from metrics updates.

        Args:
            callback: Function to remove from subscriptions

        Returns:
            True if unsubscribed successfully, False if not found

#### _should_update_subscribers

```python
def _should_update_subscribers(self, new_metrics)
```

Determine if metrics have changed enough to notify subscribers.

        Args:
            new_metrics: Newly formatted metrics

        Returns:
            True if subscribers should be notified

#### _update_performance_stats

```python
def _update_performance_stats(self, update_duration)
```

Update performance statistics.

        Args:
            update_duration: Duration of the last update in seconds

#### get_performance_stats

```python
def get_performance_stats(self)
```

Get performance statistics for the metrics subscriber.

        Returns:
            Dictionary of performance statistics

#### get_current_metrics

```python
def get_current_metrics(self)
```

Get the most recent metrics.

        Returns:
            Most recent ServerMetrics or None if no metrics collected yet

#### force_update

```python
def force_update(self)
```

Force an immediate metrics update.

        This can be called to trigger an immediate update outside the normal
        update interval, useful for testing or manual refresh.
