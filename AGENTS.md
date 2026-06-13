# Agent Workflow

This repository uses this file as the project-level workflow for AI coding
agents. Read it before making assumptions or edits.

## Startup Checklist

1. Inspect the current workspace:
   - `git status --short --untracked-files=all`
   - `git log -1 --oneline`

2. Read the handoff files:
   - `GOAL.md`
   - `NEXT_ACTIONS.md`
   - `CURRENT_STATE.md`
   - `SESSION_LOG.md`
   - `RUNBOOK.md`
   - `CHANGELOG.md`
   - `docs/competition_evidence.md`
   - `docs/problem_log.md`

3. Treat the current worktree as authoritative. Previous chat context can help
   locate work, but it is not proof of current state.

## Problem-First Debugging

Before investigating a failure, search `docs/problem_log.md` by symptom,
module, command, and keyword.

If the issue is already listed:

1. Check its status.
2. Reuse the documented resolution only if it still fits the current code.
3. Run the listed verification command or a stronger equivalent.

If a meaningful new issue is solved, update `docs/problem_log.md` with:

- symptom
- root cause
- affected files or modules
- resolution
- verification command
- future search keywords

## Work Policy

- Make changes that move the project toward the long-term goal: a
  competition-grade trusted instruction security gateway for LLM-Agent
  controlled AIoT.
- Keep edits scoped to the task and the surrounding code.
- Do not modify unrelated dirty files.
- Do not edit, delete, stage, or commit `docs/sandbox_report.md` unless the
  user explicitly asks.
- Treat `backend/evaluation/results/input_guard_check.json` as a scratch
  targeted evaluation artifact unless the user decides to keep it.
- Review risk-scoring related files before changing them:
  - `backend/risk_scoring.py`
  - `backend/test_risk_scoring.py`
  - `backend/models.py`
  - `backend/database.py`
  - `backend/audit.py`
  - `backend/main.py`

## Evidence Workflow

For dataset, metric, baseline, ablation, risk scoring, demo, or audit work:

1. Review the current diff and relevant implementation.
2. Add or adjust focused cases only when they isolate a real layer or behavior.
3. Regenerate datasets when source cases change.
4. Run the relevant evaluation.
5. Generate Markdown reports from JSON results.
6. Run focused tests plus `git diff --check`.
7. Update handoff/evidence docs with the new numbers.
8. Commit only coherent verified checkpoints when requested or appropriate.

## Standard Verification

Use the relevant subset of:

```powershell
cd D:\aiot_safe_guard\backend
..\somethingelse\venv\Scripts\python.exe -m py_compile audit.py database.py main.py models.py risk_scoring.py test_risk_scoring.py
..\somethingelse\venv\Scripts\python.exe test_selfcheck_confirmation.py
..\somethingelse\venv\Scripts\python.exe test_device_mention.py
..\somethingelse\venv\Scripts\python.exe test_risk_scoring.py
..\somethingelse\venv\Scripts\python.exe test_device_driver.py
..\somethingelse\venv\Scripts\python.exe test_transport_driver_api.py
```

For evaluation evidence:

```powershell
cd D:\aiot_safe_guard\backend
..\somethingelse\venv\Scripts\python.exe evaluation\run_eval_with_server.py --cases evaluation\security_cases_expanded.json --output evaluation\results\latest_eval.json --request-timeout 8
..\somethingelse\venv\Scripts\python.exe evaluation\report_eval_results.py --input evaluation\results\latest_eval.json --output evaluation\results\latest_eval.md
```

Always finish with:

```powershell
git diff --check
git status --short --untracked-files=all
```

## Closeout

At the end of substantial work:

1. Update `SESSION_LOG.md`.
2. Update `NEXT_ACTIONS.md`.
3. Update `CURRENT_STATE.md`.
4. Update `CHANGELOG.md` when behavior, data, or evidence changes.
5. Mention remaining untracked files and whether they were intentionally left
   alone.
6. Do not mark the long-term goal complete unless every requirement is proven
   by current evidence.
