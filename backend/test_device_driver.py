"""Regression tests for simulated MQTT/HTTP device drivers."""
from device_driver import DeviceDriverManager
from device_loader import DeviceCapabilityLoader
from sandbox import SandboxEngine


def test_driver_protocol_selection():
    manager = DeviceDriverManager()
    assert manager.choose_protocol("light") == "mqtt"
    assert manager.choose_protocol("fan") == "mqtt"
    assert manager.choose_protocol("door_lock") == "http"
    assert manager.choose_protocol("alarm") == "http"


def test_sandbox_execute_returns_mqtt_transport():
    loader = DeviceCapabilityLoader(device_dir="./data/devices")
    sandbox = SandboxEngine(loader)
    success, _message, new_state, transport = sandbox.execute("light_a1", "turn_on", {})
    assert success
    assert new_state["power"] is True
    assert transport["protocol"] == "mqtt"
    assert transport["method"] == "publish"
    assert transport["endpoint"] == "aiot/light/light_a1/command"
    assert transport["payload"]["action"] == "turn_on"
    assert transport["status"] == "acked"


def test_sandbox_execute_returns_http_transport():
    loader = DeviceCapabilityLoader(device_dir="./data/devices")
    sandbox = SandboxEngine(loader)
    success, _message, new_state, transport = sandbox.execute("door_office", "lock", {})
    assert success
    assert new_state["status"] == "locked"
    assert transport["protocol"] == "http"
    assert transport["method"] == "POST"
    assert transport["endpoint"].endswith("/devices/door_office/actions")
    assert transport["payload"]["action"] == "lock"
    assert transport["status"] == "acked"


if __name__ == "__main__":
    tests = [
        test_driver_protocol_selection,
        test_sandbox_execute_returns_mqtt_transport,
        test_sandbox_execute_returns_http_transport,
    ]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"PASS: {test.__name__}")
        except AssertionError as exc:
            print(f"FAIL: {test.__name__} - {exc}")
            failed += 1
    print(f"\n{failed} test(s) failed" if failed else "\nALL TESTS PASSED")
