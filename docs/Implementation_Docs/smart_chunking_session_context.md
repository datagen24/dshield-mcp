# Smart Chunking with Session Context Implementation

## Overview
This document describes the implementation of smart chunking with session context in the DShield MCP backend. This feature enables event streaming and chunking that preserves session boundaries, making it easier to correlate related events and analyze attack patterns.

## What is Session Context?
Session context refers to a set of fields that uniquely identify a logical session or connection, such as:
- `source.ip`
- `destination.ip`
- `user.name`
- `session.id`

Events sharing the same values for these fields are considered part of the same session.

## Key Features
- **Session-aware chunking:** Events are grouped and streamed in chunks that do not split sessions across chunk boundaries.
- **Customizable session fields:** The fields used to define a session can be specified per query.
- **Session summaries:** Each chunk includes summaries of the sessions it contains (event count, duration, metadata).
- **Performance metrics:** Each response includes query time, sessions processed, and other metrics.
- **Cursor-based streaming:** Supports resuming streams with a `stream_id`.

## API Usage
### Tool: `stream_dshield_events_with_session_context`
**Parameters:**
- `time_range_hours`: Time range to query (default: 24)
- `indices`: Indices to query (optional)
- `filters`: Query filters (supports user-friendly field names)
- `fields`: Fields to return (optional)
- `chunk_size`: Target chunk size (default: 500)
- `session_fields`: Fields to use for session grouping (default: `["source.ip", "destination.ip", "user.name", "session.id"]`)
- `max_session_gap_minutes`: Max time gap within a session (default: 30)
- `include_session_summary`: Include session metadata in response (default: true)
- `stream_id`: Resume streaming from a specific point (optional)

### Example Response
```json
{
  "events": [ ... ],
  "total_count": 1000,
  "next_stream_id": "2025-07-06T10:00:00Z|abc123",
  "session_context": {
    "session_fields": ["source.ip", "destination.ip", "user.name", "session.id"],
    "sessions_in_chunk": 12,
    "session_summaries": [
      {
        "session_key": "source.ip:1.2.3.4|destination.ip:5.6.7.8",
        "event_count": 8,
        "first_timestamp": "2025-07-06T09:55:00Z",
        "last_timestamp": "2025-07-06T10:00:00Z",
        "duration_minutes": 5.0,
        "metadata": {"source.ip": "1.2.3.4", "destination.ip": "5.6.7.8"}
      }
    ],
    "performance_metrics": {
      "query_time_ms": 42,
      "sessions_processed": 12,
      "session_chunks_created": 1
    }
  }
}
```

## Implementation Details
- Implemented in `src/elasticsearch_client.py` as `stream_dshield_events_with_session_context`
- Session keys are generated from the specified fields; events without session context are grouped separately
- Session summaries include event count, duration, and metadata for each session in the chunk
- Fully integrated with the MCP server and available as a tool

## Extensibility
- Additional session fields can be added as needed
- Session-aware analytics (e.g., session timelines, anomaly detection) can be built on top of this foundation

## Testing
- See `dev_tools/test_smart_chunking.py` for comprehensive test coverage and usage examples

## Dependencies

- **Python Packages:**
  - `elasticsearch` (for query execution and session-aware chunking)
  - `structlog` (for structured logging and error reporting)
- **Elasticsearch:**
  - Requires a running Elasticsearch instance (version 7.x or 8.x recommended)
- **Testing:**
  - `pytest` for test scripts

## 🔒 Security Implications

- **Input Validation:** All chunking and session context parameters (`chunk_size`, `session_fields`, `max_session_gap_minutes`, filters, stream_id) are validated to prevent injection attacks and ensure only valid values are processed.
- **Resource Controls:** Limits are enforced on `chunk_size` (default: 500, max: 1000) and session grouping to prevent excessive memory or resource usage and mitigate DoS risks.
- **Error Handling:** Robust error handling and logging are implemented for all chunking and session context operations. Errors are logged to stderr with context, and no sensitive information is exposed to clients.
- **Data Exposure:** Only authorized users and tools can access session-aware streaming results. Sensitive data is redacted or summarized in client-facing outputs as appropriate.
- **Protocol Compliance:** All MCP communications use JSON-RPC 2.0 with strict schema validation, preventing malformed or malicious requests from affecting the server.

## 🔄 Migration Notes

- **Backward Compatibility:** The smart chunking with session context feature is fully backward compatible. Existing queries without session context parameters will continue to work as before, with default values applied.
- **Configuration:** No additional configuration is required. Session context parameters are optional and have sensible defaults (`chunk_size=500`, `session_fields=["source.ip", "destination.ip", "user.name", "session.id"]`).
- **Upgrade Steps:**
  1. Update your MCP server and dependencies to the latest version.
  2. Review and test smart chunking features with your existing workflows.
  3. Monitor performance and resource usage after deployment, and adjust chunk size or session fields as needed.
- **Deprecations:** No breaking changes or deprecated features are introduced in this release. All previous query functionality is preserved.
