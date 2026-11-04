# Flexible execution estimator implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline, TDD, and one final independent whole-branch review.

**Goal:** Fit gain/nonlinearity/full residual covariance from execution observations, rerun paired budget tests, explain limits, publish.
**Architecture:** Separate fitted execution module and adapter; explicit CLI estimator selector; separate new audit/comparison using frozen prior fixtures.
**Tech Stack:** Existing Python/NumPy/pandas/matplotlib/pytest; no dependency changes.
**Spec:** `docs/superpowers/specs/2026-11-04-flexible-execution-design.md`.

## Global constraints / review focus

- Baseline 9679123, isolated publication checkout, branch feature/flexible-execution-estimator. Original folder mirrored only after validation.
- No generator coefficients, profile labels, passenger truth or diagnostic draws in fitting; prove same observations yield same belief under altered truth.
- Correct full residual covariance and matching scalar/vector distributions; validate an asymmetric covariance example, not only the synthetic one-rho family.
- Minimum eight interior observations, full-rank design, finite SPD covariance and global command monotonicity; exercise both endpoint constraints and zero-noise degeneracy.
- Exact same calibration observations/streams/budgets and fixed-policy trajectories across models. Missing whole cells, modified seeds/observations or mixed estimator settings must fail comparison.
- Small budgets and broader model capacity may worsen results; report all profiles, error/exposure tradeoffs, predictive undercoverage and remaining model-family restrictions.

## Tasks

- [x] 1. Create `simulation/flexible_execution.py` and `long_horizon_audit/tests/test_flexible_execution.py`. RED tests for independent coefficient/covariance fixtures, constraints, invalid inputs, sampler moments and truth isolation; implement immutable model, fit, upgrade adapter; full suite and commit.
- [x] 2. Add explicit extended/POC `--execution-estimator` integration and fit exports. Create `run_flexible_execution_audit.py`, `compare_flexible_execution.py`, tests for exact paired design, outputs, prefix/hash identity, parameter/config mismatch and missing cells. RED-to-GREEN, full suite, commit.
- [ ] 3. Run 280 new scenarios + 420 baseline replays and new-model extended/POC; compare with old archive and produce complete CSV/JSON/PNG plus Chinese result/verification reports. Inspect figures, document benefits and regressions without post-hoc retuning.
- [ ] 4. One independent review, one verified fix pass if needed, final tests/hashes/workspace sync, main fast-forward and authorized push, remote SHA verification.

## Interfaces

- Task 1: `FitSettings` fixed defaults, `FlexibleParameters` coefficients/covariance, `fit_flexible_execution(observations,settings,fit_settings=...) -> FlexibleFit`, `FlexibleExecutionModel`, `upgrade_prepared(prepared,fit_settings=...)`, `prepare_flexible_execution(config,observations=None,fit_settings=...)`.
- Task 2: optional `execution_estimator='simple'` run_configurations/default_output_dir argument; audit consumes original RobustnessSpec and changes only estimator identity. Existing Config and legacy metadata remain unchanged for exact replay.
- Task 3: comparison consumes complete manifests and calibration/diagnostic records; archive originals are immutable.

## Ledger

- Setup: clean main 9679123, no AGENTS.md found. Existing .publish clone provides isolation from the original research folder; retain this workflow on a feature branch.
- Ruling: user explicitly authorized implementation, experiments and push; proceed with documented method choices without a separate permission round. Use the current inline workflow and one final reviewer.
- Ruling: keep original default commands reproducible and make the richer estimator explicit via CLI; model complexity can hurt small budgets, so do not silently replace all historical/default assumptions before evidence.
- Pre-flight: model adapter changes belief and its metadata only; historical Config/manifests and physical RNG paths stay unchanged. Audit uses the same observations, diagnostic namespace and population-batch statistical units as the previous study.

- Task 1: baseline 63 tests passed; 11 new numerical/isolation tests first failed for the missing module. After implementation, one deliberately decreasing fixture exceeded physical acceleration bounds; corrected its intercept (1.2 to 0.9) without changing the constraint case. Final full suite: 74 passed. No outcome-based model tuning.

- Task 2: five new integration/integrity tests first failed for absent CLI/scripts; implemented explicit selector, immutable study manifests, exact observation hashes, fit recomputation guards and historical replay checks. Full suite: 79 passed. All 280 calibration designs fit without dropped scenarios. Native PowerShell/Python verification is used in place of the skill shell helper.

- Task 3 progress: all 280 new scenarios and 3780 extended/POC trials completed. All new manifests, observations, fits and diagnostics validated. Tables/plots and Chinese interpretation generated; original 420-scenario replay remains running. New whole-suite run: 79 passed (21.70 s under concurrent audit). Four main figures and three representative example figures inspected; regenerated plots are byte-identical and all coverage-series ordinates match the CSV means.
- Ruling: overlap the single independent read-only review of completed implementation/new-model results with deterministic old-version replay. Final comparison, publication hashes, workspace sync and push remain gated on all 420 replays; review does not replace that gate.
