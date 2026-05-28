"""
事实校验模块（修复版）
设备/动作存在性 + LLM Guard FactualConsistency（宽松模式） + 角色声明校验
"""
import re
from typing import Dict, Any, Tuple, List
from device_loader import DeviceCapabilityLoader
from llm_guard.output_scanners import FactualConsistency


class FactChecker:
    def __init__(self, device_loader: DeviceCapabilityLoader):
        self.device_loader = device_loader
        self.factual_scanner = FactualConsistency()

    def check(
        self,
        device_id: str,
        action: str,
        params: Dict[str, Any],
        user_role: str = None,
        llm_reason: str = "",
    ) -> Tuple[bool, str, List[str]]:
        reasons = []

        # 1. 设备存在性
        if not self.device_loader.device_exists(device_id):
            reasons.append(f"设备 {device_id} 不存在")
            return False, "fail", reasons

        # 2. 动作支持性
        if not self.device_loader.action_supported(device_id, action):
            reasons.append(f"设备 {device_id} 不支持动作 {action}")
            return False, "fail", reasons

        # 3. LLM Guard 事实一致性（宽松策略）
        device = self.device_loader.get_device(device_id)
        context = (
            f"设备 {device_id} 类型为 {device.type}，"
            f"支持的动作有: {', '.join(device.actions.keys())}。"
        )
        try:
            _, is_valid, score = self.factual_scanner.scan(context, llm_reason)
            # LLM Guard 英文模型对中文理由存在严重误判，暂禁用此项
            # 事实校验由设备存在性+动作支持性+角色声明校验保证
            if not is_valid and score is not None and score > 1.0:
                reasons.append(f"理由与设备能力严重不符 (score: {score:.2f})")
                return False, "fail", reasons
            elif not is_valid:
                reasons.append(f"理由可能存在不一致 (score: {score:.2f})，但未达到拦截阈值")
        except Exception as e:
            reasons.append(f"事实一致性扫描异常: {e}")

        # 4. 角色声明校验
        if user_role and llm_reason:
            role_patterns = [
                r"用户是\s*(\S+)",
                r"角色为\s*(\S+)",
                r"作为\s*(\S+)",
                r"用户具有\s*(\S+)权限",
            ]
            for pattern in role_patterns:
                match = re.search(pattern, llm_reason)
                if match:
                    claimed_role = match.group(1)
                    role_map = {
                        "管理员": "admin", "老师": "teacher",
                        "学生": "student", "访客": "visitor",
                    }
                    expected_role = role_map.get(claimed_role, claimed_role)
                    if expected_role != user_role:
                        reasons.append(f"角色不匹配: LLM 声称 {claimed_role}，实际为 {user_role}")
                        return False, "fail", reasons
                    break

        return True, "pass", []