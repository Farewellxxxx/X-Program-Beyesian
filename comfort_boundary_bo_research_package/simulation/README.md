# Continuous-command synthetic simulation

Current revision: **2026-11-04 regularized quadratic execution and full residual covariance**. Synthetic passengers only. The response model remains Bayesian; the acquisition score remains heuristic.

See the [new estimator results](../../docs/2026-11-04-flexible-execution-results.md), [method and limitations](../../docs/2026-11-04-flexible-execution-method.md), [previous robustness results](../../docs/2026-11-04-execution-robustness-results.md), [execution/population report](../../docs/2026-11-04-execution-population-results.md), [Bayesian model report](../../docs/2026-11-04-monotone-bayes-results.md) and [earlier boundary correction](../../docs/2026-11-04-boundary-correction-results.md).

## Entry points

- `run_uncertain_input_bo_extended.py`: 24 synthetic passengers × 12 trials × 5 policies × 2 noise levels; defaults to `outputs_execution_separated/`.
- `run_uncertain_input_bo_poc.py`: 18 synthetic passengers × 10 trials × 5 policies; defaults to `outputs_execution_separated_poc/`.
- `../../long_horizon_audit/scripts/run_execution_population_audit.py`: independent nested population/process experiments, matched fixed-population controls, historical replay and execution-misspecification stress test.
- `../../long_horizon_audit/scripts/compare_execution_population.py`: validates complete configurations and pairing, computes intervals over independent population batches, and plots current comparisons.
- `../../long_horizon_audit/scripts/run_multiseed_simulation_audit.py`: five process seeds plus six sensitivity scenarios. Specify `--output-dir`; optionally `--surrogate legacy_kernel`.
- `compare_surrogates.py`: reads the committed/rebuilt new and legacy audit paths, runs same-history replay, checks grid resolution and prior sensitivity, and writes `../../results/monotone_bayes_20261104/`.
- `compare_boundary_results.py`: historical metric-correction comparison, still uses the preserved legacy snapshots.

Both entry points accept `--execution-estimator simple|quadratic_covariance`, `--surrogate`, `--execution-belief calibrated|nominal|oracle`, `--process-rng-mode independent|legacy`, `--population-seed`, `--calibration-seed`, `--calibration-trials`, `--true-execution-bias`, `--assumed-execution-bias`, `--assumed-execution-noise-scale` and `--output-dir`. Only `oracle` plus `legacy` RNG selects the old Bayesian/kernel output paths; independent-stream runs use new directories. Keep historical directories for their original settings.

## Flexible execution estimator

Use `--execution-estimator quadratic_covariance` with calibrated belief to fit bias, gain, quadratic curvature and full standardized acceleration/conditional-jerk/duration residual covariance. This writes `outputs_flexible_execution/` or `_poc/` plus `continuous_execution_fit.csv`. The historical default remains `simple`; oracle and nominal are not accepted with the new fitting selector. All new summary tables retain estimator identity, fit-settings fingerprint and fitted parameters. `belief_execution_noise_scale` is only a compatibility scalar `sqrt(trace(covariance)/3)` in this mode; use the six `fit_cov_*` entries for the actual distribution.

`flexible_execution.py` implements observation-only fitting, immutable settings/parameters, a globally nondecreasing acceleration mean and Cholesky sampling. Fixed prior SDs are (0.50,0.50,0.75), off-diagonal shrinkage is 3/n and the covariance floor is 1e-8. Require eight uncensored records, full design rank and condition number at most 1e8. These constants were fixed before the audit. Coefficient/covariance uncertainty is not propagated. Conditional jerk/duration means, base heteroscedastic shapes and intensity mapping remain known; this is not arbitrary dynamics identification or a temporal-noise model.

`../../long_horizon_audit/scripts/run_flexible_execution_audit.py --workers 8` adds 280 fitted-model scenarios and replays all 420 old scenarios, with the same nested calibration observations and random roots. Use `--suite flexible|replay` and `--profile` for separate groups. `compare_flexible_execution.py` requires the complete declared grid, exact old replay, matching calibration values/hashes, recomputed fits, fixed-policy trajectories and independent diagnostic grids; it writes `../../results/flexible_execution_20261104/`. The `estimator` column labels the old pipeline as `simple`; its `oracle`/`nominal` arms retain their explicitly distinct information assumptions. See the linked report for error/exposure tradeoffs and small-budget regressions.

## Execution information and random streams

The separate `execution_misspecification.py` module adds synthetic gain/quadratic mean changes and correlated standardized residuals. `../../long_horizon_audit/scripts/run_execution_robustness_audit.py` runs seven profiles × six belief/budget arms × five population batches × two process repeats (420 scenarios), plus 55 original-schedule replay scenarios. Its full oracle knows the true distortion; nominal/calibrated beliefs keep the original two-parameter family. Existing CLI defaults and archived outputs are unchanged. `run_scenario(..., prepared=None)` permits this explicit audit injection.

Budgets 8/20/40/160 share exact prefixes of a base-2 radical-inverse command sequence in the central 20%-80% range, independent of feedback. Independent holdout diagnostics use namespace `0xD1A6`, command index and calibration root seed, with 4096 draws at each of 21 full-range commands. True/belief draws deliberately share innovations within each diagnostic comparison. This differs from the original sorted linspace calibration schedule; replay and schedule effects are reported separately. Comparison rejects incomplete grids, metadata mismatches, changed prefixes and fixed-policy inconsistencies, and uses population-batch intervals.

`execution_belief.py` contains immutable public settings and execution parameters, plus a weighted bias/common-noise calibration fit that receives only command, acceleration, jerk and duration observations. Calibration uses 40 independent simulated maneuvers per execution condition/seed; it uses no passenger labels. Commands cover the central 20%-80% of the public range. Observations at realized clipping bounds are excluded and counted. The known functional form and clipping approximation are limitations, not learned vehicle dynamics.

The physical model and policy belief are separate objects. `PolicySettings` omits truth and seed fields; policy history is an explicit observable-field projection. `oracle` is the only mode intentionally supplied true execution parameters. `calibrated` uses a plug-in fit; `nominal` uses explicit assumed parameters. Neither propagates execution-parameter uncertainty or learns online.

`population_seed` controls passenger attributes, `seed` (exported as `process_seed`) controls policy/execution/feedback streams, and `calibration_seed` controls a separate `SeedSequence([seed, 0xCA1B])`. New process streams use `SeedSequence([0x58505247, role, participant_id, algorithm_index, process_seed])`; roles policy/execution/feedback are 1/2/3. This avoids collisions caused by the previous additive offsets, which remain only in explicit `legacy` mode. The single-run population default remains historical `20260804`; batch runners draw each scenario's requested population. The audit uses distinct streams across independent batches and deliberate common streams within matched controls. Tests and comparison validate actual leaf-generator states, not only top-level seeds.

Trial and summary provenance includes all three seeds, `execution_belief`, `true_execution_bias/noise_scale`, `belief_execution_bias/noise_scale`, and calibration counts. `continuous_execution_calibration.csv` saves the calibration observations. Audit configuration JSONs, population parameters and fingerprints support reconstruction. Five population batches, rather than individual passengers or repeated trials, determine the main confidence intervals.

## Model and fields

`monotone_bayes.py` implements `p(accept | m,b,beta)=sigmoid(beta*(b-m))`, `beta>0`, with normalized grid posterior weights under a Bernoulli likelihood. `PriorGrid` records all fixed prior parameters and quadrature bounds; these are not learned from participant truth. `Config.bayes_grid` accepts an alternative prior/grid for programmatic sensitivity checks.

- `estimated_boundary_so_far`: posterior median of `B_tau = b - logit(tau)/beta`.
- `boundary_ci95_lower/upper`, `boundary_ci95_width`, `posterior_boundary_sd`: uncertainty about B_tau, without clipping to tested intensities.
- `boundary_support`: `no_data`, `all_accept`, `all_reject`, `below_observed_range`, `above_observed_range`, or `within_observed_range`.
- `boundary_mass_below_observed/above_observed`: posterior extrapolation mass. These are not a claim of empirical identification outside the sample.
- `posterior_grid_edge_mass`: mass on the outermost quadrature nodes; a truncation diagnostic, not a bound on omitted tail probability.
- `predicted_acceptability_before_trial`, `predicted_probability_sd_before_trial`: previous posterior evaluated at the newly realized intensity, before updating with its label. SD is epistemic uncertainty, not Bernoulli observation SD.
- `predictive_brier_score`: `(pre-feedback predicted probability - binary feedback)^2`. Scores are conditional on realized intensity, not command-level predictions.
- `boundary_ci95_covers_truth`: synthetic diagnostic. Legacy mode records posterior interval fields as missing because its uncertainty score is not a posterior.

The synthetic truth remains `criterion_boundary_tau`, computed from the noise-mixture generator and current carryover. Errors and overshoots use this quantity; `acceptability_midpoint` and `legacy_midpoint_*` retain their historical meaning. The fitted stationary logistic does not know hidden lapse/carryover parameters and may be misspecified.

Posterior probabilities use deterministic integration (121 × 61 parameter grid). Cached probability moments are interpolated on a 601-node intensity grid; small or out-of-range queries use direct integration. The comparison checks a doubled parameter grid, broader prior and model-consistent prior-predictive coverage. Empty/all-one/all-zero histories retain proper uncertain posteriors and explicit support flags.

Single-run box/bar plots show the first (low-noise) scenario; tradeoff plots include both. The historical surrogate comparison uses five process seeds with a fixed synthetic population, so its seed intervals are not population-level evidence. The current execution/population comparison instead averages process repeats within each of five independently generated population batches before computing t intervals across batches. These small-sample intervals are not multiplicity-adjusted; intervals for proportions may extend beyond [0,1].
