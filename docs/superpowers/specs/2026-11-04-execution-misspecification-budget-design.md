# Execution misspecification and calibration budget design

Baseline: e06f0e2. User requests synthetic-only robustness validation, interpretation of prior conclusions, and GitHub publication. Existing response model, acquisition, feedback budget and historical outputs remain fixed.

## Approach and scope

Use a separate stress generator and audit, retaining the existing observation-only bias/common-scale calibrator. This directly tests the current model rather than silently improving it during evaluation. A richer fitted dynamics model and online calibration are alternatives, deferred because they would confound robustness with a new algorithm. Choices below are implementation judgments within the requested experiment, not user-specified physical values.

Seven profiles: matched_low (noise .65, bias 0), matched_high (1.55, 0), biased_high (1.55, +.15), gain_high, nonlinear_high, correlated_high and combined_high (last four also 1.55, +.15). For centered command d=x-(x_min+x_max)/2, true acceleration mean adds gain*d + quadratic*d*d, before existing clipping. Gain=.25, quadratic=.45, residual correlation=.75 when enabled; combined enables all. Positive quadratic remains monotone over this command range. They are illustrative perturbations, not measured vehicle dynamics or a robustness envelope.

Correlated standardized residuals are z_a=u_a, z_j=rho*u_a+sqrt(1-rho^2)*u_j, z_d=rho*u_a+sqrt(1-rho^2)*u_d. Thus acceleration/jerk and acceleration/duration residual correlations equal rho; jerk/duration equals rho^2. Preserve the scalar innovation order acceleration, jerk, RMS jerk, duration, speed for common random numbers across profiles. All channels retain their clipping bounds. Response and measured effective-intensity definition remain unchanged.

Each profile has six arms: nominal (bias 0, scale .65), oracle (full true distribution including distortion, separately instantiated), and unchanged calibrated model with 8/20/40/160 execution observations. Oracle is an information reference, not a guarantee of best heuristic-policy outcomes. Calibrated and nominal beliefs must have no distortion object or truth settings. Calibration is extra shared execution cost, outside each person's 12 response trials.

Use the prior five population seeds, two nested process/calibration repeats and 24 passengers × five policies × 12 responses. Same population and underlying streams across arms/profiles form intentional paired comparisons; only five population batches are independent statistical units. Total main design: 420 scenarios. Save configuration, population traits, calibration observations, participant and policy summaries and trajectory fingerprints. Keep old default entry points unchanged; pass prepared execution objects into the existing runner via an optional argument.

## Budget design and independent diagnostics

New budget experiments use deterministic base-2 radical-inverse commands in the central 20%-80% of the allowed command range. Budget n is exactly the first n observations of the same stream: larger budgets add information without replacing earlier commands/noise. The old design used a budget-dependent sorted linspace; explicitly distinguish this schedule change when comparing to the previous report. Replay the prior population/stress scenarios with their original schedule to establish numerical compatibility, and compare new matched/biased 40-observation cases against paired old results.

At 21 evenly spaced commands over the full allowed range, compare true and believed intensity samples (4096 per command) using a separate, domain-separated diagnostic seed. Save predictive mean/SD differences, empirical Wasserstein-1 distance, predicted central 90% interval coverage under true draws and protocol-threshold probability discrepancies. Label interior vs extrapolation commands; no holdout draw enters calibration or policy selection. Common diagnostic innovations reduce Monte Carlo noise, and the oracle should agree exactly. Finite-sample diagnostic precision and clipping must be disclosed.

## Analysis and checks

Average two process repeats within each population batch, then use paired batch differences and t intervals over five batches. No equivalence claim just because an interval contains zero; no multiplicity-adjusted or real-world claims. Compare each calibrated budget with oracle and nominal, budgets with 40, distorted profiles with biased_high, and UncertainInputBO with NaiveContinuousBO. Show all policies and report adverse results as prominently as improvements.

Reject incomplete/duplicate/nonfinite results and mismatched configuration, seed, truth, observation prefixes or policy fingerprints. Check actual leaf states across independent batches while excluding intentional common streams. Verify all fixed strategies are identical across beliefs/budgets for each true profile. Calibrator failures must be explicit; never silently omit a scenario. Tests cover analytical mean changes, covariance, scalar/vector consistency, nested calibration data, truth isolation, exact historical replay and statistics guards. One final independent code/statistical review, fix verified important findings, then sync original workspace and publish main.
