"""Start an offline evaluation backend, run safety cases, then stop it.

This wrapper avoids manual terminal/process management during competition
preparation. It starts uvicorn with offline-friendly defaults, waits for
`/health`, runs `evaluate_security_cases.py`, and always terminates the server.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx


EVAL_DIR = Path(__file__).resolve().parent
BACKEND_DIR = EVAL_DIR.parent
RESULTS_DIR = EVAL_DIR / "results"


def load_dotenv_value(path: Path, key: str) -> str:
    if not path.exists():
        return ""
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == key:
            return value.strip().strip('"').strip("'")
    return ""


def wait_for_health(base_url: str, timeout_seconds: int) -> dict:
    deadline = time.time() + timeout_seconds
    last_error = None
    while time.time() < deadline:
        try:
            resp = httpx.get(f"{base_url}/health", timeout=2.0, trust_env=False)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001 - report last startup error
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"backend did not become healthy: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--wait-seconds", type=int, default=90)
    parser.add_argument("--request-timeout", type=float, default=10.0)
    parser.add_argument("--cases", type=Path, default=EVAL_DIR / "security_cases_core.json")
    parser.add_argument("--output", type=Path, default=RESULTS_DIR / "latest_eval.json")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--print-full-json", action="store_true")
    parser.add_argument(
        "--reset-each-case",
        action="store_true",
        help="Reset backend state before each case. Recommended for randomized formal split files.",
    )
    parser.add_argument(
        "--ablation",
        nargs="*",
        default=[
            "full",
            "baseline_llm_direct",
            "baseline_rbac_only",
            "baseline_keyword_only",
            "baseline_no_physical_rules",
            "no_input_guard",
            "no_device_gate",
            "no_fact_checker",
            "no_policy_engine",
            "no_physical_checker",
            "no_selfcheck",
        ],
    )
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    server_log = RESULTS_DIR / "server_eval.combined.log"
    env = os.environ.copy()
    env.update(
        {
            "OPENAI_API_KEY": env.get("OPENAI_API_KEY", "dummy-for-offline-eval"),
            "LLM_BASE_URL": env.get("LLM_BASE_URL", "http://127.0.0.1:9"),
            "LLM_MODEL": env.get("LLM_MODEL", "offline-eval"),
            "SELFCHECK_ENABLED": env.get("SELFCHECK_ENABLED", "false"),
            "ENABLE_LLM_GUARD_SCANNER": env.get("ENABLE_LLM_GUARD_SCANNER", "false"),
            "ENABLE_LLM_PLANNER": env.get("ENABLE_LLM_PLANNER", "false"),
            "ENABLE_LLM_FACT_CHECKS": env.get("ENABLE_LLM_FACT_CHECKS", "false"),
            "LLM_TIMEOUT_SECONDS": env.get("LLM_TIMEOUT_SECONDS", "0.5"),
            "LLM_MAX_RETRIES": env.get("LLM_MAX_RETRIES", "0"),
            "DATABASE_URL": env.get("DATABASE_URL", "sqlite:///./evaluation/results/eval_aiot_guard.db"),
            "DEVICE_CONFIG_DIR": env.get("DEVICE_CONFIG_DIR", "./data/devices"),
        }
    )

    base_url = f"http://{args.host}:{args.port}"
    api_key = args.api_key or os.environ.get("API_KEY", "") or load_dotenv_value(BACKEND_DIR / ".env", "API_KEY")
    with server_log.open("w", encoding="utf-8") as log:
        server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "main:app",
                "--host",
                args.host,
                "--port",
                str(args.port),
            ],
            cwd=BACKEND_DIR,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )

        try:
            health = wait_for_health(base_url, args.wait_seconds)
            print(f"backend healthy: {health}")

            cmd = [
                sys.executable,
                str(EVAL_DIR / "evaluate_security_cases.py"),
                "--cases",
                str(args.cases),
                "--base-url",
                base_url,
                "--output",
                str(args.output),
                "--api-key",
                api_key,
                "--request-timeout",
                str(args.request_timeout),
                "--ablation",
                *args.ablation,
            ]
            if not args.print_full_json:
                cmd.append("--summary-only")
            if args.reset_each_case:
                cmd.append("--reset-each-case")
            result = subprocess.run(cmd, cwd=BACKEND_DIR, text=True)
            return result.returncode
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=10)


if __name__ == "__main__":
    raise SystemExit(main())
