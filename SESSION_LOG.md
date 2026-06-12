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
