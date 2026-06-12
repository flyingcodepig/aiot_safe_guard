"""系统配置加载"""
import os
from dotenv import load_dotenv

load_dotenv()

IS_DOCKER = os.getenv("ENVIRONMENT", "") == "docker"

# 数据库路径
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aiot_guard.db")

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# 设备配置文件目录
DEVICE_CONFIG_DIR = os.getenv(
    "DEVICE_CONFIG_DIR",
    "/app/data/devices" if IS_DOCKER else "./data/devices"
)

# 服务器端口
PORT = int(os.getenv("PORT", 8000))

# SelfCheckGPT 配置
SELFCHECK_ENABLED = os.getenv("SELFCHECK_ENABLED", "true").lower() == "true"
SELFCHECK_METHOD = os.getenv("SELFCHECK_METHOD", "llm_prompt")
SELFCHECK_THRESHOLD = float(os.getenv("SELFCHECK_THRESHOLD", "0.5"))
SELFCHECK_SAMPLE_COUNT = int(os.getenv("SELFCHECK_SAMPLE_COUNT", "3"))

# Safety layer defaults for ablation experiments.
ENABLE_INPUT_GUARD = os.getenv("ENABLE_INPUT_GUARD", "true").lower() == "true"
ENABLE_DEVICE_GATE = os.getenv("ENABLE_DEVICE_GATE", "true").lower() == "true"
ENABLE_INTENT_GATE = os.getenv("ENABLE_INTENT_GATE", "true").lower() == "true"
ENABLE_FACT_CHECKER = os.getenv("ENABLE_FACT_CHECKER", "true").lower() == "true"
ENABLE_POLICY_ENGINE = os.getenv("ENABLE_POLICY_ENGINE", "true").lower() == "true"
ENABLE_PHYSICAL_CHECKER = os.getenv("ENABLE_PHYSICAL_CHECKER", "true").lower() == "true"
ENABLE_SELFCHECK_GATE = os.getenv("ENABLE_SELFCHECK_GATE", "true").lower() == "true"
ENABLE_LLM_GUARD_SCANNER = os.getenv("ENABLE_LLM_GUARD_SCANNER", "true").lower() == "true"
ENABLE_LLM_PLANNER = os.getenv("ENABLE_LLM_PLANNER", "true").lower() == "true"
ENABLE_LLM_FACT_CHECKS = os.getenv("ENABLE_LLM_FACT_CHECKS", "true").lower() == "true"
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "10"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "0"))

# API 认证
API_KEY = os.getenv("API_KEY", "")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
