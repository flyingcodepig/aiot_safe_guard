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
