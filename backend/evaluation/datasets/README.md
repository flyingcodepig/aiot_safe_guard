# Formal Safety Dataset

This directory contains the reproducible formal dataset used for AIoT Safe Guard
competition evidence.

## Splits

| Split | File | Count | Tuning Policy |
| --- | --- | ---: | --- |
| Core regression | `security_cases_core_regression.json` | 174 | Hand-audited suite; may be used for regression and fixes. |
| Development | `security_cases_dev.json` | 1000 | May be inspected during development. |
| Validation | `security_cases_validation.json` | 500 | Used for periodic system selection; avoid point fixes. |
| Final test | `security_cases_final_test.json` | 2000 | Frozen blind split; do not tune on failures used for official reporting. |
| All formal cases | `security_cases_formal_all.json` | 3674 | Aggregated file for coverage statistics. |

`security_cases_formal_manifest.json` records the generation seed, split counts,
category/threat taxonomy, freeze policy, and SHA-256 hashes for every dataset
file.

## Reporting Protocol

The 174-case expanded suite should be described as a core regression set, not as
the final evidence by itself. It is intentionally small enough to review and is
allowed to influence fixes.

For competition reporting:

1. Develop and debug on `core_regression` and `dev`.
2. Use `validation` for limited system selection and ablation sanity checks.
3. Run the final table on `final_test` only after the system is frozen.
4. If a final-test failure is inspected and used to patch the system, invalidate
   that final-test run and regenerate/report a new frozen split with a new seed.

This avoids the misleading pattern where a dataset is repeatedly tested, patched
against, and then presented as an independent final result.

## Taxonomy

Each case includes:

- `category`: broad evaluation bucket used by existing scripts.
- `threat_type`: report-facing taxonomy, including role spoofing, unauthorized
  control, hallucinated devices, wrong actions, parameter boundaries, interlock
  conflicts, rate abuse, and normal control/read requests.
- `dataset_split`, `source`, `base_case_id`, `variant_id`, `seed`,
  `text_fingerprint`, and `tuning_policy`: reproducibility and audit metadata.

Build command:

```powershell
D:\aiot_safe_guard\somethingelse\venv\Scripts\python.exe evaluation\build_formal_dataset.py --output-dir evaluation\datasets --seed 20260612 --dev-count 1000 --validation-count 500 --final-count 2000
```
