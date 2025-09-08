#!/usr/bin/env python3
"""
Code Quality Cleanup Report Generator.

This script generates a comprehensive report of code quality improvements
including ruff violations, mypy issues, docstring coverage, and test coverage.
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_command(cmd: list[str], cwd: Path | None = None) -> tuple[str, str, int]:
    """Run a command and return stdout, stderr, and return code."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=cwd or Path.cwd(), timeout=300
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 1
    except Exception as e:
        return "", str(e), 1


def get_ruff_violations() -> dict[str, Any]:
    """Get ruff violations and statistics."""
    print("🔍 Running ruff check...")

    # Run ruff check with statistics
    stdout, stderr, returncode = run_command(["ruff", "check", "src/", "tests/", "--statistics"])

    violations = {"total_violations": 0, "by_category": {}, "raw_output": stdout + stderr}

    # Parse statistics from output
    if stdout:
        lines = stdout.split('\n')
        for line in lines:
            if 'Found' in line and 'violation' in line:
                # Extract total violations
                match = re.search(r'Found (\d+) violation', line)
                if match:
                    violations["total_violations"] = int(match.group(1))

    return violations


def get_mypy_issues() -> dict[str, Any]:
    """Get mypy type checking issues."""
    print("🔍 Running mypy check...")

    stdout, stderr, returncode = run_command(
        ["mypy", "--strict", "src/", "--show-error-codes", "--pretty"]
    )

    issues = {
        "total_errors": 0,
        "by_file": {},
        "raw_output": stdout + stderr,
        "return_code": returncode,
    }

    # Count errors
    if stdout:
        error_lines = [line for line in stdout.split('\n') if 'error:' in line]
        issues["total_errors"] = len(error_lines)

    return issues


def get_docstring_coverage() -> dict[str, Any]:
    """Get docstring coverage statistics."""
    print("🔍 Checking docstring coverage...")

    stdout, stderr, returncode = run_command(
        ["ruff", "check", "src/", "tests/", "--select", "D", "--statistics"]
    )

    coverage = {"missing_docstrings": 0, "raw_output": stdout + stderr}

    # Parse docstring violations
    if stdout:
        lines = stdout.split('\n')
        for line in lines:
            if 'D' in line and 'violation' in line:
                match = re.search(r'(\d+) D', line)
                if match:
                    coverage["missing_docstrings"] = int(match.group(1))

    return coverage


def get_test_coverage() -> dict[str, Any]:
    """Get test coverage statistics."""
    print("🔍 Running test coverage...")

    stdout, stderr, returncode = run_command(
        ["pytest", "tests/", "--cov=src", "--cov-report=term-missing", "--cov-report=json"]
    )

    coverage = {
        "total_coverage": 0.0,
        "by_file": {},
        "raw_output": stdout + stderr,
        "return_code": returncode,
    }

    # Try to parse coverage from output
    if stdout:
        lines = stdout.split('\n')
        for line in lines:
            if 'TOTAL' in line and '%' in line:
                # Extract percentage
                match = re.search(r'(\d+)%', line)
                if match:
                    coverage["total_coverage"] = float(match.group(1))

    # Try to read coverage.json if it exists
    coverage_json = Path("coverage.json")
    if coverage_json.exists():
        try:
            with open(coverage_json) as f:
                data = json.load(f)
                coverage["total_coverage"] = data.get("totals", {}).get("percent_covered", 0.0)
                coverage["by_file"] = {
                    file: info.get("percent_covered", 0.0)
                    for file, info in data.get("files", {}).items()
                }
        except Exception as e:
            print(f"Warning: Could not parse coverage.json: {e}")

    return coverage


def generate_cleanup_report() -> dict[str, Any]:
    """Generate comprehensive cleanup report."""
    print("📊 Generating Code Quality Cleanup Report...")
    print("=" * 50)

    report = {
        "timestamp": subprocess.run(["date"], capture_output=True, text=True).stdout.strip(),
        "ruff_violations": get_ruff_violations(),
        "mypy_issues": get_mypy_issues(),
        "docstring_coverage": get_docstring_coverage(),
        "test_coverage": get_test_coverage(),
        "recommendations": [],
    }

    # Generate recommendations
    if report["ruff_violations"]["total_violations"] > 0:  # type: ignore[index]
        report["recommendations"].append(  # type: ignore[attr-defined]
            f"Fix {report['ruff_violations']['total_violations']} ruff violations"  # type: ignore[index]
        )

    if report["mypy_issues"]["total_errors"] > 0:  # type: ignore[index]
        report["recommendations"].append(  # type: ignore[attr-defined]
            f"Fix {report['mypy_issues']['total_errors']} mypy type errors"  # type: ignore[index]
        )

    if report["docstring_coverage"]["missing_docstrings"] > 0:  # type: ignore[index]
        report["recommendations"].append(  # type: ignore[attr-defined]
            f"Add {report['docstring_coverage']['missing_docstrings']} missing docstrings"  # type: ignore[index]
        )

    if report["test_coverage"]["total_coverage"] < 80:  # type: ignore[index]
        report["recommendations"].append(  # type: ignore[attr-defined]
            f"Increase test coverage from {report['test_coverage']['total_coverage']:.1f}% to 80%+"  # type: ignore[index]
        )

    return report


def print_summary(report: dict[str, Any]) -> None:
    """Print a summary of the report."""
    print("\n" + "=" * 50)
    print("📋 CODE QUALITY SUMMARY")
    print("=" * 50)

    print(f"🔧 Ruff Violations: {report['ruff_violations']['total_violations']}")
    print(f"🔍 MyPy Errors: {report['mypy_issues']['total_errors']}")
    print(f"📝 Missing Docstrings: {report['docstring_coverage']['missing_docstrings']}")
    print(f"🧪 Test Coverage: {report['test_coverage']['total_coverage']:.1f}%")

    if report["recommendations"]:
        print("\n🎯 RECOMMENDATIONS:")
        for i, rec in enumerate(report["recommendations"], 1):
            print(f"  {i}. {rec}")

    print("\n" + "=" * 50)


def main():
    """Main function."""
    try:
        report = generate_cleanup_report()

        # Save report to file
        with open("cleanup_report.json", "w") as f:
            json.dump(report, f, indent=2)

        print_summary(report)
        print("\n📄 Full report saved to: cleanup_report.json")

        return 0

    except Exception as e:
        print(f"❌ Error generating report: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
