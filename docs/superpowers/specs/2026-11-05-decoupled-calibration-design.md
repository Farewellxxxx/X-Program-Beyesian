# Decoupled passenger simulation and calibration — approved task

User approved execution on 2026-11-05 (Asia/Shanghai), after explicitly approving the research prompt and choosing GPT-6.1 Sol executors with GPT-6 Astra coordination/review. No further routine implementation approval is needed. GitHub commit/push is authorized; no force push or deletion of unrelated work.

## Research question and scope

Estimate each passenger's **one-dimensional realized-acceleration acceptability upper boundary**, using binary acceptable/unacceptable feedback. Compare Bayesian adaptive calibration, TVCG-derived UCB, and a criterion-matched staircase on trials needed to attain a predefined estimation quality. This is NOT detection threshold measurement, maximum-comfort-point optimization, or vehicle control.

CHI 2027 Poster evidence plan: simulation supplies comparative algorithm evidence; a later BO-only human feasibility study with independent validation supplies deployment/experience evidence. This task implements and evaluates simulation, not the human study. Synthetic advantages are not human comparative evidence. BO winning is not an acceptance criterion.

## Architecture and information boundary

- Independent passenger simulator accepts realized acceleration and explicitly documented public context, and returns a binary response. Hidden boundary, curve parameters, lapse parameters, probability, future random draws and evaluator state NEVER enter the policy interface. No policy-name-dependent passenger behavior.
- Vehicle execution independently maps target command to realized acceleration. True execution and the public estimated execution model are separate. Execution deviation alone does not make an otherwise measured trial invalid.
- Calibration policies expose a common suggest/observe/estimate interface; policy histories are whitelist projections. Each method has separate state/history and sees only its own observations.
- Independent runner/evaluator owns ground truth and participant generation. Separate public types from private simulation data. Ground-truth records can be stored for auditing but cannot be passed to policies.
- A single main entry point with focused modules, modest configuration and clear outputs. Reuse proven Bayesian inference, RNG isolation and historical fixes. Preserve previous complex execution work as historical/optional; do not undertake another expanding execution-model study.

## Simulator requirements

Individual hidden boundary B_tau, slope/response variability, seeded population and Bernoulli response draws. A modest set of scientifically motivated curve families must include both matched and mismatched response models; do not evaluate only the exact policy likelihood family. Noise mixtures must have correct B_tau (not automatically the midpoint). Main study uses stationary boundaries; any drift is a separately labeled extension with time-appropriate truth.

Independent population, execution-calibration, execution, feedback and policy RNG streams. Paired participants across methods, never forced equal responses at unequal stimuli. Public simulation parameters and priors are fixed before held-out evaluation; no tuning final scenarios until BO wins. Include meaningful simulator-only tests of probabilities, boundaries, noise, reproducibility and isolation. Synthetic plausibility is not empirical validation of humans.

## Algorithms and literature

Audit the original TVCG paper and source, uncertain-input BO, Bayesian binary threshold estimation/acquisition, and criterion-targeted staircase. Primary sources only for technical claims; document problem/evidence/decision/limitation succinctly.

BO: retain an appropriate Bernoulli Bayesian response model; implement ONE principled acquisition aimed at reducing uncertainty about B_tau, including prospective execution uncertainty. Distinguish epistemic uncertainty from response noise. Explain naming accurately (Bayesian adaptive threshold estimation / BO-inspired if appropriate); do not claim exact uGP-UCB reproduction. Include a matched ignore-execution-uncertainty ablation if affordable.

UCB: trace adaptations from TVCG reward, epsilon exploration, update, majority voting and stopping. Arms are target commands, not retrospectively relabeled realized values. Explicitly discuss reward versus B_tau objective. Do not compare a winning command directly against a realized-domain boundary.

Staircase: specify initialization, step/reversal and criterion. Match tau; do not compare a 50% staircase target with a 70% BO target as if identical. Avoid deliberately poor settings.

Prefer main comparison of different samplers using a common reporting estimator and physical-domain evaluation, with each method's own history. Label it as sampling-efficiency comparison rather than a verbatim whole-system reproduction. Use common realizable targets for the main comparison. Retain original behaviors as provenance, not an excuse to force minimum trial counts that manufacture superiority.

## Frozen evaluation

Before the main run, save the exact configuration: tau, delta, common domain/candidates, sample size, budgets/checkpoints, population/curve/execution scenarios, seeds, development versus held-out evaluation split, reporting and failure/censoring rules. Existing tau=0.70 may be the explicitly synthetic operational main setting, not a confirmed human standard. Justify delta and other choices without choosing based on advantage size.

Report error trajectories, trials to a predefined reliable accuracy criterion, success fraction within budget, unacceptable exposure, boundary overestimation, and interval width/coverage for estimators which provide intervals. Retain failures and out-of-domain/unidentifiable cases. Do not count one lucky threshold hit as reliable convergence. Do not call simulated trials measured real-world time. Summarize independent passengers/batches rather than pseudo-replicating sequential trials. Report uncertainty and unfavorable scenarios.

Pilot runtime first, then freeze a defensible bounded run; no unbounded sweeps and no rerun of every legacy experiment. If both generator and algorithm change, avoid attributing the combined result to one component.

## Execution and delivery

Research/audit → interfaces/implementation plan → two independent implementation tasks → integration/isolation tests → runtime smoke → frozen held-out run → analysis/plots → independent whole-change review → required verification → commit/push and remote verification.

Deliver source modules and tests, primary-source method rationale, frozen config/seeds and necessary trial records, main figures, a Chinese results/limitations report, reproducibility commands, verification record, and a short BO-only human-study handoff. Do not build the human UI or new paper/presentation artifacts in this task.

Work repository: E:/study documents/X program/YY Wang/.publish/X-Program-Beyesian, base 9b5085b. Source-only original reference materials are in E:/study documents/X program/YY Wang (including rlalgorithms/Algorithms/UBC_1_param.py and the TVCG PDF). Never publish private raw participant records. Preserve root-project accessibility by syncing only this task's finished files back after verification if needed.

## Delegation and resource discipline

Astra coordinates research decisions/interfaces and reviews. Two GPT-6.1 Sol workers implement passenger/execution and policies respectively; reuse them for bounded integration/analysis work after their initial responsibilities complete. No unnecessary recursive agents. Pass concise briefs and file paths rather than full chat context. Keep file ownership disjoint. Root handles user communication, environment/publication and integrated checks. Ordinary choices are autonomous within this approved scope.
