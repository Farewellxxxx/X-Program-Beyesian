# Monotone Bayesian binary-response surrogate

## Authorized scope

Replace the current kernel heuristic with a monotone Bayesian model for binary acceptability, validate it, compare against the corrected legacy model, and publish code/results. Keep the vehicle generator, population, seeds, trial budget, acquisition score coefficients and criterion-matched truth unchanged. Scope follows the user's explicit implementation request and the existing study design's logistic/probit recommendation.

## Model and numerical method

For realized intensity m, use y ~ Bernoulli(sigmoid(beta * (b-m))), beta > 0. Parameterize beta=exp(k). Use independent fixed priors b ~ Normal(1.2, 0.75), k ~ Normal(log(4), 0.7), truncated and numerically integrated on explicit finite support. These are scale-based design priors, not fitted to simulated true passenger parameters or historical human labels; no hierarchical population fit is claimed.

Use a normalized two-dimensional trapezoidal grid posterior, default b in [-1.5,4.0] with 121 nodes and beta in [0.25,40] with 61 evenly spaced log-beta nodes. Compute Bernoulli likelihood in log space. Validate against a doubled-resolution grid and report sensitivity to a broader prior. The chosen finite grid is transparent and reproducible with existing NumPy; MCMC would add convergence/runtime dependencies and Laplace approximation is fragile for all-yes/all-no small samples.

Every parameter realization is decreasing; the posterior mean acceptance curve is therefore decreasing. Return posterior mean acceptance and epistemic standard deviation of acceptance probability, distinguished from Bernoulli observation variance. For speed, cache exact logistic curves on a 0..3 intensity grid (601 nodes), integrate their first/second moments once per fitted model and interpolate; evaluate out-of-range points directly. Verify interpolation against direct integration.

Transform posterior parameters to B_tau=b-logit(tau)/beta. The estimate is its posterior median, accompanied by equal-tail 95% credible interval, standard deviation, posterior mass outside observed intensity range and a support label. Do not clamp estimates to tested range. All-accept/all-reject/no-data outcomes are explicitly flagged as prior-dependent/extrapolated; the simulation may score their finite model estimates against known synthetic truth. Report prior-grid edge mass so truncation is visible.

The generator retains lapse/noise mixture and optional carryover; the fitted stationary logistic does not receive hidden true noise or carryover parameters. Misspecification remains explicit. Acquisition keeps the historical score and coefficients, replacing only predicted probabilities and uncertainty with posterior quantities; it is not claimed to maximize expected information gain or have SafeOpt guarantees.

## Integration and comparison

- Keep `legacy_kernel` selectable; default to `monotone_bayes`.
- Write Bayesian extended/POC results to new directories, preserving corrected legacy CSV/PNG and historical metric-correction reproducibility.
- Attach model and boundary posterior fields to trials, participant and algorithm summaries.
- Compare same-history fits on corrected legacy trajectories (isolates estimator change) and full adaptive runs with original seeds/budgets (includes changed decisions).
- Validate fixed sampling-policy trajectories remain unchanged; validate legacy mode reproduces archived corrected results.
- Run five process seeds and original sensitivity settings. Report paired per-seed differences, intervals, exposure, interval width and empirical coverage; fixed-population limitations remain.
- Check posterior numerical resolution and prior sensitivity before interpreting algorithm changes. No tuning to obtain superiority.

## Sources

- Stan logistic/Bernoulli-logit formulation: https://mc-stan.org/docs/2_27/stan-users-guide/logistic-probit-regression-section.html
- NumPy quadrature was considered; an explicit trapezoidal posterior grid is chosen for resolvable boundary quantiles: https://numpy.org/doc/2.1/reference/generated/numpy.polynomial.hermite.hermgauss.html

## Acceptance

Tests cover exact small-grid Bayes update, monotonicity, normalized finite posterior, all-yes/all-no/empty/contradictory/extreme feedback, invalid inputs, uncertainty semantics, credible intervals, range flags, integration and deterministic replay. Published suite must pass; broader original-workspace presentation-runtime failure stays separately documented. One independent review precedes authorized GitHub update.
