# Session Bootstrap

Use this file when a new Codex session starts because context was compacted,
lost, or intentionally reset. The goal is to recover the project state from the
workspace itself, then continue the long-term competition goal without relying
on chat memory.

## One-Line Startup Prompt

```text
Please follow BOOTSTRAP.md in D:\aiot_safe_guard, inspect the current worktree,
read the required handoff files, then continue the active long-term goal. Do not
mark the goal complete unless every requirement is proven by current evidence.
```

## Startup Commands

Run these first:

```powershell
cd D:\aiot_safe_guard
git status --short --untracked-files=all
git log -1 --oneline
```

Treat the output as authoritative. If the worktree is dirty, identify which
files are part of the current task and which are unrelated or user-owned.

## Required Reading

Read these files before deciding what to do:

- `AGENTS.md`
- `GOAL.md`
- `CURRENT_STATE.md`
- `NEXT_ACTIONS.md`
- `SESSION_LOG.md`
- `RUNBOOK.md`
- `CHANGELOG.md`
- `docs/problem_log.md`
- `docs/competition_evidence.md`

If a referenced file is missing, say so and continue with the best available
evidence.

## Problem-First Rule

Before debugging a failure or repeating an investigation, search:

- `docs/problem_log.md`
- `CURRENT_STATE.md`
- `SESSION_LOG.md`
- `somethingelse/PROGRESS.md`

If a similar problem exists, reuse its resolution only after checking that it
still applies to the current code. If a new meaningful problem is solved, add or
update an entry in `docs/problem_log.md`.

## Active Long-Term Goal

Continue moving AIoT Safe Guard from engineering prototype to a
competition-grade work comparable to a first-prize information-security entry.

Primary positioning:

> 面向 LLM-Agent 控制 AIoT 的可信指令安全网关

The project must keep improving evidence for:

- reproducible engineering workflow
- formal evaluation dataset
- metrics and experiment tables
- baseline comparison
- ablation experiments
- risk scoring
- closed-loop demo
- simulated or real device handoff
- audit and manual-confirmation capability
- report/PPT/defense materials

Do not mark the long-term goal complete until every requirement is verified
against current files, commands, reports, and rendered/runtime evidence.

## Stage Work Loop

For each work stage:

1. Pick the next task from `NEXT_ACTIONS.md` and the current evidence gaps.
2. Inspect the relevant code, data, docs, and current diff before editing.
3. Make the smallest coherent change that advances the long-term goal.
4. Run the relevant verification from `RUNBOOK.md`.
5. Regenerate datasets/reports when source cases or metrics change.
6. Update handoff docs when evidence, counts, results, or known problems change.
7. Leave unrelated dirty files untouched.
8. Commit only coherent verified checkpoints when requested or appropriate.

## Stage Review

At the end of every meaningful stage, perform a comparison review before
stopping.

Compare the current AIoT Safe Guard work against:

- `GOAL.md`
- `NEXT_ACTIONS.md`
- `CURRENT_STATE.md`
- `docs/competition_evidence.md`
- `docs/problem_log.md`
- this `BOOTSTRAP.md`
- the external competition-report benchmark provided by the user:
  `D:\XAS\资料准备\信安赛作品报告.pdf`

The PDF is the benchmark document for "what a complete competition work/report
should look like." At each stage review, compare the current project evidence
against that report's expected standard, including work definition, problem
framing, innovation points, architecture, dataset, metrics, baseline comparison,
ablation experiments, result tables, demo evidence, audit/safety analysis,
engineering reproducibility, limitations, and defense/report material.

If the PDF is accessible in the current environment, inspect it directly before
making a detailed comparison. If it is not accessible, say so clearly and fall
back to the documented project goals and competition evidence map.

Review questions:

- What requirement was advanced in this stage?
- What evidence proves it?
- Which commands/tests/reports were run?
- Compared with `D:\XAS\资料准备\信安赛作品报告.pdf`, which report/work
  sections are now stronger, still weak, or missing?
- Which competition gaps remain before this project can match that benchmark?
- Did any new problem appear that belongs in `docs/problem_log.md`?
- Did any dataset count, metric, or ablation result change?
- Are there untracked or dirty files that must be called out?
- Is the long-term goal still active?

Record the review outcome in the normal handoff files when the stage changes
project state:

- `SESSION_LOG.md`
- `CURRENT_STATE.md`
- `NEXT_ACTIONS.md`
- `CHANGELOG.md` if behavior, data, or evidence changed
- `docs/competition_evidence.md` if competition evidence changed
- `docs/problem_log.md` if a new recurring issue or workaround was found

## Standard Verification Menu

Use the relevant subset, not necessarily every command every time:

```powershell
cd D:\aiot_safe_guard\backend
..\somethingelse\venv\Scripts\python.exe -m py_compile audit.py database.py main.py models.py risk_scoring.py test_risk_scoring.py
..\somethingelse\venv\Scripts\python.exe test_selfcheck_confirmation.py
..\somethingelse\venv\Scripts\python.exe test_device_mention.py
..\somethingelse\venv\Scripts\python.exe test_risk_scoring.py
..\somethingelse\venv\Scripts\python.exe test_device_driver.py
..\somethingelse\venv\Scripts\python.exe test_transport_driver_api.py
```

Evaluation/report commands:

```powershell
cd D:\aiot_safe_guard\backend
..\somethingelse\venv\Scripts\python.exe evaluation\build_expanded_cases.py
..\somethingelse\venv\Scripts\python.exe evaluation\build_formal_dataset.py --output-dir evaluation\datasets --seed 20260612 --dev-count 1000 --validation-count 500 --final-count 2000
..\somethingelse\venv\Scripts\python.exe evaluation\run_eval_with_server.py --cases evaluation\security_cases_expanded.json --output evaluation\results\latest_eval.json --request-timeout 8
..\somethingelse\venv\Scripts\python.exe evaluation\report_eval_results.py --input evaluation\results\latest_eval.json --output evaluation\results\latest_eval.md
```

Finish with:

```powershell
git diff --check
git status --short --untracked-files=all
```

## Files To Treat Carefully

- Do not edit, delete, stage, or commit `docs/sandbox_report.md` unless the user
  explicitly requests it.
- Treat files under `backend/evaluation/results/` as generated artifacts unless
  they are intentionally saved evidence.
- Review risk-scoring related files before changing them:
  - `backend/risk_scoring.py`
  - `backend/test_risk_scoring.py`
  - `backend/models.py`
  - `backend/database.py`
  - `backend/audit.py`
  - `backend/main.py`

## Closeout Response

When finishing a stage, summarize:

- changed files
- verification run and result
- latest checkpoint commit, if one was made
- remaining gaps
- intentionally untouched untracked files

Keep the goal active unless completion is proven requirement by requirement.
