# log_buffer

Bounded log buffer with filtering and burst coalescing for DShield MCP TUI.

This module provides a ring buffer implementation for log entries with level filtering,
substring search, and burst coalescing to optimize rendering performance.

## LogBuffer

Bounded log buffer with filtering and burst coalescing.
    
    This class implements a ring buffer for log entries with the following features:
    - Ring buffer capped at log_history_size
    - Level filtering (DEBUG/INFO/WARN/ERROR)
    - Substring search (case-insensitive)
    - Burst coalescing (≤1 render per N ms)
    - Thread-safe operations

#### __init__

```python
def __init__(self, max_size, coalesce_interval_ms, render_callback)
```

Initialize the log buffer.
        
        Args:
            max_size: Maximum number of log entries to keep
            coalesce_interval_ms: Minimum interval between renders in milliseconds
            render_callback: Callback function to call when rendering is needed

#### add_entry

```python
def add_entry(self, entry)
```

Add a log entry to the buffer.
        
        Args:
            entry: Log entry dictionary with at least 'level' and 'message' keys

#### add_entries

```python
def add_entries(self, entries)
```

Add multiple log entries to the buffer.
        
        Args:
            entries: List of log entry dictionaries

#### get_filtered_entries

```python
def get_filtered_entries(self)
```

Get all entries that pass current filters.
        
        Returns:
            List of filtered log entries

#### get_all_entries

```python
def get_all_entries(self)
```

Get all entries in the buffer.
        
        Returns:
            List of all log entries

#### clear

```python
def clear(self)
```

Clear all entries from the buffer.

#### set_level_filter

```python
def set_level_filter(self, levels)
```

Set the level filter.
        
        Args:
            levels: Set of log levels to include (e.g., {"DEBUG", "INFO", "ERROR"})

#### set_search_filter

```python
def set_search_filter(self, search_text, case_sensitive)
```

Set the search filter.
        
        Args:
            search_text: Text to search for in log entries
            case_sensitive: Whether search should be case-sensitive

#### get_statistics

```python
def get_statistics(self)
```

Get buffer statistics.
        
        Returns:
            Dictionary containing buffer statistics

#### _normalize_entry

```python
def _normalize_entry(self, entry)
```

Normalize a log entry for consistent processing.
        
        Args:
            entry: Raw log entry
            
        Returns:
            Normalized log entry

#### _passes_filters

```python
def _passes_filters(self, entry)
```

Check if an entry passes current filters.
        
        Args:
            entry: Log entry to check
            
        Returns:
            True if entry passes all filters

#### _schedule_render

```python
def _schedule_render(self)
```

Schedule a render operation with burst coalescing.

#### _render_immediately

```python
def _render_immediately(self)
```

Render immediately without delay.

#### cleanup

```python
def cleanup(self)
```

Clean up resources and cancel pending operations.
