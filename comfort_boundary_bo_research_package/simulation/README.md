# Continuous-command synthetic simulation

Current revision: **2026-11-04 execution belief separation and independent populations**. Synthetic passengers only. The response model remains Bayesian; the acquisition score remains heuristic.

See the [latest results](../../docs/2026-11-04-execution-population-results.md), [Bayesian model report](../../docs/2026-11-04-monotone-bayes-results.md) and [earlier boundary correction](../../docs/2026-11-04-boundary-correction-results.md).

## Entry points

- `run_uncertain_input_bo_extended.py`: 24 synthetic passengers × 12 trials × 5 policies × 2 noise levels; defaults to `outputs_execution_separated/`.
- `run_uncertain_input_bo_poc.py`: 18 synthetic passengers × 10 trials × 5 policies; defaults to `outputs_execution_separated_poc/`.
- `../../long_horizon_audit/scripts/run_execution_population_audit.py`: independent nested population/process experiments, matched fixed-population controls, historical replay and execution-misspecification stress test.
- `../../long_horizon_audit/scripts/compare_execution_population.py`: validates complete configurations and pairing, computes intervals over independent population batches, and plots current comparisons.
- `../../long_horizon_audit/scripts/run_multiseed_simulation_audit.py`: five process seeds plus six sensitivity scenarios. Specify `--output-dir`; optionally `--surrogate legacy_kernel`.
- `compare_surrogates.py`: reads the committed/rebuilt new and legacy audit paths, runs same-history replay, checks grid resolution and prior sensitivity, and writes `../../results/monotone_bayes_20261104/`.
- `compare_boundary_results.py`: historical metric-correction comparison, still uses the preserved legacy snapshots.

Both entry points accept `--surrogate`, `--execution-belief calibrated|nominal|oracle`, `--process-rng-mode independent|legacy`, `--population-seed`, `--calibration-seed`, `--calibration-trials`, `--true-execution-bias`, `--assumed-execution-bias`, `--assumed-execution-noise-scale` and `--output-dir`. Only `oracle` plus `legacy` RNG selects the old Bayesian/kernel output paths; independent-stream runs use new directories. Keep historical directories for their original settings.

## Execution information and random streams

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
