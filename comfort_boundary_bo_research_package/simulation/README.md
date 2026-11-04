# Continuous-command synthetic simulation

Current revision: **2026-11-04 monotone Bayesian binary surrogate**. Synthetic passengers only. The response model is Bayesian; the acquisition score remains heuristic.

See the [model and comparison report](../../docs/2026-11-04-monotone-bayes-results.md) and [earlier criterion-boundary correction](../../docs/2026-11-04-boundary-correction-results.md).

## Entry points

- `run_uncertain_input_bo_extended.py`: 24 synthetic passengers × 12 trials × 5 policies × 2 noise levels; defaults to `outputs_bayesian/`.
- `run_uncertain_input_bo_poc.py`: 18 synthetic passengers × 10 trials × 5 policies; defaults to `outputs_bayesian_poc/`.
- `../../long_horizon_audit/scripts/run_multiseed_simulation_audit.py`: five process seeds plus six sensitivity scenarios. Specify `--output-dir`; optionally `--surrogate legacy_kernel`.
- `compare_surrogates.py`: reads the committed/rebuilt new and legacy audit paths, runs same-history replay, checks grid resolution and prior sensitivity, and writes `../../results/monotone_bayes_20261104/`.
- `compare_boundary_results.py`: historical metric-correction comparison, still uses the preserved legacy snapshots.

Both simulation entry points accept `--surrogate monotone_bayes|legacy_kernel` and `--output-dir`. Legacy defaults write `outputs_continuous/` and `outputs_continuous_poc/`. Do not use a Bayesian run to overwrite the historical directories.

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

Main box/bar plots show the first (low-noise) scenario; tradeoff plots include both. The comparison figure uses five process seeds, all reusing a fixed synthetic population. Seed intervals are descriptive t intervals, not population-level evidence or multiplicity-adjusted tests; intervals for proportions may extend beyond [0,1].
