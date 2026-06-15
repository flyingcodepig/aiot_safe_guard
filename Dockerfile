FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ /app/backend/
COPY backend/data/ /app/data/

WORKDIR /app/backend

RUN python modelload.py || echo "LLM Guard model will be downloaded on first request"

ENV ENVIRONMENT=docker

# 离线安全模式（部署环境中根据需求修改）
ENV ENABLE_LLM_PLANNER=true
ENV ENABLE_LLM_FACT_CHECKS=true
ENV ENABLE_LLM_GUARD_SCANNER=true
ENV SELFCHECK_ENABLED=true
ENV DATABASE_URL=sqlite:///./aiot_guard.db
ENV DEVICE_CONFIG_DIR=/app/data/devices

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
