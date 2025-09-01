# Textual Library Typing Issues

## Overview

The Textual library currently does not ship with official type stubs (.pyi files) or inline typing across its API. This is a known limitation that affects type checking in projects using Textual.

## Impact on DShield MCP

### MyPy Errors
When running MyPy on TUI-related files, you will see numerous errors related to:
- Missing type annotations for Textual classes and methods
- Untyped decorators making functions untyped
- Incompatible type assignments with Textual objects
- Missing return type annotations for Textual methods

### Files Affected
- `src/tui/tui_app.py`
- `src/tui/api_key_panel.py`
- `src/tui/connection_panel.py`
- `src/tui/log_panel.py`
- `src/tui/server_panel.py`
- `src/tui/status_bar.py`
- `src/tui/screens/api_key_screen.py`
- `tests/tui/` (all test files)

## Current Mitigation

### MyPy Configuration
We have configured MyPy to ignore missing imports for the Textual library:

```ini
[mypy-textual.*]
ignore_missing_imports = True
# Note: Textual library does not provide type stubs (.pyi files) or inline typing
# This causes mypy to treat textual objects as Any, which is expected behavior
```

### Type Ignore Comments
In TUI files, we use `# type: ignore` comments for Textual imports:

```python
from textual.app import App, ComposeResult  # type: ignore
from textual.containers import Container  # type: ignore
from textual.widgets import Header, Footer  # type: ignore
```

## Expected Behavior

### What's Normal
- MyPy treating Textual objects as `Any` type
- Type checker warnings about untyped Textual methods
- Inability to get full type safety for TUI components

### What's Not Normal
- Runtime errors due to Textual usage
- Functional issues with the TUI
- Problems with Textual's actual API

## Future Considerations

### Textual Community
The Textual community is aware of this limitation. Future versions may include:
- Official type stubs
- Inline type annotations
- Better type checking support

### Alternative Approaches
If strict typing is required for TUI components, consider:
1. Creating custom type stubs for commonly used Textual classes
2. Using `# type: ignore` comments strategically
3. Focusing type checking on non-TUI components

## Recommendations

1. **Accept the Limitation**: TUI-related MyPy errors are expected and should not block development
2. **Focus on Core Logic**: Prioritize type checking on business logic, not UI components
3. **Document Decisions**: Clearly mark TUI files as having expected type checking limitations
4. **Monitor Updates**: Watch for Textual library updates that might improve typing support

## Example of Expected MyPy Output

```
src/tui/tui_app.py:12: error: Unused "type: ignore" comment  [unused-ignore]
    from textual.app import App, ComposeResult  # type: ignore
    ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
src/tui/tui_app.py:30: error: Function is missing a return type annotation  [no-untyped-def]
    def _get_dshield_mcp_server():
    ^
```

These errors are expected and should be treated as low priority in the overall code quality assessment.
