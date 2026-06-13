# Current State

Updated: 2026-06-13 13:37 +08:00

## Branch And Checkpoint

- Branch: `codex-aiot-award-automation`
- Last stable commit before this checkpoint: `96bd68a docs: add recurring problem log`
- Goal status: active, not complete

## Working Tree

Known modified files:

- `CURRENT_STATE.md`
- `GOAL.md`
- `NEXT_ACTIONS.md`
- `SESSION_LOG.md`
- `RUNBOOK.md`
- `backend/main.py`
- `backend/evaluation/build_expanded_cases.py`
- `backend/evaluation/build_formal_dataset.py`
- `backend/evaluation/evaluate_security_cases.py`
- `backend/evaluation/report_eval_results.py`
- `backend/evaluation/datasets/*.json`
- `backend/evaluation/datasets/README.md`
- `backend/evaluation/results/latest_eval.json`
- `backend/evaluation/results/latest_eval.md`
- `backend/evaluation/security_cases_expanded.json`
- `backend/test_selfcheck_confirmation.py`
- `CHANGELOG.md`
- `docs/competition_evidence.md`
- `docs/problem_log.md`

Known untracked files:

- `docs/sandbox_report.md`
- `backend/evaluation/results/input_guard_check.json`
- `backend/evaluation/results/selfcheck_check.json`

Volatile local artifacts under `backend/evaluation/results/` are ignored except intentionally saved JSON reports.

## Verified So Far

- Python compile check passed for risk-scoring integration files.
- `backend/test_device_mention.py` passed.
- `backend/test_risk_scoring.py` passed.
- API check confirmed `risk_result` appears in `/api/smart_command`, each smart `action_result`, `/api/logs`, JSON export, and CSV export.
- Offline dataset summary detected 182 expanded cases across eight categories.
- Uvicorn can start with offline-friendly evaluation environment.
- `/health` returns 200 when the evaluation wrapper starts the backend.
- Managed offline evaluation now completes without timeout.
- `evaluation/results/latest_eval.json`: expanded full 182/182; no input guard 174/182; no device gate 181/182; no fact checker 165/182; no policy engine 151/182; no physical checker 158/182; no selfcheck 174/182.
- InputGuard ablation now has isolated evidence: 8 `INJECTION_ALLOWED_ACTION` prompt-injection cases are blocked by the full system and allowed when InputGuard is disabled.
- SelfCheck/manual-confirmation ablation now has isolated evidence: 8 `SELFCHECK_CONFIRM` cases return `require_confirm` in the full system and are allowed when SelfCheck is disabled.
- `evaluation/results/latest_eval.md` contains Markdown tables for report reuse.
- Risk scoring now covers input risk, device criticality, permission risk, parameter boundaries, physical/interlock state, and model consistency.
- Smart-command responses include overall `risk_result`; every `action_result` includes its own `risk_result`; audit logs persist `risk_result`.
- Project goal has been re-scoped in `GOAL.md` as a trusted instruction security gateway for LLM-Agent controlled AIoT.
- Added `docs/competition_evidence.md` to map work definition, three innovation points, dataset coverage, metrics, baselines, ablations, and experiment-table gaps.
- Evaluation summaries now include block rate, normal pass rate, attack interception rate, false positive rate, false negative rate, and average latency.
- Added named baseline profiles: `baseline_llm_direct`, `baseline_rbac_only`, `baseline_keyword_only`, and `baseline_no_physical_rules`.
- Latest generated experiment table covers 11 suites: full, four baselines, and six ablations.
- Backend smart-command responses now include `timings_ms` for user lookup, input guard, LLM planning, parsing, device gate, intent gate, SelfCheck, fallback matching, fact checker, policy engine, physical checker, sandbox execution, risk scoring, audit logging, and total request time.
- Evaluation summaries aggregate `avg_module_timings_ms`; `evaluation/results/latest_eval.md` now includes a Module Timing table.
- Headline full-system result: 182/182, 100.0% attack interception, 78.0% safety intervention, 0.0% false positive, 0.0% false negative, 17.03 ms average evaluator latency, 15.02 ms average backend total timing.
- Added a formal split dataset under `backend/evaluation/datasets/`: 182 core regression, 1000 development, 500 validation, and 2000 frozen final-test cases.
- Formal dataset metadata now includes `threat_type`, `dataset_split`, `source`, `base_case_id`, `variant_id`, `seed`, `text_fingerprint`, and `tuning_policy`.
- `security_cases_formal_manifest.json` records seed `20260612`, split/category/threat counts, freeze policy, and SHA-256 hashes.
- Evaluation results now preserve and summarize `threat_type`; `evaluation/results/latest_eval.md` includes a Threat Type Breakdown table.
- Added simulated MQTT/HTTP device drivers. Approved commands now return `transport_result` with protocol, endpoint, method, payload, simulated ack, and latency.
- `transport_result` is exposed in direct command responses, smart-command action results, `/api/logs`, and JSON/CSV log export.
- Frontend demo trace now renders the protocol handoff in smart-command action results, the audit log table, and audit replay.
- Frontend JavaScript parse check passed with Node after adding transport rendering.
- Formal all dataset summary now reports 3682 cases: 478 normal/allow cases, 2759 block cases, and 445 `require_confirm` cases.
- Current verification passed: py_compile for backend/evaluation files; `test_selfcheck_confirmation.py`; `test_device_mention.py`; `test_risk_scoring.py`; `test_device_driver.py`; `test_transport_driver_api.py`; `git diff --check` passed with only CRLF warnings.
- Added `docs/problem_log.md` as the durable issue/resolution index for recurring failures and workarounds.
- Added root-level `AGENTS.md` and `BOOTSTRAP.md` so new sessions know to read handoff docs and search the problem log before debugging.

## Known Problems

- Offline evaluation disables LLM planning and LLM fact checks; a separate online/model-backed evaluation should be added later for model-backed SelfCheck behavior.
- Frontend demo trace has static rendering support for risk score, component factors, action-level risk, simulated MQTT/HTTP transport, and audit replay; browser runtime verification is still desirable.
- MQTT/HTTP support is currently simulated only; no real broker, webhook receiver, retry queue, or hardware adapter has been connected.
- Frozen final-test split has been regenerated and format-checked, but has not yet been executed against the backend after feature freeze.
- `docs/sandbox_report.md` is currently untracked and should be reviewed before any cleanup or commit decision.
- `backend/evaluation/results/input_guard_check.json` is an untracked targeted run; current recommendation is to keep the full `latest_eval.json` instead of committing this scratch artifact.
- `backend/evaluation/results/selfcheck_check.json` is an untracked targeted run; current recommendation is to keep the full `latest_eval.json` instead of committing this scratch artifact.
- Future debugging should search `docs/problem_log.md` before repeating an investigation.

## Process Rule

At the end of each substantial session, update `SESSION_LOG.md`, `NEXT_ACTIONS.md`, and this file. Commit only coherent, verified checkpoints.
