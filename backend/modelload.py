# preload_models.py
from llm_guard.input_scanners import PromptInjection, Toxicity
from llm_guard.output_scanners import FactualConsistency

# 初始化扫描器，触发模型下载
PromptInjection()
Toxicity()
FactualConsistency()
print("所有 LLM Guard 模型已下载完毕。")
