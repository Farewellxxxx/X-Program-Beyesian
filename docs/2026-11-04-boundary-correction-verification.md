# Boundary correction verification

Date: 2026-11-04 (Asia/Shanghai).

## Tests

- Nine new regression tests were observed failing before their corresponding implementation.
- Simulation, boundary, comparison and dataset-audit tests: **20 passed**.
- Full original research workspace: **20 passed, 1 failed**. The unchanged failure is `PresentationLauncherTests.test_resolve_skill_dir_discovers_installed_version_without_env_override`, caused by the missing legacy Presentations runtime. This failure was present before this repair.
- The initial default Windows sandbox temporary directory denied fixture-file access. Pointing TEMP/TMP to a workspace directory restored all six dataset-audit tests without modifying their logic.
- Standalone Git publication copy: **20 passed in 3.85 s**, using `python -m pytest -q`. The legacy presentation system is outside this publication's explicit scope.

## Regeneration

- Extended simulation: exit 0; 2,880 trials; 6 CSV + 9 PNG.
- POC: exit 0; 900 trials; 6 CSV + 9 PNG.
- Five-seed audit and sensitivity scenarios: exit 0; 80 per-run rows and 10 multiseed summary rows.
- Comparison CLI: exit 0 both in the original workspace and the standalone publication copy.
- Original 41 trial columns validated under explicit schema mapping for all 3,780 records: maximum numerical difference **0.0**.
- For all stationary audit scenarios, new canonical error equals the historical independently corrected error exactly (maximum difference **0.0**).
- All audit unacceptable-exposure and cumulative-discomfort summaries remain unchanged.

## Independent review

One fresh read-only reviewer inspected source changes against the saved pre-change source, tests, generated data, the report and figures. No actionable Critical, Important or Minor findings. Reviewer independently ran 14 simulation/comparison tests, recomputed metrics, verified unchanged trajectories and checked dynamic carryover rows and figure readability.

Publication allowlist and remote state are verified separately by the main executor. Broader surrogate validity, empirical superiority and the historical presentation environment remain outside this repair's scope.

## Publication scope

The GitHub repository includes current simulation and comparison code, synthetic outputs and baseline snapshots, audit scripts/tests, pinned dependency versions, this verification, the results report and selected research-design documents. It excludes raw participant data, original data archives, third-party papers, internal manuscript artifacts, legacy presentations, credentials and caches.

The repository is an initially empty remote. The publication is an initial commit on its existing default `main` branch; no history is overwritten and no force push is used. File checksums are recorded in `publication_manifest_sha256.csv` (the manifest itself and Git/cache metadata are excluded).

## Known limitations carried forward

The surrogate remains heuristic and potentially non-monotone; truth and belief execution models are still shared; population is fixed across process seeds; grid order and event taxonomy remain unchanged. These are documented future research tasks, not resolved by metric correction. Historical reports and internal manuscript artifacts are preserved rather than silently rewritten.
