# Changelog

## Unreleased

- Consolidated non-core workspace materials into `somethingelse/`.
- Added a long-term improvement goal for competition-grade development.
- Added a recurring two-day review automation in Codex.
- Added backend health check and audit log export/filtering.
- Wired `DATABASE_URL`, `DEVICE_CONFIG_DIR`, and `SELFCHECK_SAMPLE_COUNT` into runtime behavior.
- Added frontend edit support for policy and physical-rule management.
- Added a core safety evaluation dataset and runner under `backend/evaluation/`.
- Added request-level safety-layer ablation switches and evaluation runner support for named ablation suites.
- Added `ENABLE_LLM_GUARD_SCANNER` so offline evaluation can skip heavy PromptInjection model startup while keeping it enabled by default.
- Added offline evaluation controls for LLM planning/fact-checking and bounded request timeouts.
- Fixed SQLite evaluation stability with WAL/busy timeout and a rate-limit connection leak fix.
- Hardened fallback action matching against unsupported-action hallucinations and blocked read-like requests that mention no known device.
- Generated a repeatable three-suite ablation snapshot: full, no policy engine, and no physical checker.
- Added a generated 166-case expanded safety corpus with balanced category coverage.
- Added Markdown evaluation reporting for direct report/table reuse.
- Fixed reset reproducibility by clearing rate-limit buckets and pending confirmations during `/api/reset`.
- Tightened device mention matching so short generic aliases such as "door" or "light" do not trigger unsafe device matches.
- Added explainable AIoT command risk scoring across input risk, device criticality, permission risk, parameter boundaries, physical/interlock state, and model consistency.
- Returned `risk_result` from `/api/smart_command`, each smart `action_result`, and direct `/api/command` responses.
- Persisted `risk_result` in audit logs and exposed it through `/api/logs` plus JSON/CSV `/api/logs/export`.
- Re-scoped the project goal as a trusted instruction security gateway for LLM-Agent controlled AIoT.
- Added a competition evidence map covering the work definition, three named innovation points, dataset coverage, metrics, baselines, ablations, and experiment-table gaps.
- Added competition metrics to evaluation summaries: block rate, normal pass rate, attack interception rate, false positive rate, false negative rate, and average latency.
- Added named baseline profiles for LLM direct execution, RBAC-only, keyword/device-gate-only, and no-physical-rules comparisons.
- Regenerated the expanded experiment snapshot and Markdown report for full system, four baselines, and six ablations.
- Added backend `timings_ms` evidence for smart-command safety stages and aggregated `avg_module_timings_ms` in evaluation reports.
- Added a Module Timing table to the generated Markdown experiment report.
- Added a reproducible formal safety dataset generator with core, development, validation, and frozen final-test splits.
- Generated a 3666-case formal dataset with 2000 frozen final-test cases, threat-type taxonomy, split metadata, SHA-256 manifest, and reporting protocol documentation.
