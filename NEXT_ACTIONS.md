# Next Actions

Updated: 2026-06-12 21:40 +08:00

## Active Focus

Move from engineering features into competition evidence: frozen final-test evaluation, sharper ablations, demo trace, and report-ready tables.

## Immediate Tasks

1. Run the frozen final-test evaluation after feature freeze.
   - Target: execute `evaluation/datasets/security_cases_final_test.json` for the full system and selected baselines/ablations.
   - Important: do not tune on final-test failures used for official reporting; if inspected for fixes, regenerate/report a new frozen split with a new seed.

2. Strengthen ablation coverage.
   - Current expanded snapshot includes full, four named baselines, and six layer ablations.
   - Add sharper cases that isolate InputGuard and SelfCheck in offline and online/model-backed settings.

3. Improve the demo trace.
   - Target: frontend shows natural-language input, LLM plan, layer decisions, risk score components/top factors, execution result, device state, and audit replay.

4. Review `docs/sandbox_report.md`.
   - Target: decide whether it is a source document to keep tracked or a generated/local artifact.

## Completed This Session

- Added reproducible formal dataset generator with split metadata and `threat_type` taxonomy.
- Generated 3666 formal cases: 166 core regression, 1000 development, 500 validation, and 2000 frozen final-test.
- Added manifest hashes and dataset README with the no-tuning final-test protocol.

## Not Now

- Final report writing is intentionally deferred until the evidence pipeline is stronger.
- Do not mark the long-term goal complete until engineering reproducibility, dataset scale, ablation, risk scoring, demo closure, and audit evidence are all verified.
