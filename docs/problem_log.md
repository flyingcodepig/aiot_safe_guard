# Problem Log

This document records recurring project problems, root causes, fixes, and
verification evidence. When a similar issue appears, search this file before
debugging from scratch.

## How To Use

1. Search by symptom, module, command, or keyword.
2. Check the "Status" field before applying an old workaround.
3. Prefer the listed verification command over relying on memory.
4. If a new issue is solved, add a new entry with the same fields.

## Index

| ID | Area | Status | Short Name |
| --- | --- | --- | --- |
| P001 | evaluation | solved | Offline evaluation timeout |
| P002 | database | solved | SQLite batch instability |
| P003 | parser | solved | Unsupported action coerced into supported action |
| P004 | device gate | solved | Read request without known device |
| P005 | device gate | solved | Generic alias unsafe matching |
| P006 | parser | solved | Negative numeric parameters ignored |
| P007 | risk/audit | solved | Risk score not visible across audit surfaces |
| P008 | dataset | solved | Core suite overfitting/reporting risk |
| P009 | transport/demo | solved | Missing gateway-to-device handoff evidence |
| P010 | ablation | solved | InputGuard ablation showed no drop |
| P011 | ablation | solved | SelfCheck ablation still weak offline |
| P012 | frontend | open | Browser runtime verification not completed |
| P013 | local environment | benign | PowerShell profile warning |
| P014 | git/local files | benign | Git ignore permission warning |
| P015 | git/local files | benign | CRLF warning during diff/check |
| P016 | workspace hygiene | open | Untracked sandbox report decision |
| P017 | process | solved | Agent startup and recovery workflow not centralized |

## P001 - Offline Evaluation Timeout

Status: solved

Symptoms:
- Managed evaluation timed out or became very slow.
- Server logs showed repeated failed LLM calls in offline mode.

Root Cause:
- Evaluation still attempted remote LLM planning/fact checks or heavy scanner
  startup even when the environment had no usable model endpoint.

Resolution:
- Added offline evaluation controls for LLM planning, LLM fact checks, and LLM
  guard scanner startup.
- Added bounded request timeout support.
- Use `evaluation/run_eval_with_server.py` for repeatable offline runs.

Verification:
```powershell
cd D:\aiot_safe_guard\backend
..\somethingelse\venv\Scripts\python.exe evaluation\run_eval_with_server.py --cases evaluation\security_cases_expanded.json --output evaluation\results\latest_eval.json --request-timeout 8
```

Keywords:
`timeout`, `offline eval`, `LLM retries`, `ENABLE_LLM_PLANNER`,
`ENABLE_LLM_FACT_CHECKS`, `ENABLE_LLM_GUARD_SCANNER`.

## P002 - SQLite Batch Instability

Status: solved

Symptoms:
- Batch evaluation intermittently failed or slowed due to database contention.
- Rate-limit state could leak across repeated evaluation runs.

Root Cause:
- SQLite connections were not always closed correctly.
- Runtime state such as `rate_buckets` and `pending_confirmations` was not fully
  reset between runs.

Resolution:
- Enabled SQLite WAL/busy timeout.
- Closed rate-limit database connection correctly.
- Reset now clears `rate_buckets` and `pending_confirmations`.

Verification:
```powershell
cd D:\aiot_safe_guard\backend
..\somethingelse\venv\Scripts\python.exe evaluation\run_eval_with_server.py --cases evaluation\security_cases_expanded.json --output evaluation\results\latest_eval.json --request-timeout 8
```

Keywords:
`sqlite`, `busy_timeout`, `WAL`, `rate_buckets`, `pending_confirmations`,
`reset reproducibility`.

## P003 - Unsupported Action Coerced Into Supported Action

Status: solved

Symptoms:
- Unsupported requests such as "record on a light" could be coerced into a
  shorter supported action.

Root Cause:
- Fallback keyword matching preferred any supported keyword even when a longer
  unsupported action keyword was present.

Resolution:
- Hardened fallback action matching so unsupported actions block instead of
  being reduced to a misleading supported action.

Verification:
```powershell
cd D:\aiot_safe_guard\backend
..\somethingelse\venv\Scripts\python.exe test_device_mention.py
..\somethingelse\venv\Scripts\python.exe evaluation\evaluate_security_cases.py --cases evaluation\security_cases_expanded.json
```

Keywords:
`unsupported action`, `fallback matcher`, `wrong action`, `hallucination`.

## P004 - Read Request Without Known Device

Status: solved

Symptoms:
- Read-like requests that did not mention any known device could pass too far
  through the control flow.

Root Cause:
- The read fallback did not sufficiently distinguish device-state reads from
  generic non-device questions.

Resolution:
- Block read-like requests when no known device is mentioned and the device gate
  is enabled.

Verification:
```powershell
cd D:\aiot_safe_guard\backend
..\somethingelse\venv\Scripts\python.exe test_device_mention.py
```

Keywords:
`read fallback`, `non-device intent`, `device gate`, `hallucination`.

## P005 - Generic Alias Unsafe Matching

Status: solved

Symptoms:
- Short generic aliases such as "door" or "light" could match too broadly.

Root Cause:
- Device mention logic accepted short aliases without enough disambiguation.

Resolution:
- Tightened device mention matching so short generic aliases do not trigger
  unsafe matches.

Verification:
```powershell
cd D:\aiot_safe_guard\backend
..\somethingelse\venv\Scripts\python.exe test_device_mention.py
```

Keywords:
`alias`, `door`, `light`, `device_mentioned_in_input`,
`any_device_mentioned`.

## P006 - Negative Numeric Parameters Ignored

Status: solved

Symptoms:
- Out-of-range negative parameters were not extracted reliably.

Root Cause:
- Parameter extraction only handled unsigned numeric patterns.

Resolution:
- Added negative-number extraction before positive-number patterns.

Verification:
```powershell
cd D:\aiot_safe_guard\backend
..\somethingelse\venv\Scripts\python.exe evaluation\run_eval_with_server.py --cases evaluation\security_cases_expanded.json --output evaluation\results\latest_eval.json --ablation full no_fact_checker no_physical_checker --request-timeout 8
```

Keywords:
`negative number`, `parameter extraction`, `physical_range`, `out of bounds`.

## P007 - Risk Score Not Visible Across Audit Surfaces

Status: solved

Symptoms:
- Risk score was implemented but not consistently visible in API responses,
  action results, logs, or exports.

Root Cause:
- Risk scoring was not wired through every command/audit surface.

Resolution:
- Added response-level `risk_result`.
- Added per-action `risk_result`.
- Persisted `risk_result` in audit logs.
- Exposed it in `/api/logs` and JSON/CSV exports.

Verification:
```powershell
cd D:\aiot_safe_guard\backend
..\somethingelse\venv\Scripts\python.exe test_risk_scoring.py
```

Keywords:
`risk_result`, `audit`, `/api/logs`, `CSV export`, `JSON export`.

## P008 - Core Suite Overfitting/Reporting Risk

Status: solved

Symptoms:
- The hand-audited expanded corpus risked being treated as the only final
  evidence after iterative fixes.

Root Cause:
- No formal split separated development/regression use from frozen reporting.

Resolution:
- Added deterministic formal dataset generation.
- Split data into core regression, development, validation, and frozen
  final-test files.
- Added manifest hashes and no-tuning final-test protocol.

Verification:
```powershell
cd D:\aiot_safe_guard\backend
..\somethingelse\venv\Scripts\python.exe evaluation\build_formal_dataset.py --output-dir evaluation\datasets --seed 20260612 --dev-count 1000 --validation-count 500 --final-count 2000
..\somethingelse\venv\Scripts\python.exe evaluation\evaluate_security_cases.py --cases evaluation\datasets\security_cases_formal_all.json
```

Keywords:
`formal dataset`, `final_test`, `no tuning`, `manifest`, `overfitting`.

## P009 - Missing Gateway-To-Device Handoff Evidence

Status: solved

Symptoms:
- The project had API-level command approval and virtual state updates, but no
  visible protocol handoff from the gateway to devices.

Root Cause:
- No MQTT/HTTP-like device driver evidence existed in command responses or
  audit logs.

Resolution:
- Added simulated MQTT and HTTP device drivers.
- Returned `transport_result` for approved command execution.
- Exposed protocol handoff in command responses, audit logs, JSON/CSV exports,
  and frontend trace/replay.

Verification:
```powershell
cd D:\aiot_safe_guard\backend
..\somethingelse\venv\Scripts\python.exe test_device_driver.py
..\somethingelse\venv\Scripts\python.exe test_transport_driver_api.py
```

Keywords:
`transport_result`, `MQTT`, `HTTP`, `device_driver`, `sandbox`, `audit export`.

## P010 - InputGuard Ablation Showed No Drop

Status: solved

Symptoms:
- `no_input_guard` previously passed the same number of cases as full system.
- This made InputGuard's independent contribution weak in ablation tables.

Root Cause:
- Existing prompt-injection cases were often also blocked by RBAC, device gate,
  policy, or physical rules.

Resolution:
- Added 8 `INJECTION_ALLOWED_ACTION` cases where the underlying student action
  is otherwise allowed, but wrapped in prompt-injection language.
- Regenerated expanded and formal datasets.
- Regenerated the 11-suite evaluation report.

Verification:
```powershell
cd D:\aiot_safe_guard\backend
..\somethingelse\venv\Scripts\python.exe evaluation\run_eval_with_server.py --cases evaluation\security_cases_expanded.json --output evaluation\results\latest_eval.json --request-timeout 8
..\somethingelse\venv\Scripts\python.exe evaluation\report_eval_results.py --input evaluation\results\latest_eval.json --output evaluation\results\latest_eval.md
```

Expected Evidence:
- Full system: `174/174`.
- `no_input_guard`: `166/174`.
- The 8-case drop is concentrated in `prompt_injection`.

Keywords:
`InputGuard`, `no_input_guard`, `INJECTION_ALLOWED_ACTION`,
`prompt_injection`, `ablation`.

## P011 - SelfCheck Ablation Still Weak Offline

Status: solved

Symptoms:
- `no_selfcheck` had the same headline result as full system in the offline
  expanded evaluation.

Root Cause:
- Managed offline evaluation sets `SELFCHECK_ENABLED=false` and
  `ENABLE_LLM_PLANNER=false`, so model-backed SelfCheck rarely has a chance to
  contribute.
- Existing cases do not isolate the manual-confirmation/SelfCheck layer.

Resolution:
- Added an offline-reproducible manual-confirmation gate under the `selfcheck`
  safety layer. If the user claims "manual confirmation", "secondary approval",
  or similar prior approval for high-risk device actions, the system now creates
  its own `confirmation_token` and returns `require_confirm`.
- Added 8 `SELFCHECK_CONFIRM` cases that are otherwise authorized and physically
  safe, isolating the contribution of the SelfCheck/manual-confirmation layer.
- Updated evaluation metrics so `require_confirm` counts as a safety
  intervention while remaining distinct from direct `block`.
- Added `test_selfcheck_confirmation.py`.

Verification:
```powershell
cd D:\aiot_safe_guard\backend
..\somethingelse\venv\Scripts\python.exe test_selfcheck_confirmation.py
..\somethingelse\venv\Scripts\python.exe evaluation\run_eval_with_server.py --cases evaluation\security_cases_expanded.json --output evaluation\results\latest_eval.json --ablation full no_selfcheck --request-timeout 8
```

Expected Evidence:
- Full system: `182/182`.
- `no_selfcheck`: `174/182`.
- The 8-case drop is concentrated in `selfcheck` / `manual_confirmation`.

Remaining Note:
- A separate online/model-backed SelfCheck run is still useful later, but the
  offline ablation table now has reproducible SelfCheck/manual-confirmation
  evidence.

Keywords:
`SelfCheck`, `no_selfcheck`, `require_confirm`, `manual confirmation`,
`SELFCHECK_ENABLED`, `ENABLE_LLM_PLANNER`.

## P012 - Browser Runtime Verification Not Completed

Status: open

Symptoms:
- Frontend JavaScript parse check passed, but browser runtime verification has
  not been completed in this workspace.

Root Cause:
- Previous local server/browser startup was blocked by sandbox/process-launch
  restrictions.

Current Recommendation:
- When a local app server is available, use the Browser plugin to verify the
  demo trace visually: natural-language input, LLM plan, layer decisions, risk
  factors, transport handoff, execution result, device state, and audit replay.

Verification Target:
- Browser screenshot or visual QA notes confirming the frontend renders the full
  chain.

Keywords:
`frontend`, `browser`, `runtime verification`, `transport_result`, `audit replay`.

## P013 - PowerShell Profile Warning

Status: benign

Symptoms:
- Some shell commands print:
  `profile.ps1 cannot be loaded because running scripts is disabled`.

Root Cause:
- Local PowerShell execution policy blocks the user's profile script.

Resolution:
- Treat as shell startup noise if the command itself exits successfully.
- Do not change system execution policy unless the user explicitly asks.

Keywords:
`profile.ps1`, `Execution_Policies`, `PowerShell`, `SecurityError`.

## P014 - Git Ignore Permission Warning

Status: benign

Symptoms:
- Git commands print:
  `unable to access 'C:\Users\25446/.config/git/ignore': Permission denied`.

Root Cause:
- Git attempts to read a user-level ignore file outside the workspace.

Resolution:
- Treat as non-blocking if git status/add/commit succeeds.
- Do not edit files outside the workspace without approval.

Keywords:
`git ignore`, `.config/git/ignore`, `Permission denied`.

## P015 - CRLF Warning During Diff/Check

Status: benign

Symptoms:
- `git diff --check` prints warnings such as:
  `LF will be replaced by CRLF the next time Git touches it`.

Root Cause:
- Local Git line-ending normalization on Windows.

Resolution:
- Treat as a warning, not a whitespace failure, when `git diff --check` exits 0.
- Do not do a broad line-ending rewrite unless explicitly requested.

Keywords:
`CRLF`, `LF will be replaced`, `git diff --check`.

## P016 - Untracked Sandbox Report Decision

Status: open

Symptoms:
- `docs/sandbox_report.md` is untracked.

Root Cause:
- It is unclear whether the file is a source document to keep tracked or a local
  generated artifact.

Current Rule:
- Do not edit, delete, stage, or commit `docs/sandbox_report.md` unless the user
  explicitly requests it.

Keywords:
`sandbox_report.md`, `untracked`, `workspace hygiene`.

## P017 - Agent Startup And Recovery Workflow Not Centralized

Status: solved

Symptoms:
- Work habits such as reading handoff docs, checking the problem log, avoiding
  unrelated dirty files, and updating evidence docs were described in chat but
  not discoverable from the repository root.
- Future sessions could repeat previous investigations because the expected
  startup/debugging/recovery flow was not formalized in obvious files.

Root Cause:
- The project had `RUNBOOK.md`, `CURRENT_STATE.md`, `SESSION_LOG.md`, and this
  problem log, but no root-level agent instruction file.

Resolution:
- Added root-level `AGENTS.md` as the project workflow for AI coding agents.
- Added root-level `BOOTSTRAP.md` as the compact recovery guide for new or
  context-compacted sessions.
- The workflow requires startup state inspection, reading handoff files,
  searching `docs/problem_log.md` before debugging, scoped edits, relevant
  verification, and closeout documentation.

Verification:
```powershell
cd D:\aiot_safe_guard
Test-Path AGENTS.md
Test-Path BOOTSTRAP.md
Test-Path docs\problem_log.md
```

Keywords:
`AGENTS.md`, `BOOTSTRAP.md`, `agent workflow`, `startup checklist`,
`problem log`, `handoff docs`, `repeat debugging`, `context compaction`.
