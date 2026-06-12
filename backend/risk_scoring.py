"""Explainable AIoT command risk scoring."""
from __future__ import annotations

from typing import Any


DEVICE_CRITICALITY = {
    "alarm": 90,
    "door_lock": 85,
    "camera": 80,
    "instrument": 75,
    "ac": 45,
    "fan": 35,
    "light": 25,
}

ROLE_RISK = {
    "visitor": 85,
    "student": 65,
    "teacher": 35,
    "admin": 10,
}

INPUT_RISK_LEVEL = {
    "low": 10,
    "medium": 55,
    "high": 90,
}


def _clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


def _level(score: float) -> str:
    if score >= 85:
        return "critical"
    if score >= 65:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def _component(name: str, score: float, reason: str) -> dict[str, Any]:
    return {"name": name, "score": round(_clamp(score), 2), "reason": reason}


def input_risk(input_guard_result: dict[str, Any] | None) -> dict[str, Any]:
    result = input_guard_result or {}
    level = result.get("risk_level", "low")
    score = INPUT_RISK_LEVEL.get(level, 10)
    prompt_score = float(result.get("prompt_injection_score") or 0)
    score = max(score, prompt_score * 100)
    if result.get("sensitive_operation"):
        score = max(score, 60)
    return _component("input_risk", score, f"input guard level={level}")


def device_criticality(device_type: str | None) -> dict[str, Any]:
    score = DEVICE_CRITICALITY.get(device_type or "unknown", 50)
    return _component("device_criticality", score, f"device_type={device_type or 'unknown'}")


def permission_risk(user_role: str | None, policy_result: dict[str, Any] | None) -> dict[str, Any]:
    policy = policy_result or {}
    if policy.get("decision") == "block":
        return _component("permission_risk", 95, policy.get("reason", "policy blocked"))
    role_score = ROLE_RISK.get(user_role or "unknown", 55)
    return _component("permission_risk", role_score, f"user_role={user_role or 'unknown'}")


def _range_for_param(device: Any, action: str, param_name: str) -> tuple[float, float] | None:
    if not device:
        return None
    if param_name in getattr(device, "attributes", {}):
        attr = device.attributes[param_name]
        if "range" in attr:
            return tuple(attr["range"])
    constraint = device.get_param_constraints(action, param_name)
    in_range = constraint.get("in_range") if constraint else None
    if in_range and in_range.startswith("attribute."):
        parts = in_range.split(".")
        if len(parts) >= 3:
            attr = device.attributes.get(parts[1], {})
            if "range" in attr:
                return tuple(attr["range"])
    return None


def parameter_risk(device_loader: Any, device_id: str | None, action: str | None, params: dict[str, Any] | None) -> dict[str, Any]:
    if not device_id or not action or not params:
        return _component("parameter_risk", 0, "no numeric parameters")
    device = device_loader.get_device(device_id)
    highest = 0.0
    reasons = []
    for param_name, raw_value in params.items():
        if not isinstance(raw_value, (int, float)):
            continue
        bounds = _range_for_param(device, action, param_name)
        if not bounds:
            continue
        low, high = bounds
        span = max(float(high) - float(low), 1.0)
        value = float(raw_value)
        if value < low:
            distance = (low - value) / span
            risk = 80 + min(distance * 20, 20)
            reasons.append(f"{param_name} below range [{low}, {high}]")
        elif value > high:
            distance = (value - high) / span
            risk = 80 + min(distance * 20, 20)
            reasons.append(f"{param_name} above range [{low}, {high}]")
        else:
            edge_distance = min(value - low, high - value) / span
            risk = 15 if edge_distance >= 0.1 else 35
            reasons.append(f"{param_name} within range [{low}, {high}]")
        highest = max(highest, risk)
    return _component("parameter_risk", highest, "; ".join(reasons) or "no bounded numeric parameters")


def physical_risk(physical_result: dict[str, Any] | None) -> dict[str, Any]:
    result = physical_result or {}
    decision = result.get("decision")
    reason = result.get("reason", "")
    if decision == "fail":
        if "互锁" in reason or "interlock" in reason.lower():
            return _component("physical_interlock_risk", 95, reason)
        if "速率" in reason or "rate" in reason.lower():
            return _component("physical_interlock_risk", 85, reason)
        return _component("physical_interlock_risk", 80, reason or "physical check failed")
    return _component("physical_interlock_risk", 10, reason or "physical check passed")


def model_consistency_risk(
    raw_actions: list[dict[str, Any]] | None,
    parsed_actions: list[dict[str, Any]] | None,
    fact_result: dict[str, Any] | None,
) -> dict[str, Any]:
    fact = fact_result or {}
    if fact.get("is_valid") is False:
        return _component("model_consistency_risk", 80, "; ".join(fact.get("reasons", [])) or "fact check failed")
    if raw_actions is not None and parsed_actions is not None and not raw_actions and parsed_actions:
        return _component("model_consistency_risk", 25, "local fallback used")
    if raw_actions and parsed_actions and len(raw_actions) != len(parsed_actions):
        return _component("model_consistency_risk", 45, "planner actions were filtered")
    return _component("model_consistency_risk", 10, "planner/fact checks consistent or unavailable")


def aggregate(components: list[dict[str, Any]]) -> dict[str, Any]:
    weights = {
        "input_risk": 0.22,
        "device_criticality": 0.16,
        "permission_risk": 0.22,
        "parameter_risk": 0.14,
        "physical_interlock_risk": 0.16,
        "model_consistency_risk": 0.10,
    }
    by_name = {component["name"]: component for component in components}
    weighted = sum(by_name[name]["score"] * weight for name, weight in weights.items() if name in by_name)
    strongest = max((component["score"] for component in components), default=0)
    # A single hard safety failure should remain visible instead of being averaged away.
    score = round(_clamp(max(weighted, strongest * 0.75 if strongest >= 80 else weighted)), 2)
    return {
        "score": score,
        "level": _level(score),
        "components": components,
        "top_factors": sorted(components, key=lambda item: item["score"], reverse=True)[:3],
    }


def score_action(
    *,
    user_role: str,
    input_guard_result: dict[str, Any],
    device_loader: Any,
    device_id: str | None = None,
    device_type: str | None = None,
    action: str | None = None,
    params: dict[str, Any] | None = None,
    policy_result: dict[str, Any] | None = None,
    physical_result: dict[str, Any] | None = None,
    fact_result: dict[str, Any] | None = None,
    raw_actions: list[dict[str, Any]] | None = None,
    parsed_actions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    components = [
        input_risk(input_guard_result),
        device_criticality(device_type),
        permission_risk(user_role, policy_result),
        parameter_risk(device_loader, device_id, action, params or {}),
        physical_risk(physical_result),
        model_consistency_risk(raw_actions, parsed_actions, fact_result),
    ]
    result = aggregate(components)
    result.update({
        "device_id": device_id or "",
        "device_type": device_type or "",
        "action": action or "",
    })
    return result


def score_overall(action_scores: list[dict[str, Any]], fallback_score: dict[str, Any] | None = None) -> dict[str, Any]:
    if action_scores:
        highest = max(action_scores, key=lambda item: item["score"])
        return {
            "score": highest["score"],
            "level": highest["level"],
            "strategy": "max_action_score",
            "action_count": len(action_scores),
            "top_factors": highest.get("top_factors", []),
            "actions": action_scores,
        }
    if fallback_score:
        return {
            "score": fallback_score["score"],
            "level": fallback_score["level"],
            "strategy": "fallback_no_action",
            "action_count": 0,
            "top_factors": fallback_score.get("top_factors", []),
            "actions": [],
        }
    empty = aggregate([
        _component("input_risk", 10, "no input risk available"),
        _component("device_criticality", 0, "no target device"),
        _component("permission_risk", 0, "no target action"),
        _component("parameter_risk", 0, "no parameters"),
        _component("physical_interlock_risk", 0, "not evaluated"),
        _component("model_consistency_risk", 30, "no action recognized"),
    ])
    return {
        "score": empty["score"],
        "level": empty["level"],
        "strategy": "empty",
        "action_count": 0,
        "top_factors": empty["top_factors"],
        "actions": [],
    }
