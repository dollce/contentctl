#!/usr/bin/env python3
"""Format contentctl test results as a GitHub Step Summary markdown table."""

import json
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

RESULTS_DIR = Path("test_results")
SUMMARY_FILE = os.environ.get("GITHUB_STEP_SUMMARY", "")


def parse_yaml(filepath: Path) -> dict:
    """Parse a YAML file and return its contents."""
    if yaml is None:
        print(f"Warning: PyYAML not installed, skipping {filepath}")
        return {}
    with open(filepath, "r") as f:
        return yaml.safe_load(f) or {}


def parse_json(filepath: Path) -> dict:
    """Parse a JSON file and return its contents."""
    with open(filepath, "r") as f:
        return json.load(f)


def find_result_file() -> tuple:
    """Find and parse the test result file. Returns (data, filepath)."""
    if not RESULTS_DIR.exists():
        return None, None

    # Prefer summary.yml
    summary_yml = RESULTS_DIR / "summary.yml"
    if summary_yml.exists():
        return parse_yaml(summary_yml), summary_yml

    # Fall back to any .yml or .json file
    for pattern, parser in [("*.yml", parse_yaml), ("*.json", parse_json)]:
        for filepath in sorted(RESULTS_DIR.glob(pattern)):
            try:
                data = parser(filepath)
                if data:
                    return data, filepath
            except Exception as e:
                print(f"Warning: Failed to parse {filepath}: {e}")

    return None, None


def extract_results(data: dict) -> list:
    """Extract test results from parsed data into a list of dicts."""
    results = []

    # Handle different possible data structures
    if isinstance(data, dict):
        # Look for common keys that might contain test results
        for key in ("tests", "results", "detections"):
            if key in data and isinstance(data[key], list):
                for item in data[key]:
                    if isinstance(item, dict):
                        results.append({
                            "detection": item.get("name", item.get("detection", "Unknown")),
                            "status": item.get("status", item.get("result", "Unknown")),
                            "duration": item.get("duration", item.get("time", "N/A")),
                        })
                return results

        # If data itself looks like a flat result set
        if "name" in data or "detection" in data:
            results.append({
                "detection": data.get("name", data.get("detection", "Unknown")),
                "status": data.get("status", data.get("result", "Unknown")),
                "duration": data.get("duration", data.get("time", "N/A")),
            })

    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                results.append({
                    "detection": item.get("name", item.get("detection", "Unknown")),
                    "status": item.get("status", item.get("result", "Unknown")),
                    "duration": item.get("duration", item.get("time", "N/A")),
                })

    return results


def format_duration(duration) -> str:
    """Format duration value as a readable string."""
    if duration is None or duration == "N/A":
        return "N/A"
    if isinstance(duration, (int, float)):
        return f"{duration:.2f}s"
    return str(duration)


def write_summary(results: list, source_file: Path) -> None:
    """Write the formatted markdown summary."""
    if not SUMMARY_FILE:
        # Print to stdout if GITHUB_STEP_SUMMARY is not set
        output = sys.stdout
    else:
        output = open(SUMMARY_FILE, "a")

    try:
        total = len(results)
        passed = sum(1 for r in results if str(r["status"]).lower() in ("pass", "passed", "success"))
        failed = total - passed

        output.write("## Test Results\n\n")

        if total > 0:
            output.write("| Detection | Status | Duration |\n")
            output.write("|-----------|--------|----------|\n")
            for r in results:
                status = str(r["status"])
                icon = ":white_check_mark:" if status.lower() in ("pass", "passed", "success") else ":x:"
                output.write(f"| {r['detection']} | {icon} {status} | {format_duration(r['duration'])} |\n")

            output.write(f"\n**Total:** {total} | **Passed:** {passed} | **Failed:** {failed}\n")
        else:
            output.write("No individual test results found.\n")

        output.write(f"\n*Source: `{source_file}`*\n")
    finally:
        if output is not sys.stdout:
            output.close()


def main():
    data, source_file = find_result_file()

    if data is None:
        # No results found — write a graceful message
        if SUMMARY_FILE:
            with open(SUMMARY_FILE, "a") as f:
                f.write("## Test Results\n\n")
                f.write("No test result files found in `test_results/`.\n")
        else:
            print("No test result files found in test_results/")
        return

    results = extract_results(data)
    write_summary(results, source_file)
    print(f"Test summary written from {source_file} ({len(results)} results)")


if __name__ == "__main__":
    main()
