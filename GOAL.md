# AIoT Safe Guard Goal

Objective: raise AIoT Safe Guard from an engineering prototype to a competition-grade security work benchmarked against first-prize information security projects.

## Target Outcomes

- Reproducible engineering baseline: one-command setup, health checks, seeded data, and repeatable evaluation.
- Safety evaluation corpus: 150-300 categorized cases covering normal use, prompt injection, privilege abuse, hallucination, physical bounds, interlocks, and rate abuse.
- Quantitative evaluation: per-category pass rate, false positive rate, false negative rate, blocking rate, latency, and module timing.
- Ablation experiments: compare the full system against variants with each safety layer disabled.
- Risk scoring: a documented AIoT command risk score combining input risk, device criticality, permission risk, parameter distance, interlock state, and LLM consistency.
- Demo closure: natural language input, LLM plan, layer-by-layer decision trace, risk score, execution result, device state, and audit replay.
- Version checkpoints: commit at the end of each completed stage to support rollback.

## Route

1. Build the project automation baseline.
2. Expand and run the safety evaluation dataset.
3. Add ablation switches and generate comparison results.
4. Add command risk scoring.
5. Improve frontend layer-by-layer visualization.
6. Add an MQTT/HTTP virtual device driver layer.
7. Prepare final report and presentation materials.
