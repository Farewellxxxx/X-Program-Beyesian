# Execution truth/belief separation and independent populations

## Scope and decisions

Implement the user's authorized next synthetic-research step: separate the generating execution distribution from the algorithm's estimate, introduce explicit independent population seeds, validate and compare, then publish. Preserve the response posterior, criterion-matched metrics, acquisition coefficients, physical generator and participant trial budget.

Options considered: fixed assumed parameters alone (useful stress control but not a fitted estimate); offline calibration from independent synthetic execution observations (chosen default); online distribution learning (adds policy-dependent training and sequencing, deferred). No real vehicle data is used. Calibration costs 40 additional simulated maneuvers per execution condition/seed, without passenger feedback, shared fairly by all policies; it is separate from 12 passenger trials and must be reported.

## Information boundary

Create immutable ExecutionParameters(bias, noise_scale), public ExecutionSettings, and PolicySettings containing only usable algorithm settings. The simulator constructs the true distribution. Policies receive a separate belief instance with no true bias/noise, seed, latent passenger, or feedback-noise attributes. Policy history contains only observed command, realized motion and feedback fields, never exported truth/diagnostic columns. Simulator output may contain both truth and belief for evaluation, clearly named.

Modes: oracle explicitly copies true parameters into a separate model for historical comparison; calibrated fits only command/acceleration/jerk/duration observations; nominal uses explicitly assumed bias=0 and noise_scale=0.65 (stress baseline). The calibrated/nominal construction never reads hidden parameters. All modes share public generator functional form and intensity/safety definitions, a remaining optimistic assumption.

Fit the additive acceleration bias by weighted least squares with inverse base acceleration variance. Estimate a common noise scale from standardized acceleration, conditional jerk and conditional duration residual sums of squares, divided by 3*n-1. This is a plug-in estimate, not a posterior over execution parameters. Calibration commands span the central 20%-80% of the public command range. Reject nonfinite/malformed data and degenerate fits; omit observations at realized clipping bounds and report their count. Clipping can still bias this approximation; do not claim general censored likelihood inference.

Calibration uses its own SeedSequence([calibration_seed, 0xCA1B]); population uses population_seed, defaulting to historical BASE_SEED+101 for single-run continuity. New process streams use SeedSequence([0x58505247, role, participant_id, algorithm_index, process_seed]); role codes are policy=1, execution=2, feedback=3. The old additive formulas are confined to explicit process_rng_mode=legacy for exact historical replay. Changing process/calibration seeds must not change passenger parameters. Changing population seed must not change execution calibration. No seed is implicitly derived from another role.

## Experiment

- Historical replay: five old process seeds × two noise levels, fixed old population, oracle, compare all old numerical metrics.
- Population study: five independent population seeds × two process seeds nested within each population × two execution-noise levels × oracle/calibrated. Every pair shares population, process, calibration, physical generator and budget. Calibration repeats across noise levels with common innovations, but independent across population/process blocks.
- Fixed-population controls: same 20 population-study process/noise cells with the historical population and oracle. Paired with new-population oracle to isolate population changes without changing process streams.
- Stress: five independent populations × one independent process seed × high noise + true bias +0.15 × oracle/nominal/calibrated. Tests unknown bias and underestimated noise; one stress condition, not exhaustive robustness.
- 85 scenarios in total, five policies each, 24 passengers × 12 trials. Extended/POC new default artifacts are separately regenerated. Save per-participant/per-run metrics, seed/config manifests, calibration observations/estimates and population parameters; avoid publishing huge redundant trial logs from the full audit.

First average process runs within each population block, then form means and 95% t intervals across five population blocks (df=4). Report paired differences with the same grouping. Do not treat 24 people × repeats or all process runs as independent population replications. Fixed-population and archive summaries remain labeled as such. Changing cohorts is an external-validity check, not an algorithm improvement.

## Verification and acceptance

Tests cover parameter recovery with independently constructed observations, clipping/invalid fits, truth/belief object and history separation, deterministic replay, seed-role invariance, identical fixed-policy paths, historical oracle reproduction, configuration-mismatch rejection and population-cluster inference. Main posterior tests remain passing. Use a fresh read-only final reviewer; fix substantive findings, regenerate results affected by changes, sync original workspace and push verified GitHub main. Previous artifacts stay unchanged.

Independent review found that distinct top-level integers still collided after the old additive offsets. The design is corrected to domain-separated leaf streams. Verify all 7,800 process-generator initial states across the default population/stress experiments (one representative per intentional paired set), plus the specific policy/feedback collision observed by review. Regenerate every affected experiment before publishing; historical replay remains legacy.

References: [NIST weighted least squares](https://www.itl.nist.gov/div898/handbook/pmd/section4/pmd432.htm); [NumPy independent random streams](https://numpy.org/doc/stable/reference/random/parallel.html). These support the general methods; the calibration model and experimental design above are project choices.
