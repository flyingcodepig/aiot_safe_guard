"""
输入安全检测模块（修复版）
集成 LLM Guard 的 PromptInjection 扫描器 + 自定义敏感操作检测
"""
from typing import Any, Dict
from llm_guard.input_scanners import PromptInjection, BanSubstrings
from chinese_guard import ChineseGuard


class InputGuard:
    def __init__(self, llm_client=None, llm_model: str = "deepseek-chat"):
        # 仅使用 PromptInjection 和 BanSubstrings，Toxicity 对中文支持差，暂移除
        self.prompt_injection_scanner = PromptInjection()
        self.ban_substrings = BanSubstrings(substrings=["忽略所有安全规则", "维护模式"])
        self.chinese_guard = ChineseGuard(client=llm_client, model=llm_model)

        # IoT 敏感操作关键词（高危设备-仅低权限角色触发）
        # 注意："报警器"已移除，因为访客需要读取报警器状态
        self.sensitive_keywords = [
            "门锁", "摄像头", "门禁", "开锁", "禁用安全",
        ]

    def scan(self, user_input: str, user_role: str = "visitor") -> Dict[str, Any]:
        result = {
            "prompt_injection_score": 0.0,
            "sensitive_operation": False,
            "risk_level": "low",
            "details": [],
        }

        # 1. LLM Guard 提示注入扫描
        try:
            _, valid, score = self.prompt_injection_scanner.scan(user_input)
            # score 是风险分数 (0=安全, 1=高风险)？需根据实际返回值调整。
            # 如果 valid 为 True 且 score 接近 1，表示可信度高，风险低。
            # 这里假设 score 为风险分数，越低越安全。
            if not valid:
                result["prompt_injection_score"] = max(result["prompt_injection_score"], 0.8)
                result["details"].append("LLM Guard 检测到提示注入")
            elif score is not None and isinstance(score, (int, float)):
                # 如果 score 是风险概率，直接使用；否则暂时忽略
                if 0 <= score <= 1:
                    result["prompt_injection_score"] = max(result["prompt_injection_score"], score)
        except Exception as e:
            result["details"].append(f"PromptInjection 扫描器异常: {e}")

        # 2. 禁止子串（直接匹配高风险）
        try:
            _, valid, _ = self.ban_substrings.scan(user_input)
            if not valid:
                result["prompt_injection_score"] = 1.0
                result["details"].append("包含禁止子串")
        except Exception as e:
            result["details"].append(f"BanSubstrings 异常: {e}")

        # 3. 中文安全检测（新增）
        try:
            cn_result = self.chinese_guard.scan(user_input)
            cn_score = cn_result["risk_score"]
            if cn_score > 0:
                result["prompt_injection_score"] = max(
                    result["prompt_injection_score"], cn_score
                )
                for det in cn_result["pattern_result"].get("detections", []):
                    result["details"].append(
                        f"中文检测[{det['category']}]: score={det['weight']:.2f}"
                    )
                if cn_result.get("llm_result") and cn_result["llm_result"].get("triggered"):
                    result["details"].append(
                        f"DeepSeek Judge: {cn_result['llm_result'].get('reason', '')}"
                    )
        except Exception as e:
            result["details"].append(f"中文检测异常: {e}")

        # 4. IoT 敏感操作检测（仅低权限角色触发警告）
        if user_role in ("visitor", "student"):
            for kw in self.sensitive_keywords:
                if kw in user_input:
                    result["sensitive_operation"] = True
                    result["details"].append(f"包含敏感操作词: {kw}")
                    break

        # 5. 综合风险等级
        if result["prompt_injection_score"] >= 0.9:
            result["risk_level"] = "high"
        elif result["prompt_injection_score"] >= 0.5 or result["sensitive_operation"]:
            result["risk_level"] = "medium"
        else:
            result["risk_level"] = "low"

        return result