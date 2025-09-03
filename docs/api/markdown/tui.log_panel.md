# log_panel

Log display panel for DShield MCP TUI.

This module provides a terminal UI panel for displaying real-time logs,
including filtering, searching, and log level management.

## LogFilterUpdate

Message sent when log filter is updated.

#### __init__

```python
def __init__(self, filter_config)
```

Initialize log filter update message.

        Args:
            filter_config: Log filter configuration

## LogClear

Message sent when logs should be cleared.

## LogExport

Message sent when logs should be exported.

#### __init__

```python
def __init__(self, export_path)
```

Initialize log export message.

        Args:
            export_path: Path to export logs to

## LogPanel

Panel for displaying and managing logs.

    This panel provides real-time log display with filtering, searching,
    and export capabilities.

#### __init__

```python
def __init__(self, id)
```

Initialize the log panel.

        Args:
            id: Panel ID

#### compose

```python
def compose(self)
```

Compose the log panel layout.

        Returns:
            ComposeResult: The composed UI elements

#### on_mount

```python
def on_mount(self)
```

Handle panel mount event.

#### add_log_entries

```python
def add_log_entries(self, entries)
```

Add new log entries to the display.

        Args:
            entries: List of log entries to add

#### clear_logs

```python
def clear_logs(self)
```

Clear all log entries.

#### _apply_filters

```python
def _apply_filters(self)
```

Apply current filters to log entries.

#### _update_display

```python
def _update_display(self)
```

Update the log display with filtered entries.

#### _format_log_entry

```python
def _format_log_entry(self, entry)
```

Format a log entry for display.

        Args:
            entry: Log entry dictionary

        Returns:
            Formatted log entry string

#### on_button_pressed

```python
def on_button_pressed(self, event)
```

Handle button press events.

        Args:
            event: Button press event

#### on_checkbox_changed

```python
def on_checkbox_changed(self, event)
```

Handle checkbox change events.

        Args:
            event: Checkbox change event

#### on_input_changed

```python
def on_input_changed(self, event)
```

Handle input field changes.

        Args:
            event: Input change event

#### _clear_logs

```python
def _clear_logs(self)
```

Clear all logs.

#### _export_logs

```python
def _export_logs(self)
```

Export logs to file.

#### _toggle_auto_scroll

```python
def _toggle_auto_scroll(self)
```

Toggle auto-scroll mode.

#### _toggle_pause

```python
def _toggle_pause(self)
```

Toggle log pause mode.

#### _clear_search

```python
def _clear_search(self)
```

Clear search input.

#### get_log_statistics

```python
def get_log_statistics(self)
```

Get log statistics.

        Returns:
            Dictionary of log statistics

#### set_max_entries

```python
def set_max_entries(self, max_entries)
```

Set maximum number of log entries to keep.

        Args:
            max_entries: Maximum number of entries
