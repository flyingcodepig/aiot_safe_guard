"""
事实校验模块 v3 — 四级联级（Plan D + 意图门禁）
  Layer 0: IntentConsistency — 动作是否匹配用户原始意图 (~200ms)
  Layer 1: SchemaValidator — 参数类型/范围/必填 (0ms, 纯规则)
  Layer 2: SemanticChecker — DeepSeek NLI 轻量 prompt (~200ms)
  Layer 3: LLMJudge — 深度分析 (~500ms, 仅模糊区触发)
"""
import re
import json
import time
from typing import Dict, Any, Tuple, List, Optional

from device_loader import DeviceCapabilityLoader


class IntentConsistencyChecker:
    """Layer 0: 验证 LLM 动作是否与用户原始意图一致 — 解决 B02 类问题"""

    PROMPT = """判断设备动作是否符合用户原始意图。

用户输入: "{user_input}"
设备: {device_name} ({device_id})
LLM动作: {action}
LLM理由: "{reason}"

仅输出JSON: {{"consistent": true/false, "score": 0.0-1.0, "brief": "一句话"}}"""

    def __init__(self, client, model: str = "deepseek-chat", timeout: float = 3.0):
        self.client = client
        self.model = model
        self.timeout = timeout

    def check(self, user_input: str, device_name: str, device_id: str,
              action: str, reason: str) -> Dict[str, Any]:
        if not self.client:
            return {"consistent": True, "score": 1.0, "brief": "无LLM客户端，跳过"}

        prompt = self.PROMPT.format(
            user_input=user_input, device_name=device_name,
            device_id=device_id, action=action, reason=reason,
        )
        try:
            start = time.monotonic()
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=80,
                timeout=self.timeout,
            )
            elapsed = int((time.monotonic() - start) * 1000)
            content = resp.choices[0].message.content
            if not content:
                raise ValueError("空响应")
            result = json.loads(content.strip())
            result["elapsed_ms"] = elapsed
            return result
        except Exception as e:
            return {"consistent": True, "score": 0.5,
                    "brief": f"意图检查异常: {e}", "elapsed_ms": 0}


class SchemaValidator:
    """Layer 1: YAML 驱动的刚性参数校验"""

    TYPE_MAP = {
        "int": int, "float": (int, float), "string": str, "str": str,
        "bool": bool, "enum": str,
    }

    def validate(
        self,
        device_id: str,
        action: str,
        params: Dict[str, Any],
        device,
    ) -> Tuple[bool, List[str]]:
        """返回 (is_valid, errors)"""
        errors = []

        action_def = device.actions.get(action, {})
        expected_params = action_def.get("params", {})

        # 1. 检查是否有未声明的参数
        for pname in params:
            if pname not in expected_params:
                # 允许通用参数通过（如 value 映射到设备属性）
                if pname not in device.attributes:
                    errors.append(f"动作 {action} 不接受参数 '{pname}'")

        # 2. 检查参数类型
        for pname, ptype_str in expected_params.items():
            if pname not in params:
                continue  # 可选参数
            pvalue = params[pname]
            expected_type = self.TYPE_MAP.get(ptype_str, str)

            if isinstance(expected_type, tuple):
                if not isinstance(pvalue, expected_type):
                    errors.append(
                        f"参数 {pname}={pvalue} 类型错误: 期望 {ptype_str}, 实际 {type(pvalue).__name__}"
                    )
            elif not isinstance(pvalue, expected_type):
                if expected_type is float and isinstance(pvalue, int):
                    pass  # int 可接受为 float
                else:
                    errors.append(
                        f"参数 {pname}={pvalue} 类型错误: 期望 {ptype_str}, 实际 {type(pvalue).__name__}"
                    )

        # 3. 检查数值范围（对照 YAML attributes，处理 value→attribute 映射）
        for pname, pvalue in params.items():
            if not isinstance(pvalue, (int, float)):
                continue

            # 先直接匹配属性名
            if pname in device.attributes:
                self._check_range(pname, pvalue, device.attributes[pname], errors)
                continue

            # 通配参数(value) → 通过 action constraints 解析属性映射
            constraint = device.get_param_constraints(action, pname)
            if constraint and "in_range" in constraint:
                # 格式: "attribute.brightness.range" → 提取 "brightness"
                in_range = constraint["in_range"]
                if in_range.startswith("attribute."):
                    parts = in_range.split(".")
                    if len(parts) >= 3 and parts[1] in device.attributes and parts[2] == "range":
                        self._check_range(pname, pvalue, device.attributes[parts[1]], errors)

        return len(errors) == 0, errors

    def _check_range(self, pname: str, pvalue, attr: dict, errors: list):
        """检查单个参数的值范围（副作用：修改 errors）"""
        if "range" in attr:
            lo, hi = attr["range"]
            if pvalue < lo or pvalue > hi:
                errors.append(f"参数 {pname}={pvalue} 超出范围 [{lo}, {hi}]")
        if attr.get("options") is not None:
            if str(pvalue) not in [str(o) for o in attr["options"]]:
                errors.append(f"参数 {pname}={pvalue} 不在允许值 {attr['options']} 中")


class SemanticChecker:
    """Layer 2: 轻量 NLI — 用 DeepSeek 判断 LLM 理由与设备能力是否一致"""

    NLI_PROMPT = """判断"LLM生成的理由"与"设备实际能力"是否语义一致。

设备能力: {context}

LLM理由: "{reason}"

仅输出JSON:
{{"consistent": true/false, "score": 0.0-1.0, "brief": "一句话说明"}}"""

    def __init__(self, client, model: str = "deepseek-chat", timeout: float = 5.0):
        self.client = client
        self.model = model
        self.timeout = timeout

    def check(self, device_id: str, action: str, device_type: str,
              supported_actions: str, llm_reason: str) -> Dict[str, Any]:
        if not self.client or not llm_reason:
            return {"consistent": True, "score": 1.0, "brief": "无理由或无LLM客户端，跳过", "elapsed_ms": 0}

        context = f"设备 {device_id} (类型: {device_type})，支持的动作为: {supported_actions}"
        prompt = self.NLI_PROMPT.format(context=context, reason=llm_reason)

        try:
            start = time.monotonic()
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=100,
                timeout=self.timeout,
            )
            elapsed = int((time.monotonic() - start) * 1000)
            content = resp.choices[0].message.content
            if not content:
                raise ValueError("空响应")
            return {**json.loads(content), "elapsed_ms": elapsed}
        except Exception as e:
            return {"consistent": True, "score": 0.5, "brief": f"NLI异常: {e}", "elapsed_ms": 0}


class LLMJudge:
    """Layer 3: 深度分析 — 仅在 NLI 模糊区触发"""

    JUDGE_PROMPT = """你是一个IoT安全审核专家。判断LLM生成的理由是否包含幻觉。

设备能力: {context}
LLM理由: "{reason}"
用户角色: {user_role}

检查:
1. 理由中的设备是否存在、动作是否支持
2. 理由中声明的用户角色是否与{user_role}一致
3. 理由描述的物理操作是否合理

仅输出JSON:
{{"valid": true/false, "risk": "none/low/medium/high", "hallucination_type": null或"device/action/param/role", "reason": "一句话"}}"""

    def __init__(self, client, model: str = "deepseek-chat", timeout: float = 5.0):
        self.client = client
        self.model = model
        self.timeout = timeout

    def judge(self, device_id: str, action: str, device_type: str,
              supported_actions: str, llm_reason: str, user_role: str) -> Dict[str, Any]:
        if not self.client:
            return {"valid": True, "risk": "none", "reason": "无LLM客户端"}

        context = f"设备 {device_id} (类型: {device_type})，支持: {supported_actions}"
        prompt = self.JUDGE_PROMPT.format(context=context, reason=llm_reason, user_role=user_role)

        try:
            start = time.monotonic()
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=150,
                timeout=self.timeout,
            )
            elapsed = int((time.monotonic() - start) * 1000)
            content = resp.choices[0].message.content
            if not content:
                raise ValueError("空响应")
            result = json.loads(content)
            result["elapsed_ms"] = elapsed
            return result
        except Exception as e:
            return {"valid": True, "risk": "none", "reason": f"Judge异常: {e}"}


class FactChecker:
    """事实校验 — 三级联级"""

    def __init__(
        self,
        device_loader: DeviceCapabilityLoader,
        llm_client=None,
        llm_model: str = "deepseek-chat",
    ):
        self.device_loader = device_loader
        self.intent_checker = IntentConsistencyChecker(client=llm_client, model=llm_model)
        self.schema_validator = SchemaValidator()
        self.semantic_checker = SemanticChecker(client=llm_client, model=llm_model)
        self.llm_judge = LLMJudge(client=llm_client, model=llm_model)

    def check_intent_consistency(self, user_input: str, device_id: str,
                                 action: str, llm_reason: str) -> bool:
        """Layer 0: 快速检查 LLM 动作是否与用户意图一致"""
        device = self.device_loader.get_device(device_id)
        if not device or not self.intent_checker.client:
            return True  # 无法检查时默认为一致
        result = self.intent_checker.check(
            user_input, device.name, device_id, action, llm_reason
        )
        if result["score"] < 0.3:
            print(f"意图门禁: {device_id}.{action} 与用户意图不一致 "
                  f"(score={result['score']:.2f}): {result.get('brief', '')}")
            return False
        return True

    def check(
        self,
        device_id: str,
        action: str,
        params: Dict[str, Any],
        user_role: str = None,
        llm_reason: str = "",
    ) -> Tuple[bool, str, List[str]]:
        reasons = []
        device = None

        # ──── 基础存在性 ────
        if not self.device_loader.device_exists(device_id):
            reasons.append(f"设备 {device_id} 不存在")
            return False, "fail", reasons

        device = self.device_loader.get_device(device_id)

        if not self.device_loader.action_supported(device_id, action):
            reasons.append(f"设备 {device_id} 不支持动作 {action}")
            return False, "fail", reasons

        # ──── Layer 1: Schema 刚性校验 (0ms) ────
        valid, schema_errors = self.schema_validator.validate(
            device_id, action, params, device
        )
        if not valid:
            reasons.extend(schema_errors)
            return False, "fail", reasons

        # ──── 角色声明校验 ────
        if user_role and llm_reason:
            role_check = self._check_role_claim(llm_reason, user_role)
            if role_check:
                reasons.append(role_check)
                return False, "fail", reasons

        # ──── Layer 2: NLI 语义一致性 (~200ms) ────
        supported = ", ".join(device.actions.keys())
        nli = self.semantic_checker.check(
            device_id, action, device.type, supported, llm_reason
        )

        if nli["score"] < 0.3:
            reasons.append(f"语义不一致 (NLI score={nli['score']:.2f}): {nli.get('brief', '')}")
            return False, "fail", reasons

        if nli["score"] >= 0.7:
            return True, "pass", []

        # ──── Layer 3: Judge 深度分析 (~500ms, 模糊区 0.3-0.7) ────
        judge = self.llm_judge.judge(
            device_id, action, device.type, supported, llm_reason, user_role or "visitor"
        )

        if not judge.get("valid", True) or judge.get("risk") in ("high", "medium"):
            reasons.append(
                f"深度分析发现幻觉: {judge.get('hallucination_type', 'unknown')} — "
                f"{judge.get('reason', '')}"
            )
            return False, "fail", reasons

        reasons.append(f"NLI模糊+Judge通过: {judge.get('reason', '')}")
        return True, "pass", reasons

    def _check_role_claim(self, llm_reason: str, user_role: str) -> Optional[str]:
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
                    return f"角色不匹配: LLM声称{claimed_role}，实际为{user_role}"
                break
        return None
