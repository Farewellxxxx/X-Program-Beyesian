# Adaptive execution implementation plan

> Execute inline with TDD and one final independent whole-branch reviewer.

**Goal:** Select execution complexity and propagate mean/covariance/model uncertainty; validate small-budget overfit/coverage, compare outcomes and publish.
**Spec:** docs/superpowers/specs/2026-11-04-adaptive-execution-design.md.
**Architecture:** Independent conjugate core, posterior execution adapter, new audit/strict comparison modules; old code paths and result archives preserved.
**Stack:** Python/NumPy/pandas/matplotlib/pytest; explicitly add installed SciPy 1.13.1.

## Constraints and review focus

- Only ordered calibration observations and public settings enter posterior inference/RNG; altered hidden truth must not change estimates/draws.
- Validate NIG/IW parameterization, covariance orientation, normalized monotonic prior/posterior evidence, and joint rather than marginal posterior sampling.
- All posterior draws must be monotone with SPD covariances; no projection masquerading as posterior sampling. Stable handling of zero residuals, invalid/rank-deficient data and bounded rejection failure.
- Scalar and vector predictive laws must agree; predictive mean/variance must include coefficient uncertainty and use the same epistemic/aleatoric decomposition as the diagnostics.
- Missing entire scenario/variant/grid, wrong model settings/seed/draw hash, nonnested calibration or corrupted fits must fail comparison. Alternative CLI surrogates must not overwrite Bayesian outputs.
- Separate independent coverage, width and proper score; distinguish execution ablations from full feedback runs and prior sensitivity from population replication.

## Tasks

- [ ] 1. Core: create simulation/execution_posterior.py and tests/test_execution_posterior.py. RED independent conjugate/evidence fixtures, constraint-probability numerical check, joint posterior moments, deterministic prefixes, invalid inputs and no-truth leakage. Implement and run full suite; commit.
- [ ] 2. Adapter and diagnostics: create simulation/adaptive_execution.py, simulation/execution_predictive_diagnostics.py, tests/test_adaptive_execution.py. RED mixture moments/variance, immutable state, scalar/vector/time effects, fixed trajectories, independent holdout score and CLI metadata/path isolation. Add CLI mode and pinned dependency; full suite and commit.
- [ ] 3. Audit/comparison: create scripts/run_adaptive_execution_audit.py, scripts/compare_adaptive_execution.py, tests/test_adaptive_execution_audit.py. Preserve 280 configs/observations and old replay; six diagnostic variants, numerical sensitivity; strict complete manifests/fit recomputation guards and cluster contrasts. RED→GREEN; full suite; commit.
- [ ] 4. Run 280 adaptive +280 current-version replays, six-variant diagnostics, 14 predeclared sensitivity cells and extended/POC. Produce CSV/JSON/PNG, Chinese methods/results/verification, inspect figures, explain regressions/remaining limits. Commit verified artifacts.
- [ ] 5. One independent read-only review, one TDD fix pass if needed; final checks and archive hashes, original-workspace mirror, main fast-forward/push and independent remote SHA confirmation.

## Interfaces

Task 1: PosteriorSettings, RegressionPosterior, PosteriorComponent, ExecutionPosterior, fit_regression(design,response,prior_sd,settings), monotone_probability(mean,scale,df,degree,span), fit_execution_posterior(observations,public_settings,posterior_settings=...).
Task 2: PosteriorExecutionModel(public_settings,posterior,mode), mode in quadratic_plugin/adaptive_plugin/quadratic_posterior/adaptive_posterior; prepare_adaptive_execution(config,observations=None,...), upgrade_prepared(prepared,...); predictive_diagnostics(prepared,seed,n_samples=4096) preserves original fields and adds independently evaluated interval coverage/score/width.
Task 3: reuse prior RobustnessSpec unchanged; new manifest includes posterior settings/variants; same calibration and trajectory fingerprints. Separate run, fit, participant, population, calibration, diagnostic records and sensitivity manifest. Full comparison uses declared scenario counts; no weak partial joins.

## Ledger

- Setup: clean main 33e0123; isolated .publish checkout reused on feature/adaptive-execution-posterior, no AGENTS.md found. Current published suite is 81 tests.
- Ruling: user explicitly requests implementation, validation and GitHub push; preserve the authorized inline workflow without an extra permission round. The model/prior choices here are implementation decisions, not choices attributed to the user.
- Ruling: Bayesian model averaging supplies soft complexity selection and model-choice uncertainty; report MAP degree but do not collapse predictions to it. Cost if inappropriate: prior-sensitive under/over-selection, explicitly measured by the fixed sensitivity check.
- Ruling: full feedback experiments compare complete new/old methods; isolate complexity/uncertainty using the six-variant execution diagnostics. Do not claim feedback-level causal attribution from those ablations.
- Ruling: preserve old default CLI behavior and provide explicit adaptive_posterior mode with distinct paths. Freeze all existing results; add only synthetic records and documentation.
