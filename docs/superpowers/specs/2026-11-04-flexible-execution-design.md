# Flexible execution estimation design

Baseline 9679123. User requests an execution estimator that handles gain, nonlinearity and correlated noise, paired reruns of the existing misspecification/budget study, clear improvements and remaining limitations, then GitHub publication. Synthetic-only; no real passenger or vehicle resources.

## Chosen approach

Add an observation-only, regularized quadratic acceleration mean and full three-channel standardized residual covariance. Keep physical generators, response posterior, acquisition scores, all budgets, calibration commands and random roots unchanged. Alternative unrestricted dynamics/GP fitting would change more assumptions and need more calibration data; copying the one-rho truth family would be narrower and risk encoding the answer. The chosen full covariance learns three scales and three correlations from observations, not a truth profile label.

For d=x-(x_min+x_max)/2, mean acceleration is the existing clipped .05+.94*x plus learned b+g*d+q*d^2 before clipping. Conditional jerk and duration means and heteroscedastic base scales remain known as before. The raw quadratic derivative must be nonnegative at both command endpoints; this enforces monotonicity throughout the interval, also after clipping. No claim of arbitrary nonlinear dynamics identification.

## Estimation fixed before outcomes

Use only command, acceleration, jerk and duration. Exclude/count records exactly at the known realized clipping bounds as before. Require at least eight remaining observations and full rank of the weighted three-column quadratic design; reject nonfinite, out-of-range or rank-deficient inputs. No silent fallback or discarded failed scenarios.

Let X=[1,d,d^2]/s_a(x) and Y contain standardized acceleration residual against .05+.94*x, jerk residual against .58+1.74*a+.10*x, and duration residual against 3.90-.30*a. Project all three columns onto the same X; R=Y-X*lstsq(X,Y). S=R'R/(n-3) estimates the latent covariance; projecting the known-zero-mean jerk/duration residuals removes nuisance sample projections and gives all cross-products the same degrees of freedom. These projections are used only for covariance estimation, not extra jerk/duration mean fits.

Covariance estimate is (1-lambda)*S+lambda*diag(S)+1e-8*I with lambda=3/n. This fixed shrinkage stabilizes small-budget correlations and ensures a positive-definite sampler; it is not an optimized Ledoit-Wolf estimate. Fit the acceleration coefficients with H=X'X+max(S_aa,1e-8)*diag(1/prior_sd^2), score X'Y_a, zero prior means, and prior SDs (0.50,0.50,0.75) for (b,g,q). Enumerate the four endpoint-constraint active sets and choose the feasible quadratic-objective minimum. These constants are engineering choices, recorded and not tuned after observing outcomes.

This is a regularized plug-in estimate. It does not propagate coefficient/covariance estimation uncertainty into predictions or acquisition, is not an exact joint Bayesian execution posterior, and does not model general censoring. The existing monotone Bernoulli response posterior remains unchanged.

## Integration

New `simulation/flexible_execution.py` owns immutable fitted parameters/settings, estimator and scalar/vector sampling. No import of true Distortion parameters into the fitting function. An adapter upgrades a PreparedExecution using only its calibration observations and public settings, leaving truth and observations untouched. Policy history stays restricted to observables.

Expose `--execution-estimator simple|quadratic_covariance` in extended/POC runners; explicit new mode writes dedicated outputs and an execution-fit CSV. Preserve existing defaults and output snapshots for reproducibility; README's new-model command explicitly selects it. Programmatic run_configurations accepts the same optional selector. No Config schema changes, so archived experiment manifests remain valid.

## Paired study and validation

Reuse all seven profiles and budgets 8/20/40/160, five prior population batches, two process repeats, 24 passengers × five algorithms × 12 feedback trials. Run 280 new-estimator scenarios. Replay all 420 prior simple/oracle/nominal scenarios, saving their per-run summaries and manifests (the existing archive already has individual records). Compare the 280 new scenarios against the corresponding old calibrated cells and oracle/nominal references. Total 700 audit scenarios. Regenerate extended/POC examples for the explicit new estimator separately.

Use exact same nested calibration observations, with hashes and numeric prefix checks across budgets/models. Keep diagnostic grid/seeds at 21 commands × 4096 draws; no diagnostics enter training. Save coefficients, full covariance, shrinkage, rank/condition, constraint activation, used/clipped counts. Check full actual process leaf-state uniqueness excluding intentional paired reuse; fixed-policy trajectories must remain unchanged across estimators.

Compute old-to-new paired population-batch intervals for execution mean/SD/Wasserstein errors, predictive interval coverage, boundary error, unacceptable feedback, Brier score and protocol thresholds. Also compare each new budget with 40, with oracle/nominal and UncertainInputBO with Naive. Average repeats within five batches, then t intervals; no equivalence or universal superiority claims. All current structural stress profiles lie inside the expanded model family before regularization/clipping approximation, so improved recovery is not proof against untested higher-order, time-varying, heavy-tailed or conditional-mean misspecification.

Tests cover independent coefficient/covariance calculations, all constraint cases, input/identifiability failures, covariance positivity, unequal correlations, sampler agreement, no truth leakage, original-history compatibility, identical observations, strict metadata/pairing/completeness guards and CLI integration. One final independent read-only review; publish after final tests, hashes, original-workspace sync and remote SHA verification.
