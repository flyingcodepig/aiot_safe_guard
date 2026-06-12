# Next Actions

Updated: 2026-06-12 20:35 +08:00

## Active Focus

Move from expanded evaluation evidence into risk scoring and demo trace quality.

## Immediate Tasks

1. Add command risk scoring.
   - Target: documented score using input risk, device criticality, permission risk, parameter distance, interlock state, and model consistency.
   - Include the score in smart-command responses and audit logs.

2. Improve the demo trace.
   - Target: frontend shows natural-language input, LLM plan, layer decisions, risk score, execution result, device state, and audit replay.

3. Strengthen ablation coverage.
   - Current expanded snapshot: full, no input guard, no device gate, no policy engine, no physical checker.
   - Add interpretable cases that isolate input guard and device gate more strongly.
   - Later include no intent gate, no fact checker, and no selfcheck when online/model-backed evaluation is available.

4. Review `docs/sandbox_report.md`.
   - Target: decide whether it is a source document to keep tracked or a generated/local artifact.

## Not Now

- Final report writing is intentionally deferred until the evidence pipeline is stronger.
- Do not mark the long-term goal complete until engineering reproducibility, dataset scale, ablation, risk scoring, demo closure, and audit evidence are all verified.
