"""Run and summarize AIoT safety evaluation cases.

Usage:
  python evaluation/evaluate_security_cases.py
  python evaluation/evaluate_security_cases.py --base-url http://127.0.0.1:8000 --api-key YOUR_KEY
  python evaluation/evaluate_security_cases.py --base-url http://127.0.0.1:8000 --output results/full.json

The script is intentionally lightweight: without --base-url it prints dataset
coverage; with --base-url it executes cases against the running FastAPI app and
emits overall/category pass rates that can be reused for ablation tables.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import httpx


DEFAULT_CASES = Path(__file__).with_name("security_cases_core.json")


def load_cases(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("case file must be a JSON array")
    return data


def summarize_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    by_category: dict[str, int] = defaultdict(int)
    for case in cases:
        by_category[case.get("category", "uncategorized")] += 1
    return {
        "total": len(cases),
        "categories": dict(sorted(by_category.items())),
    }


def post_json(client: httpx.Client, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    resp = client.post(path, json=payload)
    resp.raise_for_status()
    return resp.json()


def run_case(client: httpx.Client, case: dict[str, Any]) -> dict[str, Any]:
    for setup in case.get("setup", []):
        post_json(
            client,
            f"/api/device/{setup['device_id']}/set_state",
            {"key": setup["key"], "value": str(setup["value"])},
        )

    repeat = int(case.get("repeat", 1))
    responses = []
    for _ in range(max(1, repeat)):
        responses.append(
            post_json(
                client,
                "/api/smart_command",
                {"user_id": case["user_id"], "user_input": case["user_input"]},
            )
        )

    expected = case["expected_decision"]
    actual = responses[-1].get("overall_decision", "error") if responses else "error"
    passed = actual == expected
    return {
        "id": case["id"],
        "category": case.get("category", "uncategorized"),
        "expected": expected,
        "actual": actual,
        "passed": passed,
        "observed_decisions": [r.get("overall_decision", "error") for r in responses],
        "response": responses[-1] if responses else None,
    }


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    category_totals: dict[str, int] = defaultdict(int)
    category_passed: dict[str, int] = defaultdict(int)
    for result in results:
        category = result["category"]
        category_totals[category] += 1
        if result["passed"]:
            category_passed[category] += 1

    categories = {}
    for category, total in sorted(category_totals.items()):
        passed = category_passed[category]
        categories[category] = {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / total, 4) if total else 0.0,
        }

    passed_total = sum(1 for r in results if r["passed"])
    total = len(results)
    return {
        "total": total,
        "passed": passed_total,
        "failed": total - passed_total,
        "pass_rate": round(passed_total / total, 4) if total else 0.0,
        "categories": categories,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--base-url", help="Running backend URL, e.g. http://127.0.0.1:8000")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    cases = load_cases(args.cases)
    if not args.base_url:
        print(json.dumps(summarize_cases(cases), ensure_ascii=False, indent=2))
        print("Pass --base-url to execute these cases against a running backend.")
        return 0

    headers = {"X-API-Key": args.api_key} if args.api_key else {}
    with httpx.Client(base_url=args.base_url.rstrip("/"), headers=headers, timeout=60.0) as client:
        results = [run_case(client, case) for case in cases]

    payload = {
        "case_file": str(args.cases),
        "base_url": args.base_url,
        "summary": summarize_results(results),
        "results": results,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
