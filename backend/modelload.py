"""模型预加载 — 首次运行时下载 LLM Guard 模型，避免请求时卡顿"""
from llm_guard.input_scanners import PromptInjection
from llm_guard.output_scanners import FactualConsistency

PromptInjection()
FactualConsistency()
print("LLM Guard 模型已就绪。")
