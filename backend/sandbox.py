"""仿真沙箱引擎 - 在虚拟设备状态机上执行动作"""
#import sqlite3
from typing import Dict, Any, Tuple
from datetime import datetime

from database import get_connection
from device_loader import DeviceCapabilityLoader

class SandboxEngine:
    def __init__(self, device_loader: DeviceCapabilityLoader):
        self.device_loader = device_loader

    def get_device_state(self, device_id: str) -> Dict[str, Any]:
        """获取设备当前状态"""
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT key, value FROM device_states WHERE device_id = ?", (device_id,))
        state = {}
        for row in c.fetchall():
            state[row["key"]] = self._parse_value(row["value"])
        conn.close()

        # 如果没有状态记录，从设备能力库中取默认值
        if not state:
            device = self.device_loader.get_device(device_id)
            if device:
                for attr_name, attr_cfg in device.attributes.items():
                    state[attr_name] = attr_cfg.get("default")
        return state

    def initialize_device_state(self, device_id: str):
        """为新设备初始化默认状态"""
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
        """
        执行设备动作
        返回: (success, message, new_state)
        """
        if not self.device_loader.device_exists(device_id):
            return False, f"设备 {device_id} 不存在", {}

        device = self.device_loader.get_device(device_id)
        if not device.supports_action(action):
            return False, f"设备 {device_id} 不支持动作 {action}", {}

        # 获取当前状态，如果不存在则初始化
        current_state = self.get_device_state(device_id)
        if not current_state:
            self.initialize_device_state(device_id)
            current_state = self.get_device_state(device_id)

        # 根据动作类型更新状态
        new_state = current_state.copy()
        if action == "turn_on":
            new_state["power"] = True
        elif action == "turn_off":
            new_state["power"] = False
        elif action == "set_brightness" and "value" in params:
            new_state["brightness"] = params["value"]
        elif action == "set_speed" and "speed" in params:
            new_state["speed"] = params["speed"]
        elif action == "set_temp" and "value" in params:
            new_state["temperature"] = params["value"]
        elif action == "unlock":
            new_state["status"] = "unlocked"
        elif action == "lock":
            new_state["status"] = "locked"
        elif action == "silence":
            new_state["status"] = "normal"
        elif action == "start_recording":
            new_state["recording"] = True
        elif action == "stop_recording":
            new_state["recording"] = False
        elif action == "set_mode" and "mode" in params:
            new_state["mode"] = params["mode"]
        elif action == "read":
            pass
        else:
            # 通用参数更新
            for k, v in params.items():
                if k in device.attributes:
                    new_state[k] = v

        # 保存新状态到数据库
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

    def _parse_value(self, value_str: str) -> Any:
        """将数据库存储的字符串值解析为正确的类型"""
        if value_str is None:
            return None
        if value_str.lower() == "true":
            return True
        if value_str.lower() == "false":
            return False
        try:
            if "." in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            return value_str