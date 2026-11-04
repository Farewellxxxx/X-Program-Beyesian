# Decoupled Calibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. User approved continuous execution and exactly two Sol implementers; Astra coordinates and reviews, root integrates/publishes.

**Goal:** Compare sampling efficiency for a realized-acceleration acceptability boundary using independent synthetic passengers.

**Architecture:** Private population/vehicle/evaluator own truth. Immutable public observations and an independently calibrated execution belief are the only inputs to policies. Every sampler reports the same Bayesian logistic estimator fitted to its own realized measurements.

**Tech Stack:** Python, NumPy, existing MonotoneBayesianLogistic, pytest, matplotlib; no new runtime dependency.

**Spec:** `docs/superpowers/specs/2026-11-05-decoupled-calibration-design.md`

## Global Constraints

- Hidden boundary, curve parameters, lapse parameters, probability, future random draws and evaluator state NEVER enter the policy interface.
- Independent population, execution-calibration, execution, feedback and policy RNG streams.
- BO winning is not an acceptance criterion. Synthetic advantages are not human comparative evidence.
- Arms are target commands; execution deviations alone do not invalidate measured trials.
- Preserve legacy code/outputs; no private participant data; no worker git commits/pushes.
- Main shared target domain [0,3] m/s², 31 equally spaced commands; tau=.70 is synthetic; delta=.15 m/s² is 5% of the domain, not validated human tolerance.
- Public contract lives at `comfort_boundary_bo_research_package/simulation/decoupled_calibration/public.py`; changes require coordinator notice.
- Root exclusively owns top-level README, publication manifest, integrated runs and verification record.

## Review Focus

- All-accept/all-reject and out-of-domain boundaries remain reported; no silent clipping of estimated B_tau.
- Lapse changes the crossing; test p(B_tau)=tau for every generator family.
- Changed hidden truth and other-method histories cannot alter a policy with identical public inputs.
- Prospective realized X is subsequently measured; acquisition averages conditional posterior risk over X, rather than treating it forever latent.
- Coarse target rounding can shift staircase criterion; retain a continuous internal state and report finite-grid limitations.

---

### Task 1: Independent passenger and vehicle (Sol passenger worker)

**Own files:** package `passenger.py`, `execution.py`, tests `tests/test_decoupled_passenger.py`, `tests/test_decoupled_execution.py`, `docs/decoupled_simulator.md` (within research package).

**Interfaces:** `Passenger` holds private evaluator data and exposes `probability(realized: float)->float`, `respond(realized: float, rng: Generator)->int`, `.boundary`, `.family`, `.slope`, `.lapse`. `generate_passengers(n:int, family:str, tau:float, rng:Generator)->list[Passenger]`. Families `logistic`, `probit`, `lapse_logistic`; choose B uniform [.5,2.5], positive slope lognormal(log(4),.35), lapse .10 for lapse family else 0. Define p(x)=lapse/2+(1-lapse)*S(k*(location-x)); solve location so p(B)=tau, including probit inverse. No import of likelihood/inference code.

`ExecutionTruth(intercept:float,gain:float,sd:float,lower:float=0,upper:float=3)`; `execute(target:float, truth:ExecutionTruth, rng:Generator)->float`; `calibrate_execution(truth:ExecutionTruth,rng:Generator,n:int=90)->ExecutionBelief`. Calibration uses independent samples, affine fit, residual SD; note clipping bias, use interior calibration targets. `execution_quadrature(target:float, belief:ExecutionBelief,nodes:int=7)->tuple[ndarray,ndarray]` returns clipped Gaussian Hermite nodes/normalized weights; zero sd deterministic. `spawn_streams(seed:int, participant:int, method:int)->dict[str,Generator]` with documented stable semantic IDs. Population generation remains method independent.

- [x] Add tests for crossings, monotonicity, lapse asymptotes, response frequency, invalid values, reproducibility, RNG isolation, clipping and quadrature normalization.
- [x] Run focused tests to establish failure before implementation.
- [x] Implement interfaces and short generator rationale/limitations.
- [x] Run focused tests with unique workspace-local TMP/TEMP and basetemp; report evidence and changed files to coordinator.

### Task 2: Three samplers and common readout (Sol algorithms worker)

**Own files:** package `policies.py`, `tests/test_decoupled_policies.py`, research-package `docs/decoupled_algorithms.md`.

**Interfaces:** `make_policy(name:str, config:PolicyConfig, belief:ExecutionBelief, rng:Generator)->Policy`. Names `bayes_risk`, `bayes_point`, `ucb_tvcg`, `ucb_tau`, `staircase`. Primary UCB preserves normalized source reward +u/-u; ucb_tau is a labeled secondary penalty sensitivity (+u on accept, -tau/(1-tau)*u on reject). Each exposes only suggest/observe/estimate; constructors receive no simulator objects. Use existing MonotoneBayesianLogistic with configured nodes and unchanged priors. Common report is posterior median and 95% equal-tail interval, support and edge mass. Observe rejects non-Observation records and invalid response/measurement; immutable copied own-history only.

**Acquisition decision:** maximize expected reduction in Var(B_tau). For each prospective realized x, compute response predictive q, posterior B moments after y=0/1, and Var(B)-sum_y p(y|x)Var(B|x,y). Average this gain over public execution quadrature, because realized x will be observed. `bayes_point` uses only calibrated mean, otherwise identical. Use cached likelihood basis/matrix operations to keep runtime bounded; no initial compulsory trials unless common across all policies (default none).

**UCB decision:** audit original `rlalgorithms/Algorithms/UBC_1_param.py` and TVCG PDF. Retain epsilon exploration, Q update, historical-majority correction (including current vote, ties use current raw response), and count confidence bonus in target arms. Normalize source reward scale G/10 and confidence coefficient 2/10=.2 together; common posterior still uses raw observations; use original normalized intensity reward +u/-u for primary ucb_tvcg and explicitly secondary criterion-weighted penalty for ucb_tau; neither guarantees a B_tau-optimal command. Preserve original reward/majority/stopping as provenance in docs, not forced sampling burden. Common fixed budget/checkpoint evaluation replaces native stop. Original source at workspace root, not checkout.

**Staircase decision:** weighted up/down on continuous target state, initial midpoint 1.5. Accept moves +step*(1-tau), reject -step*tau, so expected change=step*(p-tau). Initial step=.6; halve after each two reversals to floor .15. Project only emitted target to common grid; do not round internal state. Report this sampler via common readout, not reversal average. This targets command-domain marginal criterion under execution noise; realized-domain common readout addresses evaluation, not that sampling mismatch.

- [x] Write failing tests for exact tiny-grid Bayes-risk brute force, zero-noise equivalence, nonnegative acquisition, history isolation/whitelist, same common estimator on same history, valid grid outputs, staircase expected drift at tau, UCB arm identity and no forced minimum count.
- [x] Run tests to establish missing implementation failure.
- [x] Implement policy API, primary-source method audit and explicit adaptation limitations.
- [x] Run focused tests and record evidence; no edits to passenger/execution/public files without coordination.

### Task 3: Runner, frozen evaluation and outputs (reuse passenger worker after Task 1 review)

**Own files:** package `study.py`, `__main__.py`, `tests/test_decoupled_study.py`, `configs/decoupled_pilot.json`, `configs/decoupled_heldout.json`, research-package `docs/decoupled_reproducibility.md`.

**Interface:** `run_study(config:dict, output_dir:Path)->dict` and CLI `python -m comfort_boundary_bo_research_package.simulation.decoupled_calibration --config PATH --output PATH`. Runner constructs public whitelist explicitly; truth records separate from trial/public histories. Predeclare semantic RNG seeds, independently paired participants, execution calibration common across methods, no method-order dependence. Save exact config plus SHA256 before trials, trial records and participant summaries.

**Bounded candidate design:** 3 curve families x 2 execution conditions (`precise`: intercept=0,gain=1,sd=.03; `variable`: intercept=.08,gain=.92,sd=.18), 5 methods (4 primary plus ucb_tau sensitivity), budget60, every-trial estimates, checkpoints[10,20,40,60]. Development seed1105, held-out seed271828; pilot2 passengers/cell then root freezes n according to runtime, target32/cell and bounded lower16/cell. Separate out-of-domain stress test uses B outside [0,3] and is not pooled into main study.

**Reliable-accuracy endpoint:** PRIMARY offline evaluator first t>=10 with at least five estimates from t through budget and every estimate from t through budget within delta of truth (suffix-stable). SECONDARY first t>=10 where five consecutive estimates through t have abs error<=delta (rolling-five attainment, can subsequently fail). These are retrospective truth-based evaluation metrics, not deployable stop rules; correlated estimates do not establish independent confidence. No event means right-censored at budget; report success fraction and restricted mean trials using censored cost=budget, not successes-only average. Also report final absolute/signed error, overestimation>.15, unacceptable counts/rate, interval coverage/width, out-of-domain/unidentifiable flags. Bootstrap by passenger within scenario, preserving within-passenger method pairing; sequential trials are never independent replicates.

- [x] Test method-order invariance, truth firewall via a spy policy, reproducible reruns, stream separation, censoring/event logic including transient lucky hits and suffix failure, output completeness.
- [x] Implement runner/configs; root runs pilot, freezes one held-out config then executes once without outcome tuning.
- [x] Pass records to analysis worker; keep any rerun provenance explicit.

### Task 4: Analysis and Chinese report (reuse algorithms worker after Task 2 review)

**Own files:** package `analysis.py`, `tests/test_decoupled_analysis.py`, research-package `docs/decoupled_results_zh.md`, `docs/decoupled_human_handoff_zh.md`; generated output figures under new output directory only.

- [x] Test paired participant bootstrap and censoring summaries on hand-constructed data.
- [x] Produce scenario-specific errors, success/cost and exposures, intervals, paired effect uncertainty and unfavorable scenarios; avoid pooled pseudoreplication and simulated-time language.
- [x] Write Chinese results with exact frozen settings, held-out/dev distinction, provenance, limitations, model mismatch/calibration sensitivity and no claim of human superiority.
- [x] Write brief BO-only feasibility + independent-validation human-study handoff, with no UI or new manuscript.

### Task 5: Review and publication (Astra + root)

- [x] Astra reviews each scoped implementation against spec and quality, sends fixes to owning worker.
- [x] Root runs integrated suite, runtime pilot, freezes config, executes held-out run and verifies artifacts.
- [x] Astra conducts whole-change review including information flow, fairness and conclusions; resolve findings.
- [ ] Root records verification, commits/pushes authorized branch, verifies remote hash, and synchronizes only finished task files to original workspace if needed.




