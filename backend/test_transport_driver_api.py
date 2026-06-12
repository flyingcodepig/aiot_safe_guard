"""API regression test for simulated protocol transport evidence."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("ENABLE_LLM_PLANNER", "false")
os.environ.setdefault("ENABLE_LLM_FACT_CHECKS", "false")
os.environ.setdefault("ENABLE_LLM_GUARD_SCANNER", "false")
os.environ.setdefault("ENABLE_SELFCHECK_GATE", "false")
os.environ.setdefault("SELFCHECK_ENABLED", "false")
os.environ["API_KEY"] = ""
os.environ["DATABASE_URL"] = "sqlite:///./aiot_guard_transport_test.db"

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402


DB_FILE = Path("aiot_guard_transport_test.db")


def cleanup_db() -> None:
    for path in [DB_FILE, DB_FILE.with_suffix(".db-wal"), DB_FILE.with_suffix(".db-shm")]:
        if path.exists():
            path.unlink()


def test_smart_command_exposes_transport_result():
    cleanup_db()
    with TestClient(main.app) as client:
        response = client.post(
            "/api/smart_command",
            json={"user_id": "u001", "user_input": "打开风扇"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["overall_decision"] == "allow"
        assert body["action_results"]

        transport = body["action_results"][0]["transport_result"]
        assert transport["protocol"] == "mqtt"
        assert transport["method"] == "publish"
        assert transport["status"] == "acked"
        assert transport["payload"]["device_id"] == "fan_a1"

        logs = client.get("/api/logs").json()
        assert logs
        assert "transport_result" in logs[0]
        assert "mqtt" in logs[0]["transport_result"]

        exported_json = client.get("/api/logs/export?format=json").json()
        assert "transport_result" in exported_json[0]

        exported_csv = client.get("/api/logs/export?format=csv").text
        assert "transport_result" in exported_csv.splitlines()[0]
    cleanup_db()


if __name__ == "__main__":
    try:
        test_smart_command_exposes_transport_result()
        print("PASS: test_smart_command_exposes_transport_result")
        print("\nALL TESTS PASSED")
    except AssertionError as exc:
        print(f"FAIL: test_smart_command_exposes_transport_result - {exc}")
        raise SystemExit(1)
