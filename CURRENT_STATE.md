# Current State

Updated: 2026-06-12 20:18 +08:00

## Branch And Checkpoint

- Branch: `codex-aiot-award-automation`
- Last stable commit: `93a90fd feat: add safety layer ablation controls`
- Goal status: active, not complete

## Working Tree

Known modified files:

- `.gitignore`
- `CHANGELOG.md`
- `backend/config.py`
- `backend/database.py`
- `backend/evaluation/evaluate_security_cases.py`
- `backend/fact_checker.py`
- `backend/input_guard.py`
- `backend/llm_planner.py`
- `backend/main.py`
- `backend/physical_checker.py`

Known untracked files:

- `NEXT_ACTIONS.md`
- `CURRENT_STATE.md`
- `SESSION_LOG.md`
- `RUNBOOK.md`
- `CHECKPOINTS.md`
- `backend/evaluation/run_eval_server.cmd`
- `backend/evaluation/run_eval_with_server.py`
- `backend/evaluation/results/latest_eval.json`
- `docs/sandbox_report.md`

Volatile local artifacts under `backend/evaluation/results/` are ignored except intentionally saved JSON reports.

## Verified So Far

- Python compile check previously passed for backend files.
- `backend/test_device_mention.py` passed.
- Offline dataset summary detected 20 cases across the core categories.
- Uvicorn can start with offline-friendly evaluation environment.
- `/health` returns 200 when the evaluation wrapper starts the backend.
- Managed offline evaluation now completes without timeout.
- `evaluation/results/latest_eval.json`: full 20/20, no policy engine 18/20, no physical checker 17/20.

## Known Problems

- The evidence dataset is still too small for a first-prize-level claim.
- Offline evaluation disables LLM planning and LLM fact checks; a separate online/model-backed evaluation should be added later.
- `docs/sandbox_report.md` is currently untracked and should be reviewed before any cleanup or commit decision.

## Process Rule

At the end of each substantial session, update `SESSION_LOG.md`, `NEXT_ACTIONS.md`, and this file. Commit only coherent, verified checkpoints.
