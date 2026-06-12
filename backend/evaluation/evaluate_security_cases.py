"""Run and summarize AIoT safety evaluation cases.

Usage:
  python evaluation/evaluate_security_cases.py
  python evaluation/evaluate_security_cases.py --base-url http://127.0.0.1:8000 --api-key YOUR_KEY
  python evaluation/evaluate_security_cases.py --base-url http://127.0.0.1:8000 --output results/full.json
  python evaluation/evaluate_security_cases.py --base-url http://127.0.0.1:8000 --ablation full no_policy_engine

The script is intentionally lightweight: without --base-url it prints dataset
coverage; with --base-url it executes cases against the running FastAPI app and
emits overall/category pass rates that can be reused for ablation tables.
"""
from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import httpx


DEFAULT_CASES = Path(__file__).with_name("security_cases_core.json")

ABLATION_PROFILES = {
    "full": [],
    "baseline_llm_direct": [
        "input_guard",
        "device_gate",
        "intent_gate",
        "fact_checker",
        "policy_engine",
        "physical_checker",
        "selfcheck",
    ],
    "baseline_rbac_only": [
        "input_guard",
        "device_gate",
        "intent_gate",
        "fact_checker",
        "physical_checker",
        "selfcheck",
    ],
    "baseline_keyword_only": [
        "input_guard",
        "intent_gate",
        "fact_checker",
        "policy_engine",
        "physical_checker",
        "selfcheck",
    ],
    "baseline_no_physical_rules": ["physical_checker"],
    "no_input_guard": ["input_guard"],
    "no_device_gate": ["device_gate"],
    "no_intent_gate": ["intent_gate"],
    "no_fact_checker": ["fact_checker"],
    "no_policy_engine": ["policy_engine"],
    "no_physical_checker": ["physical_checker"],
    "no_selfcheck": ["selfcheck"],
}


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


def post_json(client: httpx.Client, path: str, payload: dict[str, Any], timeout: float | None = None) -> dict[str, Any]:
    resp = client.post(path, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def failed_case(case: dict[str, Any], error: str) -> dict[str, Any]:
    return {
        "id": case["id"],
        "category": case.get("category", "uncategorized"),
        "expected": case["expected_decision"],
        "actual": "error",
        "passed": False,
        "observed_decisions": ["error"],
        "error": error,
        "latency_ms": None,
        "module_timings_ms": {},
        "response": None,
    }


def run_case(client: httpx.Client, case: dict[str, Any], request_timeout: float) -> dict[str, Any]:
    try:
        for setup in case.get("setup", []):
            post_json(
                client,
                f"/api/device/{setup['device_id']}/set_state",
                {"key": setup["key"], "value": str(setup["value"])},
                timeout=request_timeout,
            )

        repeat = int(case.get("repeat", 1))
        responses = []
        latencies = []
        for _ in range(max(1, repeat)):
            started = time.perf_counter()
            response = post_json(
                client,
                "/api/smart_command",
                {"user_id": case["user_id"], "user_input": case["user_input"]},
                timeout=request_timeout,
            )
            latencies.append((time.perf_counter() - started) * 1000)
            responses.append(response)
    except Exception as exc:  # noqa: BLE001 - record per-case evaluation failure
        return failed_case(case, str(exc))

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
        "latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
        "module_timings_ms": responses[-1].get("timings_ms", {}) if responses else {},
        "response": responses[-1] if responses else None,
    }


def make_headers(api_key: str = "", disabled_layers: list[str] | None = None) -> dict[str, str]:
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
    if disabled_layers:
        headers["X-Ablation-Disable"] = ",".join(disabled_layers)
    return headers


def resolve_ablation(name_or_layers: str) -> tuple[str, list[str]]:
    if name_or_layers in ABLATION_PROFILES:
        return name_or_layers, ABLATION_PROFILES[name_or_layers]
    layers = [part.strip() for part in name_or_layers.split(",") if part.strip()]
    if not layers:
        raise ValueError(f"empty ablation profile: {name_or_layers}")
    return name_or_layers, layers


def run_suite(
    base_url: str,
    api_key: str,
    cases: list[dict[str, Any]],
    ablation_name: str,
    disabled_layers: list[str],
    reset_before: bool,
    request_timeout: float,
) -> dict[str, Any]:
    headers = make_headers(api_key=api_key, disabled_layers=disabled_layers)
    with httpx.Client(base_url=base_url.rstrip("/"), headers=headers, timeout=request_timeout) as client:
        if reset_before:
            resp = client.post("/api/reset", timeout=request_timeout)
            resp.raise_for_status()
        results = [run_case(client, case, request_timeout) for case in cases]

    return {
        "ablation": ablation_name,
        "disabled_layers": disabled_layers,
        "summary": summarize_results(results),
        "results": results,
    }


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    category_totals: dict[str, int] = defaultdict(int)
    category_passed: dict[str, int] = defaultdict(int)
    category_blocked_attacks: dict[str, int] = defaultdict(int)
    category_attack_totals: dict[str, int] = defaultdict(int)
    for result in results:
        category = result["category"]
        category_totals[category] += 1
        if result["passed"]:
            category_passed[category] += 1
        if category != "normal":
            category_attack_totals[category] += 1
            if result["actual"] == "block":
                category_blocked_attacks[category] += 1

    categories = {}
    for category, total in sorted(category_totals.items()):
        passed = category_passed[category]
        stats = {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / total, 4) if total else 0.0,
        }
        if category != "normal":
            blocked = category_blocked_attacks[category]
            attack_total = category_attack_totals[category]
            stats["attack_interception_rate"] = round(blocked / attack_total, 4) if attack_total else 0.0
        categories[category] = stats

    passed_total = sum(1 for r in results if r["passed"])
    total = len(results)
    normal = [r for r in results if r["category"] == "normal"]
    attacks = [r for r in results if r["category"] != "normal"]
    false_positive = [r for r in normal if r["actual"] == "block"]
    false_negative = [r for r in attacks if r["actual"] == "allow"]
    blocked = [r for r in results if r["actual"] == "block"]
    latencies = [r["latency_ms"] for r in results if isinstance(r.get("latency_ms"), (int, float))]
    return {
        "total": total,
        "passed": passed_total,
        "failed": total - passed_total,
        "pass_rate": round(passed_total / total, 4) if total else 0.0,
        "block_rate": round(len(blocked) / total, 4) if total else 0.0,
        "normal_pass_rate": round(sum(1 for r in normal if r["actual"] == "allow") / len(normal), 4) if normal else 0.0,
        "attack_interception_rate": round(sum(1 for r in attacks if r["actual"] == "block") / len(attacks), 4) if attacks else 0.0,
        "false_positive_rate": round(len(false_positive) / len(normal), 4) if normal else 0.0,
        "false_negative_rate": round(len(false_negative) / len(attacks), 4) if attacks else 0.0,
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
        "module_timing_available": any(r.get("module_timings_ms") for r in results),
        "categories": categories,
    }


def summarize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_file": payload["case_file"],
        "base_url": payload["base_url"],
        "suites": [
            {
                "ablation": suite["ablation"],
                "disabled_layers": suite["disabled_layers"],
                "summary": suite["summary"],
            }
            for suite in payload["suites"]
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--base-url", help="Running backend URL, e.g. http://127.0.0.1:8000")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--ablation",
        nargs="*",
        default=["full"],
        help="Ablation profile names or comma-separated layer lists. Known: "
        + ", ".join(ABLATION_PROFILES),
    )
    parser.add_argument("--no-reset-before", action="store_true")
    parser.add_argument("--request-timeout", type=float, default=10.0)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    cases = load_cases(args.cases)
    if not args.base_url:
        print(json.dumps(summarize_cases(cases), ensure_ascii=False, indent=2))
        print("Pass --base-url to execute these cases against a running backend.")
        return 0

    suites = []
    for profile in args.ablation:
        name, disabled_layers = resolve_ablation(profile)
        suites.append(
            run_suite(
                base_url=args.base_url,
                api_key=args.api_key,
                cases=cases,
                ablation_name=name,
                disabled_layers=disabled_layers,
                reset_before=not args.no_reset_before,
                request_timeout=args.request_timeout,
            )
        )

    payload = {
        "case_file": str(args.cases),
        "base_url": args.base_url,
        "suites": suites,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    if args.summary_only:
        print(json.dumps(summarize_payload(payload), ensure_ascii=False, indent=2))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
