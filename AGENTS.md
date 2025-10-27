# AGENTS Guidelines for dshield-mcp

This repository uses Cursor rules (see `.cursor/rules`) to codify coding, documentation, testing, security, and MCP integration practices. As an agent contributing to this codebase, follow the guidance below. These rules apply to the entire repository unless a more specific rule is present in a nested AGENTS.md.

## Objectives

- Keep changes focused, minimal, and aligned with the existing architecture.
- Prefer correctness, safety, and maintainability over cleverness.
- Preserve backward compatibility and graceful degradation wherever possible.

## Language, Style, and Tooling

- Python baseline: 3.10+ (type hints required; prefer `from __future__ import annotations` if needed).
- Lint: `ruff` with a 100‑char line limit; reduce complexity (C901) by extracting helpers.
- Formatting: keep lines ≤ 100 chars; wrap nested dicts; avoid overly long one‑liners.
- Types: add precise type hints for public APIs and internal helpers.
- Logging: use `structlog`; avoid logging secrets or PII.
- Errors: prefer structured error handling via `src/mcp_error_handler.py`.

## Documentation (py-docs-rule)

- Write Google‑style docstrings for:
  - All modules, classes, methods, and functions.
  - Include Args/Parameters (with types), Returns (with types), Raises, and Examples where useful.
  - Include doctest‑friendly snippets when it improves clarity.
- Keep docstrings accurate with signatures/behavior.
- Generate docs after changes using the project script:
  - `uv run python scripts/build_api_docs.py`
  - Or `./scripts/build_api_docs.sh` where available
  - Do not hand-roll pdoc/pydoc-markdown commands unless debugging

## Project Structure (ac-structure)

- Place code under `src/` with cohesive, testable modules.
- Add tests under `tests/`, mirroring module structure.
- Keep examples in `examples/` and templates in `templates/`.

## Testing (mcp-testing)

- Use `pytest`; write tests for new features, edge cases, and regressions.
- Aim for high coverage; tests should be focused and reliable.
- Prefer unit tests near code changes; add integration tests when behavior crosses module boundaries.
- Include edge cases: no data, single bucket, zero std/variance, invalid inputs.

## Configuration & Secrets (aa-config-mgmt, ab-secrets-mgmt)

- Project config: `mcp_config.yaml` (resolved via 1Password CLI op://), and layered user config via `user_config.yaml` / env vars.
- Never hardcode secrets. Always reference secrets via `op://...` and resolve with the existing `OnePasswordSecrets` utilities.
- Validate config updates; fail fast with clear messages and graceful fallbacks.

## Security (mcp-security, security_guideline_document)

- Follow least‑privilege; enforce rate limiting and circuit breakers.
- Avoid logging sensitive data; use redaction utilities where available.
- Validate inputs (fields, sizes, message lengths) and reject unsafe patterns.

## Error Handling (ab-error-hand)

- Use `MCPErrorHandler` for JSON‑RPC error responses and timeouts.
- Convert exceptions to structured errors with actionable messages.
- Respect retry policies and circuit breaker status; prefer graceful degradation over crashes.

## Performance & Optimization (aa-optimize, mcp-performance)

- Prefer fast paths by default; gate heavy operations behind flags/config.
- Use streaming and pagination where supported; keep timeouts reasonable.
- Add telemetry (latency, sizes) when helpful; log performance at INFO only if enabled in config.

## MCP Tools & Protocol (mcp-protocol-core)

- When adding/updating a tool:
  - Define tool schema in `mcp_server.py` (list_tools) with clear param types and descriptions.
  - Add to `src/dynamic_tool_registry.py` mapping with correct feature dependency.
  - Respect feature flags/health checks so tools only appear when their dependencies are healthy.
  - Provide resources and prompts if applicable.

### MCP Tool Schema: detect_statistical_anomalies

When modifying parameters for `detect_statistical_anomalies`, update both:
- Input schema in `mcp_server.py` (under `all_tool_definitions` in `handle_list_tools`).
- The tool call implementation `_detect_statistical_anomalies` to forward new args to
  `StatisticalAnalysisTools.detect_statistical_anomalies`.

Current args to expose (keep descriptions concise; heavy paths optional):
- `time_range_hours` (int)
- `anomaly_methods` (list[str]) — zscore, iqr, isolation_forest, time_series
- `sensitivity` (number)
- `dimensions` (list[str]) — ignored when `dimension_schema` is provided
- `return_summary_only` (bool)
- `max_anomalies` (int)
- `dimension_schema` (object) — name → {field, agg, size?, interval?, percents?}
- `enable_iqr` (bool)
- `enable_percentiles` (bool)
- `time_series_mode` ("fast"|"robust")
- `seasonality_hour_of_day` (bool)
- `raw_sample_mode` (bool)
- `raw_sample_size` (int)
- `min_iforest_samples` (int)
- `scale_iforest_features` (bool)

## Transports & TUI (mcp-stdio-transport)

- Default transport is STDIO; TCP requires authentication and rate limiting.
- Keep transport detection logic intact; do not degrade STDIO behavior.
- TUI interactions should set environment flags and manage the server process cleanly.

## Branch, Commits, and PRs (aa-branch-mgmt, aa-github-pr)

- Branch names: `feature/<short-description>`, `fix/<short-description>`, `chore/<task>`.
- Commits: small, descriptive, imperative tense. Reference issues when relevant.
- PRs: include summary, rationale, scope, testing notes, and any migrations. Link docs/tests.
- CI: ensure lint/tests/docs generation succeed locally before PR.

## Dependency Management & Snyk (aa-snyk)

- Keep dependencies pinned; avoid unnecessary new packages.
- Use provided scripts (e.g., `scripts/security_scan.py`) for scans where applicable.

## Implementation Checklist for Agents

1. Read relevant Cursor rules in `.cursor/rules` before large changes.
2. Design changes to be modular and minimal; prefer adding helpers over increasing function complexity.
3. Update/author comprehensive docstrings (Google style) and examples.
4. Add or update unit tests; cover edge cases and negative paths.
5. Ensure `ruff` passes (line length ≤ 100, complexity within limits).
6. Use `structlog` for logs; no sensitive content in logs.
7. Wire new MCP tools into: tool schema, tool registry, feature flags, and health checks.
8. Validate configuration and secrets usage; no plaintext secrets.
9. Generate/refresh API docs (HTML + Markdown) as part of PR workflow.
10. Prepare a concise PR summary with risk, testing, and rollback notes.

## Do / Don’t

- Do
  - Keep changes surgical; follow existing patterns and naming.
  - Prefer explicit types and small helpers to reduce complexity.
  - Handle failures gracefully and return structured errors.
  - Gate expensive operations behind flags; document tunables.

- Don’t
  - Introduce breaking changes without migration/documentation.
  - Log secrets, credentials, or large payloads.
  - Bypass `MCPErrorHandler` or feature gating.
  - Add external services without config/health checks.

## File Placement & Naming

- New modules: `src/<domain>/<module>.py` or `src/<module>.py` consistent with current layout.
- Tests: `tests/<domain>/test_<module>.py` or `tests/test_<feature>.py`.
- Docs: Module/class/function docstrings; generated API docs in `docs/api` and `docs/api/markdown`.

## Examples

- Add examples to `examples/` when you introduce new tool flows or patterns.
- Keep examples minimal, safe, and runnable via `uv run` or active virtualenv.

---

Questions or ambiguities: prefer following `.cursor/rules` documents first; if a conflict exists, align with the repository’s README and contributor documentation, and preserve backward‑compatible behavior.
