# Adaptive execution complexity and parameter propagation

Baseline: 33e01230d284cf585a25234bfb46b9738f5a09df. Synthetic-only continuation: reduce small-calibration overfit and evaluate predictive coverage without changing physical generators, populations, binary response model or acquisition rule. Preserve prior results. User authorizes implementation, experiments, workspace sync and GitHub publication.

## Choice and scope

Use proper conjugate Bayesian models for degrees 0/1/2 of the acceleration mean correction (bias, gain, quadratic). Compute normalized constrained-model evidence and use posterior model probabilities for soft complexity selection (Bayesian model averaging), rather than treating a hard selected model as certain. Export MAP degree as a diagnostic. Sample model identity, mean coefficients and full residual covariance in predictive/acquisition draws. Alternatives considered: held-out hard selection plus bootstrap would spend scarce calibration observations and omit model-choice uncertainty; generic MCMC would require convergence diagnostics and much more fitting work. A conditional Gaussian factorization gives closed-form updates and evidence here.

This is still a quadratic-family, stationary, Gaussian execution model with known conditional jerk/duration means, base heteroscedastic shapes and clipping map. Calibration likelihood approximates uncensored, unclipped means; reject invalid records, exclude/count realized clipping records as before. Require eight interior records and a full-rank quadratic command design with condition number <=1e8. No silently discarded scenarios.

## Probability model fixed before outcomes

Use only four calibration fields. Define X_k=[1,d,...,d^k]/s_a(x), y=(a-.05-.94x)/s_a and W=[(j-.58-1.74a-.10x)/s_j, (t-3.90+.30a)/.18], d centered on public command bounds. Model W_i~N(0,Lambda) and y_i=X_k beta+W_i c+e_i, e_i~N(0,sigma2). This is a full joint three-channel covariance, not independent noise; no truth/profile label enters fitting.

Let H=[X_k,W], eta=[beta,c]. Prior eta|sigma2~N(0,sigma2 V0), sigma2~InvGamma(a0=2,b0=1); diagonal prior SDs for bias/gain/quadratic are .50/.50/.75 and each conditional residual coefficient c is 1.0. Lambda~InvWishart(df0=4,scale=I2), independent. Model prior weights are (1/3,1/3,1/3). Priors are proper and fixed; no outcome-based tuning.

Vn=(V0^-1+H'H)^-1, mn=Vn H'y, an=a0+n/2, bn=b0+.5*(y'y-mn'Vn^-1 mn), evaluated by the equivalent nonnegative residual-plus-prior-penalty expression for stability. Lambda posterior is IW(4+n,I+W'W). Conditional log evidence is lgamma(an)-lgamma(a0)+a0 log(b0)-an log(bn)+.5(log|Vn|-log|V0|)-n/2 log(2*pi). The W marginal and transformation Jacobians cancel between degree models.

All component priors/posteriors are restricted to global acceleration-mean monotonicity: .94+g +/- span*q >=0 (missing coefficients zero). Correct evidence by log(P_posterior(constraint))-log(P_prior(constraint)); omitting prior normalization would bias complexity comparison. Degree 0 probability is one; degree 1 uses a univariate Student-t tail; degree 2 integrates over q using its Student-t marginal and the conditional Student-t tail of g above -.94+span*abs(q). Deterministic SciPy quadrature tolerance 1e-9. Add the already-installed scipy==1.13.1 dependency explicitly.

Draw the joint eta/sigma2 posterior by inverse-Gamma plus Gaussian sampling and reject nonmonotone beta, retaining sigma2 with its paired eta. Draw Lambda independently from its posterior. Reconstruct covariance in acceleration/jerk/duration order: Sigma_aa=sigma2+c'Lambda*c, Sigma_aW=c'Lambda, Sigma_WW=Lambda. Cholesky sampling then uses original channel means and physical clipping. Rejection has an explicit bounded failure; never silently project posterior samples or fall back to a plug-in fit.

Default 2048 accepted draws per degree, fixed-size draw batches and separate posterior streams for eta/sigma2 and Lambda. Seed derives only from ordered observable values, public execution settings and fixed posterior settings; posterior-draw count is excluded from this seed so 8192-draw checks retain the same prefixes. Store all settings, seed/draw fingerprints, model probabilities, coefficients/covariance means, parameter SDs, constraint probabilities and acceptance diagnostics. Ensembles are reproducible from saved observations/settings; do not publish a redundant large draw archive. Prior/data probability calculations are deterministic, not estimated from the finite ensemble.

## Implementation and integration

`execution_posterior.py`: proper prior settings, conjugate updates, constraint probabilities, evidence, immutable posterior component draws and observation-only fitting. `adaptive_execution.py`: posterior-mixture execution sampler, plug-in ablation adapters, PreparedExecution/CLI integration. Existing defaults, Config schema, old samplers and archived bytes remain unchanged. Add explicit `--execution-estimator adaptive_posterior`, separate `outputs_adaptive_execution[_legacy_kernel][_poc]` paths and fit exports with metadata propagated into all summaries.

## Experiment

Reuse all seven profiles, four budgets (8/20/40/160), five populations and two process repeats: 280 new full adaptive-feedback scenarios, plus all 280 current quadratic plug-in scenarios replayed exactly. Each has 24 participants x 5 algorithms x 12 labels: 806400 feedback trials plus separate extended/POC examples. No full feedback factorial is necessary for the requested small-budget execution-diagnostic focus.

For each calibration set, run independent execution diagnostics for six variants: old quadratic_covariance, quadratic_plugin (new conjugate posterior mean parameters), adaptive_plugin (model-weighted posterior mean parameters), quadratic_posterior, adaptive_posterior and oracle. The four new variants form a 2x2 comparison of fixed/adaptive complexity and plug-in/posterior predictions; both plug-ins use E(beta),E(Sigma) without coefficient/model mean-spread variance. These are execution-distribution ablations, not full feedback-policy experiments. The posterior family/prior/correlated regression differs from the old ridge estimator, so old-to-new gains cannot be attributed solely to either switch.

Keep old 21-command x4096 diagnostic namespace and columns for exact baseline recheck. Additionally evaluate interval coverage and central 90% interval score on independent true draws from a separate namespace, shared across variants. Report width and score with coverage, so merely widening intervals cannot be called uniformly better. Include mean/SD/W1 errors, protocol probability error, training acceleration mean RMSE, model weights/MAP degree and posterior parameter spread. Oracle is a distribution reference, not an optimizer guarantee.

Compute intervals by averaging two repeats within each of the same five population batches, then paired t intervals across batches. Validate exact observations/prefixes, all manifests/rows/variants/grids/settings/draw fingerprints, fixed-policy trajectories and actual RNG leaf states. Recompute posterior fits in validation. Recompute individual summaries and freeze all previous archives. Small-sample intervals are descriptive and not multiplicity-adjusted.

Predeclared numerical checks: for all seven profiles at budgets 8/40, first population/repeat only (14 fits), compare 2048 versus 8192 posterior draws, and coefficient prior SD multiplier 1 versus 2. Save differences and report sensitivity; these single-cell checks do not establish population-level prior robustness. Do not tune main settings after results.

## Limits to report

Model averaging need not identify the true order from eight points; model probabilities and uncertainty depend on the stated proper priors. Posterior intervals are Monte Carlo approximations and have no unconditional real-vehicle coverage guarantee. Propagating epistemic uncertainty can raise caution/exposure tradeoffs or widen intervals without lowering final boundary error. No higher-order/time-varying dynamics, temporal correlation, heavy-tail likelihood, general censoring likelihood, learned intensity map or real participant evidence is added.

References: conjugate Bayesian linear models (https://arxiv.org/html/2406.01819v1); SciPy inverse-Wishart implementation (https://docs.scipy.org/doc/scipy-1.13.1/reference/generated/scipy.stats.invwishart.html); proper interval scoring (https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf).
