"""仿真沙箱引擎 - 在虚拟设备状态机上执行动作（数据驱动）"""
from typing import Dict, Any, Tuple
from datetime import datetime

from database import get_connection
from device_loader import DeviceCapabilityLoader

# 简单动作的状态映射（无参数动作 → 固定状态变更）
FIXED_ACTION_STATE: Dict[str, Dict[str, Any]] = {
    "turn_on":         {"power": True},
    "turn_off":        {"power": False},
    "unlock":          {"status": "unlocked"},
    "lock":            {"status": "locked"},
    "silence":         {"status": "normal"},
    "start_recording": {"recording": True},
    "stop_recording":  {"recording": False},
    "read":            {},
}


class SandboxEngine:
    def __init__(self, device_loader: DeviceCapabilityLoader):
        self.device_loader = device_loader

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

    def initialize_device_state(self, device_id: str):
        device = self.device_loader.get_device(device_id)
        if not device:
            return
        conn = get_connection()
        c = conn.cursor()
        for attr_name, attr_cfg in device.attributes.items():
            default_val = attr_cfg.get("default")
            c.execute(
                "INSERT OR REPLACE INTO device_states (device_id, key, value, updated_at) VALUES (?, ?, ?, ?)",
                (device_id, attr_name, str(default_val), datetime.now().isoformat())
            )
        conn.commit()
        conn.close()

    def execute(self, device_id: str, action: str, params: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        if not self.device_loader.device_exists(device_id):
            return False, f"设备 {device_id} 不存在", {}

        device = self.device_loader.get_device(device_id)
        if not device.supports_action(action):
            return False, f"设备 {device_id} 不支持动作 {action}", {}

        current_state = self.get_device_state(device_id)
        if not current_state:
            self.initialize_device_state(device_id)
            current_state = self.get_device_state(device_id)

        new_state = current_state.copy()

        # 数据驱动：从 FIXED_ACTION_STATE 获取固定映射，或从 YAML params 推断
        if action in FIXED_ACTION_STATE:
            new_state.update(FIXED_ACTION_STATE[action])
        else:
            self._apply_params(device, new_state, params)

        # 保存状态
        conn = get_connection()
        c = conn.cursor()
        for key, value in new_state.items():
            c.execute(
                "INSERT OR REPLACE INTO device_states (device_id, key, value, updated_at) VALUES (?, ?, ?, ?)",
                (device_id, key, str(value), datetime.now().isoformat())
            )
        conn.commit()
        conn.close()

        return True, f"设备 {device_id} 执行 {action} 成功", new_state

    def _apply_params(self, device, new_state: Dict[str, Any], params: Dict[str, Any]):
        """根据 YAML 设备属性将参数值映射到状态变更"""
        for param_name, param_value in params.items():
            # 直接匹配属性名
            if param_name in device.attributes:
                new_state[param_name] = param_value
                continue
            # 推断：常见别名映射
            alias_map = {"value": "temperature", "speed": "speed"}
            if param_name in alias_map and alias_map[param_name] in device.attributes:
                new_state[alias_map[param_name]] = param_value
                continue
            # 通用：值类型匹配数值属性
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