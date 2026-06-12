# Current State

Updated: 2026-06-12 20:35 +08:00

## Branch And Checkpoint

- Branch: `codex-aiot-award-automation`
- Last stable commit: `b93a9fe feat: stabilize evaluation automation`
- Goal status: active, not complete

## Working Tree

Known modified files:

- `.gitignore`
- `CHANGELOG.md`
- `backend/database.py`
- `backend/device_loader.py`
- `backend/evaluation/results/latest_eval.json`
- `backend/evaluation/run_eval_with_server.py`
- `backend/llm_planner.py`
- `backend/main.py`
- `backend/test_device_mention.py`

Known untracked files:

- `backend/evaluation/build_expanded_cases.py`
- `backend/evaluation/report_eval_results.py`
- `backend/evaluation/results/latest_eval.md`
- `backend/evaluation/security_cases_expanded.json`
- `docs/sandbox_report.md`

Volatile local artifacts under `backend/evaluation/results/` are ignored except intentionally saved JSON reports.

## Verified So Far

- Python compile check passed for modified backend and evaluation files.
- `backend/test_device_mention.py` passed.
- Offline dataset summary detected 166 expanded cases across seven categories.
- Uvicorn can start with offline-friendly evaluation environment.
- `/health` returns 200 when the evaluation wrapper starts the backend.
- Managed offline evaluation now completes without timeout.
- `evaluation/results/latest_eval.json`: expanded full 166/166; no input guard 166/166; no device gate 165/166; no policy engine 135/166; no physical checker 142/166.
- `evaluation/results/latest_eval.md` contains Markdown tables for report reuse.

## Known Problems

- Input-guard and device-gate ablations need sharper isolating cases; current expanded suite shows the clearest drops for policy and physical layers.
- Offline evaluation disables LLM planning and LLM fact checks; a separate online/model-backed evaluation should be added later.
- `docs/sandbox_report.md` is currently untracked and should be reviewed before any cleanup or commit decision.

## Process Rule

At the end of each substantial session, update `SESSION_LOG.md`, `NEXT_ACTIONS.md`, and this file. Commit only coherent, verified checkpoints.
