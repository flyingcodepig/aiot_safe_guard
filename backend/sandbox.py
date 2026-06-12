"""Simulation sandbox for approved AIoT device actions.

The sandbox owns virtual device state and calls a simulated protocol driver for
the final gateway-to-device hop. It does not contact real hardware.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Tuple

from database import get_connection
from device_driver import DeviceDriverManager
from device_loader import DeviceCapabilityLoader


FIXED_ACTION_STATE: Dict[str, Dict[str, Any]] = {
    "turn_on": {"power": True},
    "turn_off": {"power": False},
    "unlock": {"status": "unlocked"},
    "lock": {"status": "locked"},
    "silence": {"status": "normal"},
    "start_recording": {"recording": True},
    "stop_recording": {"recording": False},
    "read": {},
}


class SandboxEngine:
    def __init__(self, device_loader: DeviceCapabilityLoader):
        self.device_loader = device_loader
        self.driver_manager = DeviceDriverManager()

    def get_device_state(self, device_id: str) -> Dict[str, Any]:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT key, value FROM device_states WHERE device_id = ?", (device_id,))
        state = {}
        for row in c.fetchall():
            state[row["key"]] = self._parse_value(row["value"])
        conn.close()

        if not state:
            device = self.device_loader.get_device(device_id)
            if device:
                for attr_name, attr_cfg in device.attributes.items():
                    state[attr_name] = attr_cfg.get("default")
        return state

    def initialize_device_state(self, device_id: str) -> None:
        device = self.device_loader.get_device(device_id)
        if not device:
            return
        conn = get_connection()
        c = conn.cursor()
        for attr_name, attr_cfg in device.attributes.items():
            default_val = attr_cfg.get("default")
            c.execute(
                "INSERT OR REPLACE INTO device_states (device_id, key, value, updated_at) VALUES (?, ?, ?, ?)",
                (device_id, attr_name, str(default_val), datetime.now().isoformat()),
            )
        conn.commit()
        conn.close()

    def execute(self, device_id: str, action: str, params: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any], Dict[str, Any]]:
        if not self.device_loader.device_exists(device_id):
            return False, f"device {device_id} does not exist", {}, {}

        device = self.device_loader.get_device(device_id)
        if not device.supports_action(action):
            return False, f"device {device_id} does not support action {action}", {}, {}

        current_state = self.get_device_state(device_id)
        if not current_state:
            self.initialize_device_state(device_id)
            current_state = self.get_device_state(device_id)

        new_state = current_state.copy()
        if action in FIXED_ACTION_STATE:
            new_state.update(FIXED_ACTION_STATE[action])
        else:
            self._apply_params(device, new_state, params)

        conn = get_connection()
        c = conn.cursor()
        for key, value in new_state.items():
            c.execute(
                "INSERT OR REPLACE INTO device_states (device_id, key, value, updated_at) VALUES (?, ?, ?, ?)",
                (device_id, key, str(value), datetime.now().isoformat()),
            )
        conn.commit()
        conn.close()

        transport_result = self.driver_manager.send(
            device_id=device_id,
            device_type=device.type,
            action=action,
            params=params,
            new_state=new_state,
        )
        return True, f"device {device_id} executed {action}", new_state, transport_result

    def _apply_params(self, device: Any, new_state: Dict[str, Any], params: Dict[str, Any]) -> None:
        for param_name, param_value in params.items():
            if param_name in device.attributes:
                new_state[param_name] = param_value
                continue

            alias_map = {"value": "temperature", "speed": "speed"}
            if param_name in alias_map and alias_map[param_name] in device.attributes:
                new_state[alias_map[param_name]] = param_value
                continue

            if isinstance(param_value, (int, float)):
                for attr_name, attr_cfg in device.attributes.items():
                    if attr_cfg.get("type") in ("int", "float") and attr_name not in new_state:
                        new_state[attr_name] = param_value
                        break

    @staticmethod
    def _parse_value(value_str: str) -> Any:
        if value_str is None:
            return None
        if value_str.lower() == "true":
            return True
        if value_str.lower() == "false":
            return False
        try:
            return int(value_str)
        except (ValueError, TypeError):
            try:
                return float(value_str)
            except (ValueError, TypeError):
                return value_str
