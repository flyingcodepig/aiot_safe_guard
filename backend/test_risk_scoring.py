"""Regression tests for explainable command risk scoring."""
from device_loader import DeviceCapabilityLoader
from risk_scoring import score_action, score_overall


def test_low_risk_light_command():
    loader = DeviceCapabilityLoader(device_dir="./data/devices")
    score = score_action(
        user_role="student",
        input_guard_result={"risk_level": "low", "prompt_injection_score": 0.0},
        device_loader=loader,
        device_id="light_a1",
        device_type="light",
        action="turn_on",
        params={},
        policy_result={"decision": "allow"},
        physical_result={"decision": "pass"},
        fact_result={"is_valid": True},
        raw_actions=[],
        parsed_actions=[{"device_id": "light_a1"}],
    )
    assert score["level"] in {"low", "medium"}
    assert score["score"] < 50


def test_blocked_door_unlock_is_high_risk():
    loader = DeviceCapabilityLoader(device_dir="./data/devices")
    score = score_action(
        user_role="student",
        input_guard_result={"risk_level": "low", "prompt_injection_score": 0.0},
        device_loader=loader,
        device_id="door_office",
        device_type="door_lock",
        action="unlock",
        params={},
        policy_result={"decision": "block", "reason": "student cannot unlock door"},
        physical_result={"decision": "pass"},
        fact_result={"is_valid": True},
    )
    assert score["level"] in {"high", "critical"}
    assert score["score"] >= 65


def test_out_of_range_parameter_raises_risk():
    loader = DeviceCapabilityLoader(device_dir="./data/devices")
    score = score_action(
        user_role="student",
        input_guard_result={"risk_level": "low", "prompt_injection_score": 0.0},
        device_loader=loader,
        device_id="fan_a1",
        device_type="fan",
        action="set_speed",
        params={"speed": 120},
        policy_result={"decision": "allow"},
        physical_result={"decision": "fail", "reason": "range violation"},
        fact_result={"is_valid": False, "reasons": ["speed out of range"]},
    )
    assert score["score"] >= 55
    assert any(c["name"] == "parameter_risk" and c["score"] >= 80 for c in score["components"])


def test_overall_uses_highest_action_score():
    low = {"score": 20, "level": "low", "top_factors": []}
    high = {"score": 88, "level": "critical", "top_factors": []}
    overall = score_overall([low, high])
    assert overall["score"] == 88
    assert overall["level"] == "critical"


if __name__ == "__main__":
    tests = [
        test_low_risk_light_command,
        test_blocked_door_unlock_is_high_risk,
        test_out_of_range_parameter_raises_risk,
        test_overall_uses_highest_action_score,
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
