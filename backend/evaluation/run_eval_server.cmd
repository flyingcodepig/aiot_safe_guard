@echo off
set OPENAI_API_KEY=dummy-for-offline-eval
set LLM_BASE_URL=http://127.0.0.1:9
set LLM_MODEL=offline-eval
set SELFCHECK_ENABLED=false
set ENABLE_LLM_GUARD_SCANNER=false
set ENABLE_LLM_PLANNER=false
set ENABLE_LLM_FACT_CHECKS=false
set LLM_TIMEOUT_SECONDS=0.5
set LLM_MAX_RETRIES=0
set DATABASE_URL=sqlite:///./evaluation/results/eval_aiot_guard.db
set DEVICE_CONFIG_DIR=./data/devices
cd /d "%~dp0.."
"..\somethingelse\venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8000
