# Next Actions

Updated: 2026-06-12 21:29 +08:00

## Active Focus

Move from engineering features into competition evidence: definition, innovations, dataset taxonomy, metrics, baselines, ablations, and experiment tables.

## Immediate Tasks

1. Add dataset taxonomy tags.
   - Target: add `threat_type` or equivalent metadata so role spoofing and wrong-action hallucination can be reported directly.

2. Strengthen ablation coverage.
   - Current expanded snapshot includes full, four named baselines, and six layer ablations.
   - Add sharper cases that isolate InputGuard and SelfCheck in offline and online/model-backed settings.

3. Improve the demo trace.
   - Target: frontend shows natural-language input, LLM plan, layer decisions, risk score components/top factors, execution result, device state, and audit replay.

4. Review `docs/sandbox_report.md`.
   - Target: decide whether it is a source document to keep tracked or a generated/local artifact.

## Not Now

- Final report writing is intentionally deferred until the evidence pipeline is stronger.
- Do not mark the long-term goal complete until engineering reproducibility, dataset scale, ablation, risk scoring, demo closure, and audit evidence are all verified.
