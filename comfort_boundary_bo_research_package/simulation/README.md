# Continuous-command synthetic simulation

Current revision: **2026-11-04 criterion-boundary correction**. This is an uncertain-input BO-inspired heuristic with synthetic passengers, not a validated human-study implementation.

See [the correction report](../../docs/2026-11-04-boundary-correction-results.md) for equations, schema changes, before/after results and remaining limitations.

## Entry points

- `run_uncertain_input_bo_extended.py`: fixed population, 24 synthetic passengers, 12 trials per policy, low/high execution noise; writes `outputs_continuous/`.
- `run_uncertain_input_bo_poc.py`: 18 synthetic passengers, 10 trials, low noise; writes `outputs_continuous_poc/`.
- `../../long_horizon_audit/scripts/run_multiseed_simulation_audit.py`: five process seeds and sensitivity scenarios; output directory is explicit.
- `compare_boundary_results.py`: verifies unchanged historical trajectories and creates before/after tables and figure.

All boundary errors and overshoots now use `criterion_boundary_tau`, including history-dependent carryover. `acceptability_midpoint` is the latent 50% point. Explicit `legacy_midpoint_*` columns exist only to reconstruct historical metrics. The response generator, acquisition functions and RNG are unchanged.

`criterion_boundary_tau` can lie outside the tested command/intensity range; it is synthetic ground truth. This correction does not add censoring or monotonicity to the heuristic estimator. Unattainable criteria raise `ValueError` rather than producing a clipped pseudo-truth.

The main box/bar plots use the first (low-noise) scenario; the tradeoff plot includes both noise settings. The separate comparison figure summarizes five process seeds for both settings. The five seeds reuse a fixed population; intervals do not capture population uncertainty.

The archive `long_horizon_audit/derived/simulation_audit/` predates this repair. New audit outputs are in `simulation_audit_corrected_20261104/`.
