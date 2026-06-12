# Current State

Updated: 2026-06-12 20:56 +08:00

## Branch And Checkpoint

- Branch: `codex-aiot-award-automation`
- Last stable commit before this session: `29f6368 feat: expand safety evaluation corpus`
- Goal status: active, not complete

## Working Tree

Known modified files:

- `CHANGELOG.md`
- `CURRENT_STATE.md`
- `NEXT_ACTIONS.md`
- `RUNBOOK.md`
- `SESSION_LOG.md`
- `backend/audit.py`
- `backend/database.py`
- `backend/evaluation/results/latest_eval.json`
- `backend/main.py`
- `backend/models.py`

Known untracked files:

- `backend/risk_scoring.py`
- `backend/test_risk_scoring.py`
- `docs/sandbox_report.md`

Volatile local artifacts under `backend/evaluation/results/` are ignored except intentionally saved JSON reports.

## Verified So Far

- Python compile check passed for risk-scoring integration files.
- `backend/test_device_mention.py` passed.
- `backend/test_risk_scoring.py` passed.
- API check confirmed `risk_result` appears in `/api/smart_command`, each smart `action_result`, `/api/logs`, JSON export, and CSV export.
- Offline dataset summary detected 166 expanded cases across seven categories.
- Uvicorn can start with offline-friendly evaluation environment.
- `/health` returns 200 when the evaluation wrapper starts the backend.
- Managed offline evaluation now completes without timeout.
- `evaluation/results/latest_eval.json`: expanded full 166/166; no input guard 166/166; no device gate 165/166; no policy engine 135/166; no physical checker 142/166.
- `evaluation/results/latest_eval.md` contains Markdown tables for report reuse.
- Risk scoring now covers input risk, device criticality, permission risk, parameter boundaries, physical/interlock state, and model consistency.
- Smart-command responses include overall `risk_result`; every `action_result` includes its own `risk_result`; audit logs persist `risk_result`.

## Known Problems

- Input-guard and device-gate ablations need sharper isolating cases; current expanded suite shows the clearest drops for policy and physical layers.
- Offline evaluation disables LLM planning and LLM fact checks; a separate online/model-backed evaluation should be added later.
- Frontend/demo trace still needs to render risk score, component factors, and audit replay clearly.
- `docs/sandbox_report.md` is currently untracked and should be reviewed before any cleanup or commit decision.

## Process Rule

At the end of each substantial session, update `SESSION_LOG.md`, `NEXT_ACTIONS.md`, and this file. Commit only coherent, verified checkpoints.
