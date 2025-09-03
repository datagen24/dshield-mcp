# status_bar

Status bar for DShield MCP TUI.

This module provides a status bar widget for displaying real-time status
information including server status, connection counts, and system metrics.

## StatusBar

Status bar widget for displaying real-time status information.

    This widget shows server status, connection counts, system metrics,
    and other relevant information in a compact format.

#### __init__

```python
def __init__(self, id)
```

Initialize the status bar.

        Args:
            id: Widget ID

#### on_mount

```python
def on_mount(self)
```

Handle widget mount event.

#### update_server_status

```python
def update_server_status(self, status)
```

Update server status information.

        Args:
            status: Server status dictionary

#### update_connection_count

```python
def update_connection_count(self, total, authenticated)
```

Update connection count information.

        Args:
            total: Total number of connections
            authenticated: Number of authenticated connections

#### update_api_key_count

```python
def update_api_key_count(self, count)
```

Update API key count information.

        Args:
            count: Number of API keys

#### update_error_count

```python
def update_error_count(self, count)
```

Update error count information.

        Args:
            count: Number of errors

#### update_display

```python
def update_display(self)
```

Update the status bar display.

#### watch_connection_count

```python
def watch_connection_count(self, count)
```

Watch for connection count changes.

        Args:
            count: New connection count

#### watch_authenticated_count

```python
def watch_authenticated_count(self, count)
```

Watch for authenticated count changes.

        Args:
            count: New authenticated count

#### watch_api_key_count

```python
def watch_api_key_count(self, count)
```

Watch for API key count changes.

        Args:
            count: New API key count

#### watch_error_count

```python
def watch_error_count(self, count)
```

Watch for error count changes.

        Args:
            count: New error count

#### watch_last_update

```python
def watch_last_update(self, update_time)
```

Watch for last update time changes.

        Args:
            update_time: New update time

#### get_status_summary

```python
def get_status_summary(self)
```

Get a summary of current status information.

        Returns:
            Dictionary of status summary

#### set_status_message

```python
def set_status_message(self, message, timeout)
```

Set a temporary status message.

        Args:
            message: Status message to display
            timeout: Optional timeout in seconds to revert to normal status

#### add_status_indicator

```python
def add_status_indicator(self, indicator, value)
```

Add a status indicator to the display.

        Args:
            indicator: Indicator name
            value: Indicator value

#### remove_status_indicator

```python
def remove_status_indicator(self, indicator)
```

Remove a status indicator from the display.

        Args:
            indicator: Indicator name to remove
