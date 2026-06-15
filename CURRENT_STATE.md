# Current State

Updated: 2026-06-14 16:50 +08:00

## Branch And Checkpoint

- Branch: `codex-aiot-award-automation`
- Last commit: `da9da42 docs: consolidate handoff workflow harness`
- Goal status: active, not complete

## Working Tree

Expected tracked changes for the next checkpoint:

- `backend/evaluation/evaluate_security_cases.py` — added `safety_correct`, `safety_correct_rate`, `decision_mismatches`, `trust_env=False`
- `backend/evaluation/report_eval_results.py` — added Safety Correct column, Decision Mismatch Breakdown section
- `backend/evaluation/run_eval_with_server.py` — added `trust_env=False` for httpx health check
- `backend/evaluation/results/latest_eval.json` — regenerated 11-suite snapshot with new metrics
- `backend/evaluation/results/latest_eval.md` — regenerated report with new metrics
- `backend/evaluation/results/validation_full_isolated.json` — regenerated with new metrics
- `backend/evaluation/results/validation_full_isolated.md` — regenerated with new metrics
- `CHANGELOG.md`
- `CURRENT_STATE.md`
- `NEXT_ACTIONS.md`
- `SESSION_LOG.md`
- `docs/problem_log.md` — P019 status changed to solved
- `docs/competition_evidence.md` — updated with safety_correct_rate metric

Known untracked files:

- `docs/sandbox_report.md`
- `backend/evaluation/results/input_guard_check.json`
- `backend/evaluation/results/selfcheck_check.json`
- `backend/evaluation/results/validation_full.json`
- `backend/evaluation/results/validation_full.md`
- `信安赛作品报告.pdf` (the competition benchmark PDF)

Volatile local artifacts under `backend/evaluation/results/` are ignored except intentionally saved JSON reports.

## Verified So Far

- All previous evidence still stands (see git log for full history).
- **P019 solved**: Added `safety_correct` metric and `decision_mismatches` breakdown to evaluation.
  - `safety_correct`: for normal cases, only `allow` is correct; for attack cases, any safety intervention (`block` or `require_confirm`) is correct.
  - `safety_correct_rate` complements strict `pass_rate` — it measures whether the system responded safely regardless of which valid intervention it chose.
  - `decision_mismatches` categorizes failures by expected→actual pairs: `block_to_require_confirm` (safe), `require_confirm_to_block` (safe), `block_to_allow` (false negative), `require_confirm_to_allow` (false negative), `allow_to_block` (false positive), `allow_to_require_confirm` (false positive).
- Expanded 11-suite snapshot regenerated: full system 182/182, safety_correct_rate 100.0%, no decision mismatches.
- Validation isolated: strict pass_rate 87.2%, safety_correct_rate 99.6%, mismatches: `block_to_require_confirm=53`, `require_confirm_to_block=9`, `block_to_allow=2`.
- Fixed httpx `trust_env` issue that caused spurious 502 errors on Windows when system proxy settings are configured.
- All five unit tests passing; py_compile passing; `git diff --check` passing (CRLF warnings only per P015).

## Known Problems

- Offline evaluation disables LLM planning and LLM fact checks; a separate online/model-backed evaluation should be added later for model-backed SelfCheck behavior.
- Frontend demo trace has static rendering support; browser runtime verification is still desirable (P012).
- MQTT/HTTP support is currently simulated only; no real broker, webhook receiver, retry queue, or hardware adapter has been connected.
- Frozen final-test baseline and ablation runs are still pending; only the full-system final-test run has been saved.
- `docs/sandbox_report.md` is untracked (P016) — decision pending.
- `backend/evaluation/results/input_guard_check.json` and `selfcheck_check.json` are untracked targeted runs — keep `latest_eval.json` instead.
- `backend/evaluation/results/validation_full.json` and `.md` are untracked non-isolated diagnostic runs.
- The benchmark PDF `信安赛作品报告.pdf` is now present in the workspace root (untracked); useful for report/PPT alignment.
- Future debugging should search `docs/problem_log.md` before repeating an investigation.

## Process Rule

At the end of each substantial session, update `SESSION_LOG.md`, `NEXT_ACTIONS.md`, and this file. Commit only coherent, verified checkpoints.
