"""Render evaluation JSON results as Markdown tables."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_INPUT = Path(__file__).with_name("results") / "latest_eval.json"
DEFAULT_OUTPUT = Path(__file__).with_name("results") / "latest_eval.md"


def load_payload(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def suite_table(payload: dict[str, Any]) -> list[str]:
    lines = [
        "| Suite | Disabled Layers | Total | Passed | Failed | Pass Rate |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for suite in payload["suites"]:
        summary = suite["summary"]
        disabled = ", ".join(suite.get("disabled_layers", [])) or "none"
        lines.append(
            "| {suite} | {disabled} | {total} | {passed} | {failed} | {rate} |".format(
                suite=suite["ablation"],
                disabled=disabled,
                total=summary["total"],
                passed=summary["passed"],
                failed=summary["failed"],
                rate=percent(summary["pass_rate"]),
            )
        )
    return lines


def category_table(suite: dict[str, Any]) -> list[str]:
    lines = [
        f"### {suite['ablation']}",
        "",
        "| Category | Total | Passed | Failed | Pass Rate |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for category, stats in suite["summary"]["categories"].items():
        lines.append(
            "| {category} | {total} | {passed} | {failed} | {rate} |".format(
                category=category,
                total=stats["total"],
                passed=stats["passed"],
                failed=stats["failed"],
                rate=percent(stats["pass_rate"]),
            )
        )
    return lines


def failed_cases(suite: dict[str, Any], limit: int) -> list[str]:
    failed = [case for case in suite.get("results", []) if not case.get("passed")]
    lines = [f"### {suite['ablation']}", ""]
    if not failed:
        lines.append("No failed cases.")
        return lines

    lines.extend([
        "| Case | Category | Expected | Actual |",
        "| --- | --- | --- | --- |",
    ])
    for case in failed[:limit]:
        lines.append(
            f"| {case['id']} | {case['category']} | {case['expected']} | {case['actual']} |"
        )
    if len(failed) > limit:
        lines.append(f"| ... | ... | ... | {len(failed) - limit} more |")
    return lines


def render_markdown(payload: dict[str, Any], failure_limit: int) -> str:
    lines = [
        "# AIoT Safe Guard Evaluation Summary",
        "",
        f"- Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"- Case file: `{payload['case_file']}`",
        f"- Base URL: `{payload['base_url']}`",
        "",
        "## Suite Summary",
        "",
        *suite_table(payload),
        "",
        "## Category Breakdown",
        "",
    ]
    for suite in payload["suites"]:
        lines.extend(category_table(suite))
        lines.append("")

    lines.extend(["## Failed Cases", ""])
    for suite in payload["suites"]:
        lines.extend(failed_cases(suite, failure_limit))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--failure-limit", type=int, default=20)
    args = parser.parse_args()

    payload = load_payload(args.input)
    text = render_markdown(payload, args.failure_limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
