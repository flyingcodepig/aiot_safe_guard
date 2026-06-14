# Next Actions

Updated: 2026-06-14 16:05 +08:00

## Active Focus

Move from corrected formal full-system evidence into selected final-test baseline/ablation reporting, `block`/`require_confirm` decision-boundary cleanup, frontend/browser demo verification, and report/PPT-ready material.

## Master Workstreams

1. Work definition and competition narrative.
   - Position the project as a trusted instruction safety gateway for LLM-Agent controlled AIoT, not a generic IoT console.
   - Keep the core problem, threat model, and three named innovation points aligned across docs, demo, report, and PPT.

2. Core safety gateway capability.
   - Maintain InputGuard, device/intent gate, FactChecker, PolicyEngine, PhysicalChecker, SelfCheck/manual confirmation, risk scoring, and audit export as one coherent control chain.
   - Keep `risk_result`, `timings_ms`, action-level decisions, and audit evidence visible in API responses and logs.

3. Simulated device and protocol loop.
   - Keep the virtual device state, simulated MQTT/HTTP handoff, `transport_result`, and device-state update path demonstrable end to end.
   - Optional later extension: fake MQTT broker/webhook receiver, retry/failure simulation, and driver-failure safety tests.

4. Formal evaluation dataset.
   - Maintain the 182-case core regression suite and the 3682-case formal split corpus.
   - Preserve dev/validation/final-test separation and the no-tuning final-test protocol.
   - Preserve the sharpened InputGuard and SelfCheck/manual-confirmation cases.

5. Metrics and experiment system.
   - Keep pass rate, block rate, attack interception, false positive, false negative, normal pass rate, per-category rate, per-threat-type rate, latency, and module timing in generated outputs.
   - Ensure high-risk blocked cases and representative failure cases are reportable.

6. Baselines and ablations.
   - Maintain LLM direct, RBAC-only, keyword/device-gate-only, no-physical-rules, and full-system baselines.
   - Maintain layer ablations for InputGuard, device gate, FactChecker, PolicyEngine, PhysicalChecker, and SelfCheck.
   - Run the final baseline/ablation tables on the frozen final-test split after feature freeze.

7. Advanced presentation UI.
   - Upgrade the frontend from a basic Bootstrap admin page into a polished security-operation style demo console.
   - Show the complete chain: natural-language command, LLM plan, parsed action, layer decisions, risk factors, simulated MQTT/HTTP handoff, device state, audit replay, and evaluation/ablation evidence.
   - Add a guided demo mode or curated scenario entry points for judges.

8. Engineering reproducibility and delivery.
   - Keep one-command or clearly documented startup, smoke test, evaluation, report generation, and dataset regeneration paths.
   - Keep RUNBOOK, environment variables, dataset manifest, and result locations current.
   - Avoid hidden dependencies on chat history or local-only state.

9. Report, PPT, and defense materials.
   - Produce final report sections for work definition, threat model, architecture, innovations, dataset, metrics, baselines, ablations, latency, high-risk cases, audit chain, and limitations.
   - Produce PPT outline/slides, architecture diagrams, experiment tables, screenshots, demo script, and likely Q&A.

## Immediate Tasks

1. Tighten formal split decision semantics without violating no-tuning protocol.
   - Current isolated frozen final-test full-system result is 1735/2000, with 99.09% attack interception and 0.0% false positives.
   - Remaining failures are mostly `block` vs `require_confirm`; use core/dev/validation data for fixes or label-policy decisions.
   - If final-test failures are inspected for tuning, regenerate/report a new frozen split with a new seed.

2. Run selected frozen final-test baselines/ablations.
   - Full-system final-test run is complete and saved in `evaluation/results/final_test_full.json`/`.md`.
   - Use `--reset-each-case` for formal split runs.
   - Run selected baselines/ablations on final-test after deciding the reporting subset, because each full-system final-test pass expands to 4750 smart-command requests.

3. Runtime-check the demo trace.
   - Target: open the frontend against a running backend and visually verify natural-language input, LLM plan, layer decisions, risk score components/top factors, simulated MQTT/HTTP transport, execution result, device state, and audit replay.

4. Review `docs/sandbox_report.md`.
   - Target: decide whether it is a source document to keep tracked or a generated/local artifact.

5. Decide whether to keep `backend/evaluation/results/input_guard_check.json`.
   - Current recommendation: treat it as a temporary targeted run because `latest_eval.json` now contains the full 11-suite evidence.

## Completed This Session

- Added reproducible formal dataset generator with split metadata and `threat_type` taxonomy.
- Generated 3674 formal cases: 174 core regression, 1000 development, 500 validation, and 2000 frozen final-test.
- Added manifest hashes and dataset README with the no-tuning final-test protocol.
- Added evaluation/report support for `threat_type` breakdown tables.
- Added simulated MQTT/HTTP device drivers and exposed `transport_result` through command responses and audit export.
- Added frontend rendering for the simulated transport hop in action results, audit log rows, and audit replay.
- Added 8 `INJECTION_ALLOWED_ACTION` cases that wrap otherwise allowed student actions in prompt-injection language.
- Regenerated the expanded suite to 174 cases and the formal split corpus to 3674 cases.
- Regenerated `latest_eval.json`/`.md`: full system 174/174; `no_input_guard` 166/174 with all 8 regressions in `prompt_injection`.
- Re-ran py_compile, device mention, risk scoring, device driver, transport driver API, and `git diff --check`.
- Added offline-reproducible SelfCheck/manual-confirmation gate for high-risk actions where the user claims prior approval.
- Added 8 `SELFCHECK_CONFIRM` cases and regenerated the expanded suite to 182 cases and the formal split corpus to 3682 cases.
- Updated metrics and Markdown reports to count `require_confirm` as a safety intervention distinct from direct `block`.
- Regenerated `latest_eval.json`/`.md`: full system 182/182; `no_selfcheck` 174/182 with all 8 regressions in `selfcheck`.
- Added and ran `test_selfcheck_confirmation.py`.
- Ran frozen final-test for the full system only: 1667/2000 passed, 99.09% attack interception, 27.2% false positive, 0.91% false negative.
- Generated `evaluation/results/final_test_full.json` and `evaluation/results/final_test_full.md`.
- Added `--reset-each-case` for randomized formal split evaluation after diagnosing cross-case state leakage with validation data.
- Re-ran isolated core, validation, and final-test full-system evidence: core 182/182, validation 436/500, final-test 1735/2000 with 0.0% false positive.
- Consolidated cheap-model handoff workflow, long-term goal contract, and command harness into `BOOTSTRAP.md`, `AGENTS.md`, and `RUNBOOK.md`.

## Remaining Driver Work

- Browser runtime verification should be run when the local app server is available.
- Optional later extension: add a fake MQTT broker/webhook receiver, retry/failure simulation, and driver-failure safety tests.

## Not Now

- Final report writing is intentionally deferred until the evidence pipeline is stronger.
- Do not mark the long-term goal complete until engineering reproducibility, dataset scale, ablation, risk scoring, demo closure, and audit evidence are all verified.
