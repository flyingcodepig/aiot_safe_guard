"""
SelfCheckGPT 集成模块
通过多采样比较检测 LLM 生成的动作计划中的幻觉。
支持两种方法:
  - llm_prompt: 使用现有 DeepSeek 客户端进行自我一致性检查 (无需额外依赖)
  - nli: 使用 selfcheckgpt 包的 NLI 方法 (需要 torch)
"""
import os
from typing import Dict, Any, List, Optional, Tuple


class SelfCheckWrapper:
    def __init__(
        self,
        method: str = "llm_prompt",
        client=None,
        model: str = "deepseek-chat",
        threshold: float = 0.5,
    ):
        self.method = method
        self.client = client
        self.model = model
        self.threshold = threshold
        self._nli_model = None

    def check(
        self,
        prompt: str,
        original_actions: List[Dict[str, Any]],
        plan_func,
        num_samples: int = 3,
    ) -> Dict[str, Any]:
        """
        对 LLM 生成的动作计划进行一致性检测。
        plan_func: 可调用对象，接受 user_input 返回 raw_actions list
        返回: {"risk_score": float, "details": list, "method": str}
        """
        if self.method == "llm_prompt":
            return self._check_llm_prompt(prompt, original_actions, plan_func, num_samples)
        elif self.method == "nli":
            return self._check_nli(prompt, original_actions, plan_func, num_samples)
        else:
            return {"risk_score": 0.0, "details": [f"unknown method: {self.method}"], "method": self.method}

    def _check_llm_prompt(
        self,
        prompt: str,
        original_actions: List[Dict[str, Any]],
        plan_func,
        num_samples: int,
    ) -> Dict[str, Any]:
        """使用 LLM-Prompt 方法进行一致性检查"""
        if not self.client or not original_actions:
            return {"risk_score": 0.0, "details": [], "method": "llm_prompt"}

        # 多次采样获得替代动作计划
        samples = []
        for _ in range(num_samples):
            try:
                sample = plan_func(prompt)
                samples.append(sample)
            except Exception:
                pass

        if not samples:
            return {"risk_score": 0.0, "details": ["无有效样本"], "method": "llm_prompt"}

        # 构造一致性检查上下文
        original_str = self._actions_to_str(original_actions)
        samples_str = "\n---\n".join(self._actions_to_str(s) for s in samples)

        consistency_prompt = (
            f"用户指令: {prompt}\n\n"
            f"原始动作计划:\n{original_str}\n\n"
            f"备选动作计划 (从相同指令重新生成):\n{samples_str}\n\n"
            f"请判断原始动作计划中的每个动作是否与备选计划一致。"
            f"对于每个原始动作，如果它在多数备选计划中也出现（设备相同、动作相同或相似），标记为 consistent。"
            f"如果某个动作在所有备选计划中都没有出现，标记为 inconsistent。"
            f"以 JSON 数组格式回复: [{{\"action_index\": 0, \"consistent\": true/false, \"reason\": \"...\"}}]"
        )

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": consistency_prompt}],
                temperature=0.1,
                max_tokens=300,
            )
            result_text = resp.choices[0].message.content.strip()
            import json
            import re
            result_text = re.sub(r'```(json)?', '', result_text).strip()
            consistency = json.loads(result_text)
        except Exception as e:
            return {"risk_score": 0.0, "details": [f"一致性检查失败: {e}"], "method": "llm_prompt"}

        inconsistent_count = sum(1 for c in consistency if not c.get("consistent", True))
        total = len(consistency) or 1
        risk_score = inconsistent_count / total
        details = [f"{c.get('reason', '')}" for c in consistency if not c.get("consistent", True)]

        return {"risk_score": risk_score, "details": details, "method": "llm_prompt", "consistency": consistency}

    def _check_nli(
        self,
        prompt: str,
        original_actions: List[Dict[str, Any]],
        plan_func,
        num_samples: int,
    ) -> Dict[str, Any]:
        """使用 NLI 方法进行一致性检查 (需要 selfcheckgpt + torch)"""
        try:
            from selfcheckgpt.modeling_selfcheck import SelfCheckNLI
            import torch

            if self._nli_model is None:
                device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                self._nli_model = SelfCheckNLI(device=device)

            # Get sample plans
            samples = []
            for _ in range(num_samples):
                try:
                    sample = plan_func(prompt)
                    samples.append(sample)
                except Exception:
                    pass

            if not samples:
                return {"risk_score": 0.0, "details": ["NLI: 无有效样本"], "method": "nli"}

            original_sentences = [self._action_to_sentence(a) for a in original_actions]
            sample_passages = [" ".join(self._action_to_sentence(a) for a in s) for s in samples]

            scores = self._nli_model.predict(
                sentences=original_sentences,
                sampled_passages=sample_passages,
            )

            risk_score = float(sum(scores) / len(scores)) if len(scores) > 0 else 0.0
            details = [f"NLI score: {s:.3f}" for s in scores]
            return {"risk_score": risk_score, "details": details, "method": "nli"}

        except ImportError:
            return {"risk_score": 0.0, "details": ["NLI 方法不可用: 缺少 selfcheckgpt/torch"], "method": "nli"}

    def _actions_to_str(self, actions: List[Dict[str, Any]]) -> str:
        if not actions:
            return "(空)"
        parts = []
        for a in actions:
            parts.append(
                f"设备={a.get('device_id','?')}, 动作={a.get('action','?')}, "
                f"参数={a.get('params',{})}, 理由={a.get('reason','')}"
            )
        return "\n".join(parts)

    def _action_to_sentence(self, action: Dict[str, Any]) -> str:
        return f"对设备 {action.get('device_id','?')} 执行 {action.get('action','?')}，因为 {action.get('reason','')}"

    @classmethod
    def is_available(cls, method: str = "llm_prompt") -> bool:
        """检查指定方法是否可用"""
        if method == "nli":
            try:
                import selfcheckgpt  # noqa
                import torch  # noqa
                return True
            except ImportError:
                return False
        return True  # llm_prompt always available if client is set
