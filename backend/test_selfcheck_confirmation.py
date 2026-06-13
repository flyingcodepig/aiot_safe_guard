"""Regression test for SelfCheck/manual confirmation gate evidence."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("ENABLE_LLM_PLANNER", "false")
os.environ.setdefault("ENABLE_LLM_FACT_CHECKS", "false")
os.environ.setdefault("ENABLE_LLM_GUARD_SCANNER", "false")
os.environ.setdefault("ENABLE_SELFCHECK_GATE", "true")
os.environ.setdefault("SELFCHECK_ENABLED", "false")
os.environ["API_KEY"] = ""
os.environ["DATABASE_URL"] = "sqlite:///./aiot_guard_selfcheck_test.db"

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402


DB_FILE = Path("aiot_guard_selfcheck_test.db")


def cleanup_db() -> None:
    for path in [DB_FILE, DB_FILE.with_suffix(".db-wal"), DB_FILE.with_suffix(".db-shm")]:
        if path.exists():
            path.unlink()


def test_manual_confirmation_gate_is_ablatable() -> None:
    cleanup_db()
    with TestClient(main.app) as client:
        response = client.post(
            "/api/smart_command",
            json={"user_id": "u003", "user_input": "人工确认后打开办公室摄像头"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["overall_decision"] == "require_confirm"
        assert body["require_confirmation"] is True
        token = body["confirmation_token"]
        assert token
        assert body["parsed_actions"][0]["device_id"] == "camera_01"

        confirmed = client.post(f"/api/confirm/{token}", json={"confirm": True})
        assert confirmed.status_code == 200
        confirmed_body = confirmed.json()
        assert confirmed_body["overall_decision"] == "allow"
        assert confirmed_body["require_confirmation"] is False
        assert confirmed_body["action_results"][0]["transport_result"]["protocol"] == "http"

        ablated = client.post(
            "/api/smart_command",
            headers={"X-Ablation-Disable": "selfcheck"},
            json={"user_id": "u003", "user_input": "人工确认后打开办公室摄像头"},
        )
        assert ablated.status_code == 200
        ablated_body = ablated.json()
        assert ablated_body["overall_decision"] == "allow"
        assert ablated_body["require_confirmation"] is False
        assert ablated_body["action_results"][0]["transport_result"]["protocol"] == "http"
    cleanup_db()


if __name__ == "__main__":
    try:
        test_manual_confirmation_gate_is_ablatable()
        print("PASS: test_manual_confirmation_gate_is_ablatable")
        print("\nALL TESTS PASSED")
    except AssertionError as exc:
        print(f"FAIL: test_manual_confirmation_gate_is_ablatable - {exc}")
        raise SystemExit(1)
