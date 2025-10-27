# Contributing Guide

## Development Setup

### Prerequisites

- Python 3.10 or higher
- UV package manager
- 1Password CLI (for secrets management)
- Git

### Installation

```bash
# Install UV package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone https://github.com/datagen24/dshield-mcp.git
cd dshield-mcp

# Install dependencies
uv sync

# Install development dependencies
uv sync --group dev

# Copy environment template
cp .env.example .env
```

## Development Workflow

### Branch Management

**NEVER work directly on main branch.** Always create a feature or bugfix branch:

```bash
# Feature branch
git checkout -b feature/your-feature-name

# Bug fix branch
git checkout -b bugfix/issue-description

# Refactoring branch
git checkout -b refactor/what-you-are-refactoring
```

### Code Quality

#### Linting with Ruff

```bash
# Check for issues
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .
```

#### Formatting with Ruff

```bash
# Format code
uv run ruff format .
```

#### Type Checking with mypy

```bash
# Run type checker
uv run mypy src/
```

### Testing

Run tests before committing:

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/mcp/test_mcp_server_refactored.py
```

## Coding Standards

### Python Code Style

- **Type Annotations**: All functions and classes must have typing annotations
- **Docstrings**: Use PEP257 convention (Google style)
- **Line Length**: Maximum 100 characters
- **Imports**: Use `ruff` for import organization

### Documentation

- **Implementation Docs**: Create documentation in `docs/` for all new features
- **Docstrings**: All public functions, classes, and methods must have docstrings
- **Type Hints**: Required for all function parameters and return values

### Secrets Management

**NEVER hardcode secrets.** Use 1Password CLI integration:

```python
# Good: 1Password reference
ELASTICSEARCH_PASSWORD=op://DevSecOps/es-data01-elastic/password

# Bad: Hardcoded secret
ELASTICSEARCH_PASSWORD=my-secret-password
```

## Creating Pull Requests

### Using GitHub CLI

```bash
# Create PR with body from file
gh pr create --title "feat: Add new feature" --body-file PR_DESCRIPTION.md

# Create PR with inline description
gh pr create --title "fix: Fix bug" --body "Description of the fix"
```

### PR Guidelines

1. **Clear Title**: Use conventional commit format (feat:, fix:, refactor:, docs:)
2. **Detailed Description**: Explain what and why, not just how
3. **Link Issues**: Reference related issues with #issue-number
4. **Test Coverage**: Include tests for new features
5. **Documentation**: Update docs for user-facing changes

### PR Template

```markdown
## Summary
Brief description of changes

## Changes
- List of specific changes
- Another change

## Testing
- How to test these changes
- What was tested

## Related Issues
Fixes #123
Related to #456
```

## Code Review

All PRs require:

1. **Passing Tests**: All CI checks must pass
2. **Code Review**: At least one approval
3. **Up to Date**: Must be up to date with main branch
4. **Conflicts Resolved**: No merge conflicts

## Release Process

1. Update `CHANGELOG.md` with changes
2. Update version in `pyproject.toml`
3. Create release notes in `docs/`
4. Tag release: `git tag v1.0.0`
5. Push tags: `git push --tags`

## Getting Help

- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Ask questions in GitHub Discussions
- **Documentation**: Check docs/ directory first

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Help others learn and grow
