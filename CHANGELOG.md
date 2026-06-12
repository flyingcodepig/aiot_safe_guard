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
