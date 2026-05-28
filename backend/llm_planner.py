"""
大模型任务规划器
将自然语言指令转换为结构化的设备动作计划
"""
import json
import re
from typing import List, Dict, Any, Optional
from openai import OpenAI

# 系统 Prompt 模板
SYSTEM_PROMPT = """你是一个AIoT设备控制规划器，负责将用户的自然语言指令转换为结构化的设备动作计划。

## 核心规则
1. 只输出合法的 JSON 数组，不要输出任何解释、markdown代码块或其他内容。
2. 每个动作必须包含 device_id、action、params、reason 四个字段。
3. 尽可能将用户输入匹配到可用设备，利用设备的"别名"来做模糊匹配。
4. 如果用户输入中提到了多个设备或复合指令，你需要拆解为多个动作。
5. 不要因为"不确定"就返回空数组 — 你必须尽力匹配最可能的设备和动作。
6. 如果用户只是查看/查询/询问状态，生成一个 read 动作（如果设备支持），否则生成 turn_on 后跟 read。

## 动作映射指南
- "打开" → turn_on
- "关闭" / "关掉" → turn_off
- "调高" / "调低" / "调到" / "设置为" + 数值 → 对应的 set_* 动作
- "查看" / "查询" / "什么状态" → read
- "解锁" / "开锁" / "开门" → unlock
- "上锁" / "锁门" / "锁上" → lock

## 可用设备列表
{device_list}

## Few-Shot 示例

示例1: 多动作拆解
用户: "打开实验区A的灯，把风扇调到50"
输出: [
  {{"device_id": "light_a1", "action": "turn_on", "params": {{}}, "reason": "用户要求打开实验区A的灯"}},
  {{"device_id": "fan_a1", "action": "set_speed", "params": {{"speed": 50}}, "reason": "用户要求设置风扇转速为50"}}
]

示例2: 别名匹配
用户: "把焊台温度调到300"
输出: [
  {{"device_id": "solder_b1", "action": "set_temp", "params": {{"value": 300}}, "reason": "用户要求将焊台设为300°C"}}
]

示例3: 开门/关门映射
用户: "打开办公室门"
输出: [
  {{"device_id": "door_office", "action": "unlock", "params": {{}}, "reason": "用户要求打开办公室门"}}
]

示例4: 查询状态
用户: "查看烟雾报警器状态"
输出: [
  {{"device_id": "smoke_alarm", "action": "read", "params": {{}}, "reason": "用户询问报警器状态"}}
]

示例5: 复合指令
用户: "打开走廊灯和空调，把空调温度调到26度"
输出: [
  {{"device_id": "light_corridor1", "action": "turn_on", "params": {{}}, "reason": "用户要求打开走廊灯"}},
  {{"device_id": "ac_a1", "action": "turn_on", "params": {{}}, "reason": "用户要求打开空调"}},
  {{"device_id": "ac_a1", "action": "set_temp", "params": {{"value": 26}}, "reason": "用户要求设置空调温度为26°C"}}
]

现在开始处理用户输入，只输出 JSON 数组。"""

DEVICE_LIST_TEMPLATE = """- 设备ID: {device_id}
  名称: {name}
  类型: {type}
  别名: {aliases}
  支持的动作: {actions}
"""


class LLMPlanner:
    """大模型任务规划器"""

    def __init__(
        self,
        model: str = "deepseek-chat",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url or "https://api.deepseek.com",
        )
        self.model = model
        self.system_prompt = ""

    def build_system_prompt(self, device_loader):
        """根据当前设备库构建系统提示词"""
        device_descriptions = []
        for device_id, device in device_loader.devices.items():
            actions_list = list(device.actions.keys())
            device_descriptions.append(
                DEVICE_LIST_TEMPLATE.format(
                    device_id=device_id,
                    name=device.name,
                    type=device.type,
                    aliases=", ".join(device.aliases) if device.aliases else "无",
                    actions=", ".join(actions_list),
                )
            )
        self.system_prompt = SYSTEM_PROMPT.format(
            device_list="\n".join(device_descriptions)
        )

    def plan(self, user_input: str) -> List[Dict[str, Any]]:
        """将用户输入转换为动作计划列表（含重试+兜底）"""
        if not self.system_prompt:
            raise ValueError("系统提示词未初始化，请先调用 build_system_prompt()")

        # 第1次: 低温精确调用
        actions = self._call_llm(user_input, temperature=0.1)
        if actions and len(actions) > 0:
            return actions

        # 第2次: 中温放宽重试
        actions = self._call_llm(user_input, temperature=0.4)
        if actions and len(actions) > 0:
            return actions

        # 第3次: 高温再试
        actions = self._call_llm(user_input, temperature=0.7)
        if actions and len(actions) > 0:
            return actions

        # 全部失败: 返回空，由 pipeline 的 empty-actions 逻辑处理
        print(f"LLM 三次尝试均未生成有效动作: {user_input}")
        return []

    def _call_llm(self, user_input: str, temperature: float) -> List[Dict[str, Any]]:
        """单次 LLM 调用"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input},
        ]
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=500,
            )
            content = response.choices[0].message.content.strip()
            return self._parse_response(content)
        except Exception as e:
            print(f"LLM 调用失败 (temp={temperature}): {e}")
            return []

    def _parse_response(self, content: str) -> List[Dict[str, Any]]:
        """从 LLM 回复中提取 JSON 动作列表"""
        content = re.sub(r'```(json)?', '', content).strip()
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
            else:
                return []
        except json.JSONDecodeError:
            match = re.search(r'\[.*?]', content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            print(f"无法解析 LLM 输出: {content}")
            return []


class FallbackMatcher:
    """本地关键词兜底匹配器：LLM 失败时用关键词+别名匹配设备/动作"""

    ACTION_KEYWORDS = {
        "turn_on":     ["打开", "开启", "启动", "开", "点亮", "开机"],
        "turn_off":    ["关闭", "关掉", "关", "熄灭", "停掉", "停止", "关机"],
        "unlock":      ["解锁", "开锁", "开门", "打开门", "打开"],
        "lock":        ["上锁", "锁门", "锁上", "锁", "关上", "关上门"],
        "read":        ["查看", "查询", "状态", "读取", "检查", "是多少"],
        "silence":     ["静音", "消音", "关闭声音", "声音关掉", "关掉声音", "关闭"],
        "set_temp":    ["调到", "温度", "调高", "调低", "设置为"],
        "set_speed":   ["转速", "速度", "调到", "风速"],
        "set_brightness": ["亮度", "调到", "调亮", "调暗"],
        "set_mode":    ["模式", "切换", "制冷", "制热", "送风"],
        "start_recording": ["录像", "开始录像", "开始录制"],
        "stop_recording":  ["停止录像", "停止录制"],
    }

    def __init__(self, device_loader):
        self.device_loader = device_loader

    def match(self, user_input: str) -> list:
        """尝试从用户输入中匹配设备和动作，返回动作列表"""
        actions = []

        for device_id, device in self.device_loader.devices.items():
            if not self._device_matched(device_id, device, user_input):
                continue

            # 找到匹配的设备，尝试匹配动作
            matched_action = self._match_action(device, user_input)

            if matched_action:
                params = self._extract_params(device, matched_action, user_input)
                actions.append({
                    "device_id": device_id,
                    "device_type": device.type,
                    "action": matched_action,
                    "params": params,
                    "llm_reason": f"关键词兜底: 用户输入匹配到设备{device.name}和动作{matched_action}",
                })

        return actions

    def _device_matched(self, device_id: str, device, user_input: str) -> bool:
        """检查用户输入是否提到了这个设备"""
        search_texts = [device.name, device_id] + device.aliases
        for text in search_texts:
            if text and text.lower() in user_input.lower():
                return True
        return False

    def _match_action(self, device, user_input: str) -> str | None:
        """在用户输入中查找匹配的动作"""
        best_action = None
        best_len = 0
        for action_name, keywords in self.ACTION_KEYWORDS.items():
            if action_name not in device.actions:
                continue
            for kw in keywords:
                if kw in user_input and len(kw) > best_len:
                    best_action = action_name
                    best_len = len(kw)
        return best_action

    def _extract_params(self, device, action_name: str, user_input: str) -> dict:
        """从用户输入中提取数值参数"""
        import re
        params = {}
        action_def = device.actions.get(action_name, {})
        param_specs = action_def.get("params", {})

        if not param_specs:
            return params

        for param_name, param_type in param_specs.items():
            patterns = [
                rf'{param_name}\s*[=是为：:]\s*(\d+)',
                rf'(\d+)\s*度',
                rf'调[到至为]\s*(\d+)',
                rf'设[置为]\s*(\d+)',
                rf'(\d+)\s*档',
                rf'转速\s*(\d+)',
            ]
            for pattern in patterns:
                match = re.search(pattern, user_input)
                if match:
                    val = match.group(1)
                    params[param_name] = float(val) if '.' in val else int(val)
                    break

        return params


class ActionParser:
    """动作解析器：校验和规范化 LLM 输出的动作计划"""

    def __init__(self, device_loader):
        self.device_loader = device_loader

    def parse(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed_actions = []
        errors = []

        for idx, raw_action in enumerate(actions):
            device_id = raw_action.get("device_id", "")
            action = raw_action.get("action", "")
            params = raw_action.get("params", {})
            reason = raw_action.get("reason", "")

            if not device_id or not action:
                errors.append(f"动作 {idx}: 缺少 device_id 或 action")
                continue
            if not self.device_loader.device_exists(device_id):
                errors.append(f"动作 {idx}: 设备 {device_id} 不存在")
                continue
            if not self.device_loader.action_supported(device_id, action):
                errors.append(f"动作 {idx}: 设备 {device_id} 不支持动作 {action}")
                continue

            device = self.device_loader.get_device(device_id)
            parsed_actions.append({
                "device_id": device_id,
                "device_type": device.type,
                "action": action,
                "params": params if isinstance(params, dict) else {},
                "llm_reason": reason,
            })

        if errors:
            print("动作解析警告:", "\n".join(errors))
        return parsed_actions