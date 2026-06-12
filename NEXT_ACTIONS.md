# Next Actions

Updated: 2026-06-12 20:18 +08:00

## Active Focus

Expand the evidence base beyond the 20-case core suite and start turning the engineering pipeline into competition-grade quantitative evaluation.

## Immediate Tasks

1. Expand the evaluation dataset.
   - Current core set: 20 cases in `backend/evaluation/security_cases_core.json`.
   - Target for competition-grade evidence: 150-300 categorized cases.
   - Add adversarial natural-language variants, boundary values, multi-device commands, role confusion, and state-dependent interlocks.

2. Add command risk scoring.
   - Target: documented score using input risk, device criticality, permission risk, parameter distance, interlock state, and model consistency.

3. Improve the demo trace.
   - Target: frontend shows natural-language input, LLM plan, layer decisions, risk score, execution result, device state, and audit replay.

4. Add evaluation reporting helpers.
   - Target: summarize `evaluation/results/latest_eval.json` into Markdown tables for the future report.

5. Review `docs/sandbox_report.md`.
   - Target: decide whether it is a source document to keep tracked or a generated/local artifact.

## Not Now

- Final report writing is intentionally deferred until the evidence pipeline is stronger.
- Do not mark the long-term goal complete until engineering reproducibility, dataset scale, ablation, risk scoring, demo closure, and audit evidence are all verified.
