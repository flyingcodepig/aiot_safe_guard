# Runbook

This file is the restart guide for a new session. Read it together with `GOAL.md`, `NEXT_ACTIONS.md`, `CURRENT_STATE.md`, and `CHANGELOG.md`.

## Inspect State

```powershell
cd D:\aiot_safe_guard
git status --short
git branch --show-current
git log -1 --oneline
```

## Backend Smoke Checks

```powershell
cd D:\aiot_safe_guard\backend
..\somethingelse\venv\Scripts\python.exe -m py_compile audit.py database.py main.py models.py risk_scoring.py test_risk_scoring.py
..\somethingelse\venv\Scripts\python.exe test_device_mention.py
..\somethingelse\venv\Scripts\python.exe test_risk_scoring.py
..\somethingelse\venv\Scripts\python.exe test_device_driver.py
..\somethingelse\venv\Scripts\python.exe test_transport_driver_api.py
```

## Dataset Summary

```powershell
cd D:\aiot_safe_guard\backend
..\somethingelse\venv\Scripts\python.exe evaluation\evaluate_security_cases.py
..\somethingelse\venv\Scripts\python.exe evaluation\evaluate_security_cases.py --cases evaluation\security_cases_expanded.json
```

## Regenerate Expanded Dataset

```powershell
cd D:\aiot_safe_guard\backend
..\somethingelse\venv\Scripts\python.exe evaluation\build_expanded_cases.py
```

## Regenerate Formal Split Dataset

```powershell
cd D:\aiot_safe_guard\backend
..\somethingelse\venv\Scripts\python.exe evaluation\build_formal_dataset.py --output-dir evaluation\datasets --seed 20260612 --dev-count 1000 --validation-count 500 --final-count 2000
..\somethingelse\venv\Scripts\python.exe evaluation\evaluate_security_cases.py --cases evaluation\datasets\security_cases_formal_all.json
```

Use `core_regression` and `dev` for fixes, `validation` for limited system
selection, and `final_test` only for frozen final reporting. If final-test
failures are inspected and used for fixes, regenerate/report a new final split
with a new seed.

## Run Offline Evaluation With Managed Server

```powershell
cd D:\aiot_safe_guard\backend
..\somethingelse\venv\Scripts\python.exe evaluation\run_eval_with_server.py --cases evaluation\security_cases_expanded.json --output evaluation\results\latest_eval.json --ablation full no_input_guard no_device_gate no_policy_engine no_physical_checker
```

The wrapper starts uvicorn, waits for `/health`, runs the evaluation, prints a summary, writes the full JSON, and stops the server.

Use `--print-full-json` when the full response body is needed in terminal output.

## Run Competition Baselines And Ablations

```powershell
cd D:\aiot_safe_guard\backend
..\somethingelse\venv\Scripts\python.exe evaluation\run_eval_with_server.py --cases evaluation\security_cases_expanded.json --output evaluation\results\latest_eval.json --request-timeout 8
..\somethingelse\venv\Scripts\python.exe evaluation\report_eval_results.py --input evaluation\results\latest_eval.json --output evaluation\results\latest_eval.md
```

Default suites now include:

- `full`
- `baseline_llm_direct`
- `baseline_rbac_only`
- `baseline_keyword_only`
- `baseline_no_physical_rules`
- `no_input_guard`
- `no_device_gate`
- `no_fact_checker`
- `no_policy_engine`
- `no_physical_checker`
- `no_selfcheck`

The Markdown report includes pass rate, attack interception, false positive, false negative, normal pass rate, average latency, per-category tables, failed cases, and high-risk blocked cases.
It also includes a Threat Type Breakdown table when cases/results include `threat_type`, plus a Module Timing table derived from smart-command `timings_ms` and suite-level `avg_module_timings_ms`.

For post-freeze reporting on the formal final split, replace `--cases
evaluation\security_cases_expanded.json` with `--cases
evaluation\datasets\security_cases_final_test.json`. Expect a longer run because
the final split contains 2000 cases, including repeated rate-limit cases.

Current expected generated counts with seed `20260612`: 174 core regression,
1000 development, 500 validation, 2000 final-test, and 3674 formal-all cases.

## Check Risk Score Audit Surface

```powershell
cd D:\aiot_safe_guard\backend
$env:ENABLE_LLM_PLANNER='false'
$env:ENABLE_LLM_FACT_CHECKS='false'
$env:ENABLE_LLM_GUARD_SCANNER='false'
$env:ENABLE_SELFCHECK_GATE='false'
$env:SELFCHECK_ENABLED='false'
$env:DATABASE_URL='sqlite:///./aiot_guard_api_check.db'
```

Then use `fastapi.testclient.TestClient` to send `/api/smart_command` and verify:

- response-level `risk_result`
- per-action `risk_result`
- `/api/logs` `risk_result`
- `/api/logs/export?format=json` `risk_result`
- `/api/logs/export?format=csv` `risk_result` header/field

## Check Simulated Driver Surface

```powershell
cd D:\aiot_safe_guard\backend
..\somethingelse\venv\Scripts\python.exe test_device_driver.py
..\somethingelse\venv\Scripts\python.exe test_transport_driver_api.py
```

Approved command responses should expose `transport_result` in each executed
action. Audit logs and JSON/CSV export should also include `transport_result`.
The current drivers are simulated:

- MQTT-like devices publish to `aiot/{device_type}/{device_id}/command`.
- HTTP-like devices POST to `http://simulated-device-bus.local/devices/{device_id}/actions`.
- No real MQTT broker, webhook server, retry queue, or hardware adapter is required for this evidence layer.

## Render Evaluation Tables

```powershell
cd D:\aiot_safe_guard\backend
..\somethingelse\venv\Scripts\python.exe evaluation\report_eval_results.py --input evaluation\results\latest_eval.json --output evaluation\results\latest_eval.md
```

## Manual Evaluation Server

```powershell
cd D:\aiot_safe_guard
backend\evaluation\run_eval_server.cmd
```

Then, in another terminal:

```powershell
cd D:\aiot_safe_guard\backend
..\somethingelse\venv\Scripts\python.exe evaluation\evaluate_security_cases.py --base-url http://127.0.0.1:8000 --output evaluation\results\latest_eval.json --ablation full
```

## Session Closeout

1. Stop any backend process started for evaluation.
2. Update `SESSION_LOG.md`.
3. Update `NEXT_ACTIONS.md`.
4. Update `CURRENT_STATE.md`.
5. Run the smallest relevant verification command.
6. Commit only a coherent checkpoint.
