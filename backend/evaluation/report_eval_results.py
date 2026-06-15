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


def percent_or_na(value: Any) -> str:
    if value is None:
        return "n/a"
    return percent(float(value))


def metric(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def suite_table(payload: dict[str, Any]) -> list[str]:
    lines = [
        "| Suite | Disabled Layers | Total | Passed | Failed | Pass Rate | Safety Correct | Safety Intervention | Attack Interception | False Positive | False Negative | Normal Pass | Avg Latency(ms) |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for suite in payload["suites"]:
        summary = suite["summary"]
        disabled = ", ".join(suite.get("disabled_layers", [])) or "none"
        lines.append(
            "| {suite} | {disabled} | {total} | {passed} | {failed} | {rate} | {safety_correct} | {intervention} | {attack} | {fp} | {fn} | {normal} | {latency} |".format(
                suite=suite["ablation"],
                disabled=disabled,
                total=summary["total"],
                passed=summary["passed"],
                failed=summary["failed"],
                rate=percent(summary["pass_rate"]),
                safety_correct=percent_or_na(summary.get("safety_correct_rate")),
                intervention=percent_or_na(summary.get("safety_intervention_rate")),
                attack=percent_or_na(summary.get("attack_interception_rate")),
                fp=percent_or_na(summary.get("false_positive_rate")),
                fn=percent_or_na(summary.get("false_negative_rate")),
                normal=percent_or_na(summary.get("normal_pass_rate")),
                latency=metric(summary.get("avg_latency_ms")),
            )
        )
    return lines


def category_table(suite: dict[str, Any]) -> list[str]:
    lines = [
        f"### {suite['ablation']}",
        "",
        "| Category | Total | Passed | Failed | Pass Rate | Attack Interception |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for category, stats in suite["summary"]["categories"].items():
        lines.append(
            "| {category} | {total} | {passed} | {failed} | {rate} | {attack} |".format(
                category=category,
                total=stats["total"],
                passed=stats["passed"],
                failed=stats["failed"],
                rate=percent(stats["pass_rate"]),
                attack="-" if category == "normal" else percent_or_na(stats.get("attack_interception_rate")),
            )
        )
    return lines


def threat_type_table(suite: dict[str, Any]) -> list[str]:
    threat_types = suite["summary"].get("threat_types", {})
    lines = [
        f"### {suite['ablation']}",
        "",
    ]
    if not threat_types:
        lines.append("No threat-type breakdown available.")
        return lines

    lines.extend([
        "| Threat Type | Total | Passed | Failed | Pass Rate | Attack Interception |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ])
    for threat_type, stats in threat_types.items():
        lines.append(
            "| {threat_type} | {total} | {passed} | {failed} | {rate} | {attack} |".format(
                threat_type=threat_type,
                total=stats["total"],
                passed=stats["passed"],
                failed=stats["failed"],
                rate=percent(stats["pass_rate"]),
                attack=percent_or_na(stats.get("attack_interception_rate")),
            )
        )
    return lines


def module_timing_table(payload: dict[str, Any]) -> list[str]:
    timing_names = sorted({
        name
        for suite in payload["suites"]
        for name in suite["summary"].get("avg_module_timings_ms", {})
    })
    if not timing_names:
        return ["No module timing data available."]

    lines = [
        "| Suite | " + " | ".join(timing_names) + " |",
        "| --- | " + " | ".join("---:" for _ in timing_names) + " |",
    ]
    for suite in payload["suites"]:
        timings = suite["summary"].get("avg_module_timings_ms", {})
        cells = [metric(timings.get(name)) for name in timing_names]
        lines.append("| {suite} | {cells} |".format(
            suite=suite["ablation"],
            cells=" | ".join(cells),
        ))
    return lines


def high_risk_cases(suite: dict[str, Any], limit: int) -> list[str]:
    rows = []
    for case in suite.get("results", []):
        response = case.get("response") or {}
        risk = response.get("risk_result") or {}
        if case.get("expected") in {"block", "require_confirm"} and case.get("actual") in {"block", "require_confirm"}:
            rows.append((risk.get("score", 0), case, risk))
    rows.sort(reverse=True, key=lambda item: item[0])

    lines = [f"### {suite['ablation']}", ""]
    if not rows:
        lines.append("No high-risk blocked cases.")
        return lines

    lines.extend([
        "| Case | Category | Threat Type | Decision | Risk | Top Factors |",
        "| --- | --- | --- | --- | ---: | --- |",
    ])
    for _, case, risk in rows[:limit]:
        factors = "; ".join(
            f"{item.get('name')}={item.get('score')}" for item in risk.get("top_factors", [])
        )
        lines.append(
            f"| {case['id']} | {case['category']} | {case.get('threat_type', '-')} | {case['actual']} | {metric(risk.get('score'))} | {factors or '-'} |"
        )
    if len(rows) > limit:
        lines.append(f"| ... | ... | ... | ... | {len(rows) - limit} more |")
    return lines


def failed_cases(suite: dict[str, Any], limit: int) -> list[str]:
    failed = [case for case in suite.get("results", []) if not case.get("passed")]
    lines = [f"### {suite['ablation']}", ""]
    if not failed:
        lines.append("No failed cases.")
        return lines

    lines.extend([
        "| Case | Category | Threat Type | Expected | Actual | Safety Correct |",
        "| --- | --- | --- | --- | --- | --- |",
    ])
    for case in failed[:limit]:
        lines.append(
            f"| {case['id']} | {case['category']} | {case.get('threat_type', '-')} | {case['expected']} | {case['actual']} | {case.get('safety_correct', False)} |"
        )
    if len(failed) > limit:
        lines.append(f"| ... | ... | ... | {len(failed) - limit} more |")
    return lines


def decision_mismatch_table(payload: dict[str, Any]) -> list[str]:
    """Render decision-mismatch breakdown across suites."""
    lines = [
        "| Suite | Mismatch | Count |",
        "| --- | --- | ---: |",
    ]
    has_any = False
    for suite in payload["suites"]:
        mismatches = suite.get("decision_mismatches") or suite["summary"].get("decision_mismatches", {})
        if mismatches:
            has_any = True
            for key, count in sorted(mismatches.items()):
                lines.append(f"| {suite['ablation']} | {key} | {count} |")
        else:
            lines.append(f"| {suite['ablation']} | (none) | 0 |")
    if not has_any:
        return ["No decision mismatches across any suite."]
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

    lines.extend(["## Threat Type Breakdown", ""])
    for suite in payload["suites"]:
        lines.extend(threat_type_table(suite))
        lines.append("")

    lines.extend(["## Module Timing", ""])
    lines.extend(module_timing_table(payload))
    lines.append("")

    lines.extend(["## Failed Cases", ""])
    for suite in payload["suites"]:
        lines.extend(failed_cases(suite, failure_limit))
        lines.append("")

    lines.extend(["## Decision Mismatch Breakdown", ""])
    lines.append(
        "Safety-correct mismatches (`block` ↔ `require_confirm`) are safe "
        "interventions where the system chose a different valid response than "
        "the expected label. Unsafe mismatches (`*_to_allow` and `allow_to_*`) "
        "are false negatives or false positives."
    )
    lines.append("")
    lines.extend(decision_mismatch_table(payload))
    lines.append("")

    lines.extend(["## High-Risk Blocked Cases", ""])
    for suite in payload["suites"]:
        lines.extend(high_risk_cases(suite, failure_limit))
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
