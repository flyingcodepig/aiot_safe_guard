"""设备能力库加载器 - 读取YAML设备文件，提供查询接口"""
import os
import yaml
from typing import Dict, Any#List

class DeviceCapability:
    """单个设备的能力描述"""
    def __init__(self, device_id: str, config: Dict[str, Any]):
        self.device_id = device_id
        self.name = config.get("name", device_id)
        self.type = config.get("type", "unknown")
        self.aliases = config.get("aliases", [])
        self.attributes = {}
        self.actions = {}
        self._parse_config(config)

    def _parse_config(self, config: Dict[str, Any]):
        # 解析属性
        for attr in config.get("attributes", []):
            self.attributes[attr["name"]] = {
                "type": attr.get("type", "string"),
                "access": attr.get("access", "r"),
                "range": attr.get("range"),
                "options": attr.get("options"),
                "unit": attr.get("unit"),
                "default": attr.get("default"),
            }
        # 解析动作
        for action in config.get("actions", []):
            self.actions[action["name"]] = {
                "params": action.get("params", {}),
                "constraints": action.get("constraints", []),
            }

    def supports_action(self, action: str) -> bool:
        return action in self.actions

    def get_param_constraints(self, action: str, param_name: str) -> Dict[str, Any]:
        """获取指定动作的指定参数约束"""
        action_def = self.actions.get(action, {})
        for constraint in action_def.get("constraints", []):
            if constraint.get("param") == param_name:
                return constraint
        return {}

class DeviceCapabilityLoader:
    """设备能力库管理器"""
    def __init__(self, device_dir: str = "./data/devices"):
        self.device_dir = device_dir
        self.devices: Dict[str, DeviceCapability] = {}
        self.load_all()

    def load_all(self):
        """加载设备目录下所有YAML文件"""
        if not os.path.exists(self.device_dir):
            os.makedirs(self.device_dir)
            print(f"创建设备配置目录: {self.device_dir}")
            # 创建默认设备文件
            self._create_default_devices()

        for filename in os.listdir(self.device_dir):
            if filename.endswith((".yaml", ".yml")):
                filepath = os.path.join(self.device_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                    device_id = config.get("device_id", filename.replace(".yaml", ""))
                    self.devices[device_id] = DeviceCapability(device_id, config)

        print(f"已加载 {len(self.devices)} 个设备")

    def _create_default_devices(self):
        """创建默认设备配置文件"""
        devices = [
            {
                "device_id": "light_a1",
                "name": "实验区A智能灯1",
                "type": "light",
                "attributes": [
                    {"name": "power", "type": "bool", "default": False},
                    {"name": "brightness", "type": "int", "range": [1, 100], "default": 80},
                ],
                "actions": [
                    {"name": "turn_on", "params": {}, "constraints": [{"role_required": "student"}]},
                    {"name": "turn_off", "params": {}, "constraints": [{"role_required": "student"}]},
                    {
                        "name": "set_brightness",
                        "params": {"value": "int"},
                        "constraints": [
                            {"param": "value", "in_range": "attribute.brightness.range"},
                            {"role_required": "student"},
                        ],
                    },
                ],
            },
            {
                "device_id": "fan_a1",
                "name": "实验区A吊扇1",
                "type": "fan",
                "attributes": [
                    {"name": "power", "type": "bool", "default": False},
                    {"name": "speed", "type": "int", "range": [0, 80], "default": 0},
                ],
                "actions": [
                    {"name": "turn_on", "params": {}, "constraints": [{"role_required": "student"}]},
                    {"name": "turn_off", "params": {}, "constraints": [{"role_required": "student"}]},
                    {
                        "name": "set_speed",
                        "params": {"speed": "int"},
                        "constraints": [
                            {"param": "speed", "in_range": "attribute.speed.range"},
                            {"role_required": "student"},
                        ],
                    },
                ],
            },
            {
                "device_id": "door_office",
                "name": "办公室门锁",
                "type": "door_lock",
                "attributes": [
                    {"name": "status", "type": "enum", "options": ["locked", "unlocked"], "default": "locked"},
                ],
                "actions": [
                    {"name": "lock", "params": {}, "constraints": [{"role_required": "teacher"}]},
                    {
                        "name": "unlock",
                        "params": {},
                        "constraints": [
                            {"role_required": "teacher"},
                            # 解锁需要用户有teacher或admin权限
                        ],
                    },
                ],
            },
            {
                "device_id": "solder_b1",
                "name": "恒温焊台B1",
                "type": "instrument",
                "attributes": [
                    {"name": "power", "type": "bool", "default": False},
                    {"name": "temperature", "type": "float", "range": [200, 450], "unit": "°C", "default": 300},
                ],
                "actions": [
                    {"name": "turn_on", "params": {}, "constraints": [{"role_required": "teacher"}]},
                    {"name": "turn_off", "params": {}, "constraints": [{"role_required": "teacher"}]},
                    {
                        "name": "set_temp",
                        "params": {"value": "float"},
                        "constraints": [
                            {"param": "value", "in_range": "attribute.temperature.range"},
                            {"role_required": "teacher"},
                        ],
                    },
                ],
            },
            {
                "device_id": "smoke_alarm",
                "name": "烟雾报警器",
                "type": "alarm",
                "attributes": [
                    {"name": "status", "type": "enum", "options": ["normal", "alarming"], "default": "normal"},
                ],
                "actions": [
                    {"name": "read", "params": {}, "constraints": [{"role_required": "visitor"}]},
                    {"name": "silence", "params": {}, "constraints": [{"role_required": "admin"}]},
                ],
            },
        ]

        for device in devices:
            filepath = os.path.join(self.device_dir, f"{device['device_id']}.yaml")
            with open(filepath, "w", encoding="utf-8") as f:
                yaml.dump(device, f, allow_unicode=True, default_flow_style=False)

    def device_exists(self, device_id: str) -> bool:
        return device_id in self.devices

    def get_device(self, device_id: str) -> DeviceCapability:
        return self.devices.get(device_id)

    def get_device_type(self, device_id: str) -> str:
        device = self.get_device(device_id)
        return device.type if device else "unknown"

    def action_supported(self, device_id: str, action: str) -> bool:
        device = self.get_device(device_id)
        return device.supports_action(action) if device else False