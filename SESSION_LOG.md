# Session Log

## 2026-06-12 19:58 +08:00

- Added project handoff structure to prevent chat-context dependency.
- Current focus is stabilizing the evaluation loop and recording repeatable evidence for ablation experiments.
- Confirmed the evaluation wrapper starts the backend and reaches `/health`.
- Confirmed the previous real evaluation run timed out after processing several cases; logs show repeated failed LLM calls in offline mode.
- Next engineering step: bound per-case request time and avoid slow offline LLM retries where possible.

## 2026-06-12 20:18 +08:00

- Added offline evaluation controls for LLM planning and LLM-backed fact checks.
- Fixed SQLite batch-evaluation stability by enabling WAL/busy timeout and closing the rate-limit database connection correctly.
- Added summary-only output for managed evaluation while keeping full JSON snapshots on disk.
- Hardened fallback matching so unsupported actions such as recording on a light are blocked instead of coerced into a shorter supported action.
- Blocked read-like requests that mention no known device when the device gate is enabled.
- Low-privilege sensitive operations now hard-block instead of entering confirmation.
- Verification: full core suite passed 20/20; latest three-suite ablation snapshot generated successfully.

## 2026-06-12 20:35 +08:00

- Added `evaluation/build_expanded_cases.py` and generated a 166-case expanded corpus.
- Added `evaluation/report_eval_results.py` and generated `evaluation/results/latest_eval.md`.
- Fixed reset reproducibility by clearing `rate_buckets` and `pending_confirmations`.
- Tightened device mention matching to avoid short generic aliases matching unknown doors/lights.
- Added negative-number parameter extraction for physical boundary tests.
- Updated device mention regression tests to the safer matching semantics.
- Verification: expanded full suite passed 166/166; five-suite ablation snapshot generated successfully.

## 2026-06-12 20:56 +08:00

- Added explainable command risk scoring with components for input risk, device criticality, permission risk, parameter boundaries, physical/interlock state, and model consistency.
- Wired `risk_result` into direct command responses, smart-command overall responses, every smart `action_result`, audit log persistence, `/api/logs`, and JSON/CSV log export.
- Added regression tests for low-risk commands, permission-blocked door unlocks, out-of-range parameters, and overall score aggregation.
- Verified the risk audit surface with an in-process FastAPI check covering `/api/smart_command`, `/api/logs`, and `/api/logs/export`.
- Verification: py_compile passed; `test_device_mention.py` passed; `test_risk_scoring.py` passed; expanded five-suite ablation run completed with full 166/166, no input guard 166/166, no device gate 165/166, no policy engine 135/166, no physical checker 142/166.

## 2026-06-12 21:11 +08:00

- Re-scoped `GOAL.md` to position the project as a trusted instruction security gateway for LLM-Agent controlled AIoT, with seven competition evidence requirements.
- Added `docs/competition_evidence.md` covering the core problem, three named innovation points, dataset coverage, metrics, baselines, ablations, and missing evidence.
- Extended evaluation summaries with block rate, normal pass rate, attack interception rate, false positive rate, false negative rate, average latency, and module timing availability.
- Added named baseline profiles: `baseline_llm_direct`, `baseline_rbac_only`, `baseline_keyword_only`, and `baseline_no_physical_rules`.
- Regenerated `evaluation/results/latest_eval.json` and `evaluation/results/latest_eval.md` for 11 suites: full, four baselines, and six ablations.
- Added static frontend rendering support for risk summaries, per-action risk components, and audit replay modal.
- Verification: evaluation script py_compile passed; expanded dataset summary remains 166 cases; managed evaluation completed successfully; frontend JavaScript parsed successfully with Node. Browser runtime verification was attempted but local server startup was blocked by this sandbox's process-launch restrictions.

## 2026-06-12 21:29 +08:00

- Added smart-command `timings_ms` for user lookup, input guard, planning, parsing, device gate, intent gate, SelfCheck, fallback matching, fact checker, policy engine, physical checker, sandbox execution, risk scoring, audit logging, and total request time.
- Aggregated per-suite `avg_module_timings_ms` in `evaluation/evaluate_security_cases.py`.
- Added a Module Timing table to `evaluation/report_eval_results.py` and regenerated `evaluation/results/latest_eval.md`.
- Updated `docs/competition_evidence.md` with module timing evidence; remaining evidence gap is dataset taxonomy tagging.
- Verification: py_compile passed; `test_device_mention.py` passed; `test_risk_scoring.py` passed; TestClient confirmed `timings_ms`; managed 11-suite evaluation completed with module timing available.
