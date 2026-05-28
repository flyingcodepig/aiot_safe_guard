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
SELFCHECK_ENABLED = os.getenv("SELFCHECK_ENABLED", "false").lower() == "true"
SELFCHECK_METHOD = os.getenv("SELFCHECK_METHOD", "llm_prompt")
SELFCHECK_THRESHOLD = float(os.getenv("SELFCHECK_THRESHOLD", "0.5"))
SELFCHECK_SAMPLE_COUNT = int(os.getenv("SELFCHECK_SAMPLE_COUNT", "3"))

# API 认证
API_KEY = os.getenv("API_KEY", "")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")