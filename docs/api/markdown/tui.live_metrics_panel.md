# live_metrics_panel

Live metrics panel for DShield MCP TUI.

This module provides a live metrics panel that displays real-time metrics
with stable formatting and threshold cues.

## LiveMetricsPanel

Live metrics panel for displaying real-time server metrics.

    This panel subscribes to metrics updates and displays them with
    stable formatting and threshold cues.

#### __init__

```python
def __init__(self, metrics_subscriber, id)
```

Initialize the live metrics panel.

        Args:
            metrics_subscriber: Metrics subscriber instance
            id: Widget ID

#### on_mount

```python
def on_mount(self)
```

Handle widget mount event.

#### on_unmount

```python
def on_unmount(self)
```

Handle widget unmount event.

#### _initialize_display

```python
def _initialize_display(self)
```

Initialize the display components.

#### _on_metrics_update

```python
def _on_metrics_update(self, update)
```

Handle metrics update from subscriber.

        Args:
            update: Metrics update message

#### _update_display

```python
def _update_display(self)
```

Update the display with current metrics.

#### _display_loading_state

```python
def _display_loading_state(self)
```

Display loading state when no metrics are available.

#### _display_error_state

```python
def _display_error_state(self, error_message)
```

Display error state when metrics update fails.

        Args:
            error_message: Error message to display

#### _update_connections_display

```python
def _update_connections_display(self)
```

Update the connections metrics display.

#### _update_rps_display

```python
def _update_rps_display(self)
```

Update the RPS metrics display.

#### _update_violations_display

```python
def _update_violations_display(self)
```

Update the violations metrics display.

#### _update_server_state_display

```python
def _update_server_state_display(self)
```

Update the server state metrics display.

#### get_display_statistics

```python
def get_display_statistics(self)
```

Get display statistics for monitoring.

        Returns:
            Dictionary of display statistics

#### force_refresh

```python
def force_refresh(self)
```

Force a refresh of the metrics display.

#### set_metrics_subscriber

```python
def set_metrics_subscriber(self, subscriber)
```

Set the metrics subscriber for this panel.

        Args:
            subscriber: Metrics subscriber instance

#### cleanup

```python
def cleanup(self)
```

Cleanup resources when panel is destroyed.
