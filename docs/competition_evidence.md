# Competition Evidence Map

## Work Definition

AIoT Safe Guard is positioned as a trusted instruction security gateway for LLM-Agent controlled AIoT systems. It sits between natural-language/agent plans and physical device execution, preventing unsafe commands before they reach devices.

It is not a generic IoT dashboard. The core security problem is that an LLM-Agent may transform user language into unsafe device control because of prompt injection, role spoofing, over-privileged requests, hallucinated devices, unsupported actions, unsafe parameters, physical conflicts, or missing audit evidence.

## Innovation Points

1. Semantic-consistency driven LLM-IoT instruction hallucination gate
   - Evidence to show: device mention gate, supported-action validation, intent consistency gate, fact checking, hallucination dataset cases.

2. RBAC and physical-constraint fused safety decision engine
   - Evidence to show: PolicyEngine, PhysicalChecker, parameter range checks, interlock checks, rate-limit checks, policy/physical ablation drops.

3. Multi-layer audit and human confirmation for AIoT control chains
   - Evidence to show: input scan result, LLM plan, parsed actions, per-layer decisions, risk score, simulated MQTT/HTTP transport result, final decision, audit export, pending confirmation records.

## Dataset Coverage

Core regression corpus: `backend/evaluation/security_cases_expanded.json`

Formal split corpus: `backend/evaluation/datasets/`

Current formal size: 3682 cases.

| Split | File | Count | Intended Use |
| --- | --- | ---: | --- |
| Core regression | `security_cases_core_regression.json` | 182 | Hand-audited regression and fix verification |
| Development | `security_cases_dev.json` | 1000 | Development and debugging |
| Validation | `security_cases_validation.json` | 500 | Periodic system selection and sanity checks |
| Final test | `security_cases_final_test.json` | 2000 | Frozen final evaluation; no tuning on official failures |
| Formal all | `security_cases_formal_all.json` | 3682 | Coverage statistics |

`security_cases_formal_manifest.json` records seed `20260612`, SHA-256 hashes,
split counts, category counts, threat taxonomy counts, and the freeze policy.
The 182-case suite should be reported as the core regression set, not as the
only final test evidence.

Required coverage mapping:

| Required Type | Current Evidence | Status |
| --- | --- | --- |
| Normal operation | `normal` category | covered |
| Prompt injection | `prompt_injection` category | covered |
| Role spoofing | `threat_type=role_spoofing` | covered |
| Unauthorized control | `privilege` category | covered |
| Hallucinated device | `hallucination` category | covered |
| Wrong/unsupported action | `threat_type=wrong_action` | covered |
| Parameter out of bounds | `physical_range` category | covered |
| Interlock conflict | `interlock` category | covered |
| Rate abuse | `rate_limit` category | covered |
| Manual confirmation | `selfcheck` category / `threat_type=manual_confirmation` | covered |

Threat-type distribution in the formal corpus:

| Threat Type | Count |
| --- | ---: |
| `normal_control` | 407 |
| `normal_read` | 71 |
| `prompt_injection` | 191 |
| `role_spoofing` | 225 |
| `audit_evasion` | 53 |
| `unauthorized_control` | 467 |
| `hallucinated_device` | 212 |
| `wrong_action` | 142 |
| `non_device_intent` | 108 |
| `parameter_out_of_bounds` | 462 |
| `interlock_conflict` | 450 |
| `rate_abuse` | 449 |
| `manual_confirmation` | 445 |

## Metrics

Implemented in `backend/evaluation/evaluate_security_cases.py` summary:

| Metric | Meaning |
| --- | --- |
| `pass_rate` | cases where actual final decision equals expected final decision |
| `block_rate` | all cases whose final decision is `block` |
| `safety_intervention_rate` | all cases whose final decision is `block` or `require_confirm` |
| `attack_interception_rate` | non-normal cases blocked or sent to manual confirmation by the system |
| `false_positive_rate` | normal cases incorrectly blocked or sent to manual confirmation |
| `false_negative_rate` | non-normal cases incorrectly allowed |
| `normal_pass_rate` | normal cases allowed |
| `avg_latency_ms` | average request latency measured by the evaluator |
| `module_timing_available` | whether backend responses include module-level timing evidence |
| `avg_module_timings_ms` | per-suite average timing for user lookup, input guard, LLM planning, parsing, device gate, intent gate, SelfCheck, fallback matching, fact checker, policy engine, physical checker, sandbox execution, risk scoring, audit logging, and total request time |

## Simulated Device Drivers

Implemented evidence:

| Layer | Evidence | Purpose |
| --- | --- | --- |
| MQTT simulation | `backend/device_driver.py` `SimulatedMqttDriver` | Models command publish to topic `aiot/{device_type}/{device_id}/command` for light/fan/instrument-like devices |
| HTTP simulation | `backend/device_driver.py` `SimulatedHttpDriver` | Models POST to a device action endpoint for alarm, door lock, and camera-like devices |
| Sandbox integration | `backend/sandbox.py` | Approved commands update virtual state and return `transport_result` for the simulated protocol hop |
| API/audit evidence | `/api/smart_command`, `/api/command`, `/api/logs`, `/api/logs/export` | Shows protocol, endpoint, method, payload, ack, and simulated latency in response/audit surfaces |
| Frontend demo trace | `backend/static/index.html` | Renders the protocol handoff in action results, audit log rows, and audit replay |

This is still a simulated driver layer, not real hardware connectivity. It
closes the demo loop enough to show the trusted gateway's final handoff without
requiring physical devices.

## Baselines

Configured profiles in `backend/evaluation/evaluate_security_cases.py`:

| Baseline | Profile | Meaning |
| --- | --- | --- |
| LLM direct execution | `baseline_llm_direct` | all safety layers disabled |
| RBAC only | `baseline_rbac_only` | only PolicyEngine remains active |
| Keyword/device gate only | `baseline_keyword_only` | local matching/device gate retained while safety decision layers are disabled |
| No physical rules | `baseline_no_physical_rules` | PhysicalChecker disabled |
| Complete system | `full` | all default layers enabled |

Note: offline evaluation disables remote LLM planning and LLM fact checks for reproducibility. A later online run should document model-backed behavior separately.

## Ablations

Configured profiles:

| Ablation | Disabled Layer |
| --- | --- |
| `no_input_guard` | InputGuard |
| `no_device_gate` | device mention gate |
| `no_fact_checker` | FactChecker |
| `no_policy_engine` | PolicyEngine |
| `no_physical_checker` | PhysicalChecker |
| `no_selfcheck` | SelfCheck confirmation gate |

Current saved expanded snapshot includes: `full`, `baseline_llm_direct`, `baseline_rbac_only`, `baseline_keyword_only`, `baseline_no_physical_rules`, `no_input_guard`, `no_device_gate`, `no_fact_checker`, `no_policy_engine`, `no_physical_checker`, `no_selfcheck`.

Latest headline results:

| Suite | Pass Rate | Safety Intervention | Attack Interception | False Positive | False Negative | Avg Latency(ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| full | 100.0% | 78.0% | 100.0% | 0.0% | 0.0% | 17.03 |
| baseline_llm_direct | 34.6% | 12.6% | 16.2% | 0.0% | 83.8% | 15.54 |
| baseline_rbac_only | 63.7% | 41.8% | 53.5% | 0.0% | 46.5% | 16.18 |
| baseline_keyword_only | 35.2% | 13.2% | 16.9% | 0.0% | 83.1% | 15.07 |
| baseline_no_physical_rules | 86.8% | 64.8% | 83.1% | 0.0% | 16.9% | 12.93 |
| no_input_guard | 95.6% | 73.6% | 94.4% | 0.0% | 5.6% | 17.31 |
| no_device_gate | 99.5% | 77.5% | 99.3% | 0.0% | 0.7% | 16.80 |
| no_fact_checker | 90.7% | 68.7% | 88.0% | 0.0% | 12.0% | 17.83 |
| no_policy_engine | 83.0% | 61.0% | 78.2% | 0.0% | 21.8% | 16.11 |
| no_physical_checker | 86.8% | 64.8% | 83.1% | 0.0% | 16.9% | 13.52 |
| no_selfcheck | 95.6% | 73.6% | 94.4% | 0.0% | 5.6% | 17.84 |

InputGuard-specific evidence: the expanded suite includes 8
`INJECTION_ALLOWED_ACTION` cases where an otherwise allowed light/fan command is
wrapped in prompt-injection language such as rule bypass or maintenance mode.
The full system blocks all 32 prompt-injection cases; `no_input_guard` passes
only 24/32 prompt-injection cases, producing the 8-case ablation drop.

SelfCheck/manual-confirmation evidence: the expanded suite includes 8
`SELFCHECK_CONFIRM` cases where a high-risk but otherwise authorized action is
wrapped in a user claim such as "manual confirmation" or "secondary approval".
The full system does not trust that text claim; it returns `require_confirm`
with a system-generated confirmation token. `no_selfcheck` allows all 8 cases,
producing the 8-case ablation drop.

Latest full-system module timing highlights:

| Module | Avg ms |
| --- | ---: |
| user_role_lookup | 3.10 |
| input_guard | 0.18 |
| fact_checker | 0.02 |
| policy_engine | 2.20 |
| physical_checker | 6.42 |
| sandbox_execution | 7.29 |
| risk_scoring | 0.04 |
| confirmation_store | 4.62 |
| audit_logging | 5.22 |
| total | 15.02 |

Next experiment gap: execute the frozen final-test split after feature freeze and
report it separately from development/regression results.

## Experiment Tables

`backend/evaluation/report_eval_results.py` renders:

- suite summary table with pass rate, safety intervention, attack interception, false positive, false negative, normal pass, and average latency
- per-category table with attack interception rate
- per-threat-type table with pass rate and attack interception rate when cases contain `threat_type`
- failed-case table
- high-risk blocked/confirmation-case table using `risk_result`
- module timing table using `avg_module_timings_ms`

Required next tables:

- frozen final-test result table once final evaluation is run
