"""Simulated device protocol drivers for demo and audit evidence.

These drivers do not contact real hardware. They model the final gateway-to-
device hop so the safety pipeline can show what would be sent over MQTT or HTTP
after a command is approved.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class DriverResult:
    protocol: str
    endpoint: str
    method: str
    payload: dict[str, Any]
    status: str
    latency_ms: float
    simulated: bool = True
    ack: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BaseSimulatedDriver:
    protocol = "simulated"
    method = "execute"

    def send(
        self,
        device_id: str,
        device_type: str,
        action: str,
        params: dict[str, Any],
        new_state: dict[str, Any],
    ) -> DriverResult:
        started = time.perf_counter()
        payload = {
            "device_id": device_id,
            "device_type": device_type,
            "action": action,
            "params": params,
            "desired_state": new_state,
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        latency_ms = round((time.perf_counter() - started) * 1000, 3)
        return DriverResult(
            protocol=self.protocol,
            endpoint=self.endpoint(device_id, device_type),
            method=self.method,
            payload=payload,
            status="acked",
            latency_ms=latency_ms,
            ack={"bytes": len(encoded.encode("utf-8")), "message": "simulated_ack"},
        )

    def endpoint(self, device_id: str, device_type: str) -> str:
        raise NotImplementedError


class SimulatedMqttDriver(BaseSimulatedDriver):
    protocol = "mqtt"
    method = "publish"

    def endpoint(self, device_id: str, device_type: str) -> str:
        return f"aiot/{device_type}/{device_id}/command"


class SimulatedHttpDriver(BaseSimulatedDriver):
    protocol = "http"
    method = "POST"

    def endpoint(self, device_id: str, device_type: str) -> str:
        return f"http://simulated-device-bus.local/devices/{device_id}/actions"


class DeviceDriverManager:
    def __init__(self) -> None:
        self.mqtt_driver = SimulatedMqttDriver()
        self.http_driver = SimulatedHttpDriver()

    def choose_protocol(self, device_type: str) -> str:
        if device_type in {"alarm", "door_lock", "camera"}:
            return "http"
        return "mqtt"

    def send(
        self,
        device_id: str,
        device_type: str,
        action: str,
        params: dict[str, Any],
        new_state: dict[str, Any],
    ) -> dict[str, Any]:
        driver = self.http_driver if self.choose_protocol(device_type) == "http" else self.mqtt_driver
        return driver.send(device_id, device_type, action, params, new_state).to_dict()
