# Real-Vehicle BO Feasibility User Study Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, approve, dry-run, execute, analyze, and close a single-arm real-vehicle BO feasibility study with 12–16 valid completed participants and at most 12 formal probes per participant.

**Architecture:** The study has three gated workstreams: governance/operations, locked software/data infrastructure, and staged execution. Stage 0 calibrates command-to-realized motion before any participant; a two-person soft launch validates the full protocol; the main cohort starts only after predefined go/no-go review. Raw data, processed features, algorithm logs, questionnaires, incidents, and identity linkage remain separated and versioned.

**Tech Stack:** Python 3.12, `unittest`, NumPy, pandas, SciPy/scikit-learn or an approved Bayesian logistic/probit library, JSON/CSV/NDJSON, SHA256 manifests, 100 Hz IMU data, optional CAN/OBD speed, controlled-route real vehicle testing.

## Global Constraints

- Study scope is feasibility, not BO efficacy or superiority.
- Recruit 16–18 people to obtain 12–16 valid completed participants.
- Use one vehicle, one fixed trained driver, one controlled route, one longitudinal maneuver direction, one session per participant.
- Each participant receives one low familiarization probe and at most 12 formal probes: three conservative initialization probes, seven adaptive probes, and two protocol-selected anchor repeats.
- `tau=0.70` is the primary operational criterion; report sensitivity at 0.60 and 0.80; never describe tau as a universal comfort standard.
- Measured realized motion `z_t`, not target command `x_t`, is the actual stimulus used in the participant model.
- `protocol_deviation`, `safety_event`, `participant_skip`, `stop_requested`, `technical_failure`, and `algorithm_recovery` are separate fields.
- Stop/skip and driver override always dominate the algorithm.
- No participant recruitment begins before ethics/technology-ethics approval, route permission, vehicle/insurance clearance, safety sign-off, and Stage 0 go/no-go pass.
- The existing workspace is not recognized as a valid Git repository. Do not claim commits or rely on Git history. At each checkpoint, write a SHA256 manifest under `user_study/checkpoints/`; repair/version-control initialization is a separate authorized task.
- Preserve `IEEE_THMS dataset.zip`, `Data/Data`, original PDFs/DOCX/PPTX, legacy outputs, and `long_horizon_audit/` as read-only evidence.
- Do not use names, phone numbers, IP addresses, device IDs, or exact GPS routes in analysis or algorithm data.
- Full specification: `docs/superpowers/specs/2026-08-07-bo-feasibility-user-study-design.md`.

---

## Planned file structure

```text
user_study/
  README.md
  governance/
    ethics_submission_checklist.md
    protocol_v1.md
    risk_and_incident_plan.md
    privacy_and_retention_plan.md
    approvals_registry.csv
  forms/
    screening_questionnaire.md
    consent_and_safety_briefing.md
    baseline_questionnaire.md
    trial_feedback_form.md
    post_session_questionnaire.md
    interview_guide.md
    incident_and_deviation_form.md
  sops/
    stage0_execution_calibration_sop.md
    driver_operator_sop.md
    daily_run_checklist.md
    participant_session_checklist.md
    recovery_and_stop_sop.md
  config/
    study_config.json
    data_dictionary.csv
    questionnaire_codebook.csv
  src/
    config.py
    schema.py
    signal_pipeline.py
    boundary_model.py
    acquisition.py
    session_runner.py
    checkpoint_manifest.py
  tests/
    test_checkpoint_manifest.py
    test_config.py
    test_schema.py
    test_signal_pipeline.py
    test_boundary_model.py
    test_acquisition.py
    test_session_runner.py
  calibration/
    stage0_run_registry.csv
    stage0_summary.md
    execution_model.json
  data/
    linkage/
    raw_sensor/
    raw_questionnaire/
    algorithm_logs/
    processed/
    incidents/
  analysis/
    freeze_manifest.csv
    feasibility_summary.py
    execution_analysis.py
    boundary_analysis.py
    anchor_analysis.py
    qualitative_codebook.md
    final_decision_memo.md
  checkpoints/
```

Each source file has one responsibility: configuration loading, schema validation, signal extraction, boundary inference, acquisition, session orchestration, or immutable checkpointing. Do not combine all functions into the existing extended simulation file.

---

### Task 1: Governance, permissions, and named responsibility owners

**Owners:** Principal investigator, institutional ethics contact, vehicle safety lead, data protection lead.

**Files:**
- Create: `user_study/governance/ethics_submission_checklist.md`
- Create: `user_study/governance/protocol_v1.md`
- Create: `user_study/governance/risk_and_incident_plan.md`
- Create: `user_study/governance/privacy_and_retention_plan.md`
- Create: `user_study/governance/approvals_registry.csv`
- Create: `user_study/src/checkpoint_manifest.py`
- Create: `user_study/tests/test_checkpoint_manifest.py`

**Interfaces:**
- Consumes: approved design specification and institutional templates.
- Produces: draft approval gates consumed by later tasks; `approvals_registry.csv` columns `gate,authority,approval_reference,effective_date,expiry_date,status,document_path`; `write_manifest(root: Path, out: Path) -> int` used at every checkpoint.

- [ ] **Step 1: Create the directory tree and write the failing manifest test**

```python
def test_manifest_excludes_its_own_output(tmp_path):
    (tmp_path / "source.txt").write_text("source", encoding="utf-8")
    out = tmp_path / "manifest.csv"
    rows = write_manifest(tmp_path, out)
    self.assertEqual(rows, 1)
    self.assertNotIn("manifest.csv", out.read_text(encoding="utf-8"))
```

- [ ] **Step 2: Run the manifest test and confirm failure**

Run:

```powershell
python -m unittest user_study.tests.test_checkpoint_manifest -v
```

Expected: FAIL because `write_manifest` does not exist.

- [ ] **Step 3: Implement the checkpoint helper**

Walk files under `root`, exclude `out`, sort normalized relative paths, compute SHA256 and byte size, and write `path,size_bytes,sha256`. Never follow paths outside the requested root.

- [ ] **Step 4: Run the manifest test**

Expected: PASS; repeated execution over unchanged input produces identical rows.

- [ ] **Step 5: Create the protocol from the approved specification**

Copy the study objective, 12-probe structure, Stage 0 gate, stop rules, traffic-light criteria, recruitment, compensation, privacy, analysis populations, and incident reporting requirements without changing numerical thresholds.

- [ ] **Step 6: Create the approvals registry with explicit gates**

```csv
gate,authority,approval_reference,effective_date,expiry_date,status,document_path
ethics,institutional ethics committee,,,,not_approved,
route,controlled-route owner,,,,not_approved,
vehicle,vehicle safety lead,,,,not_approved,
insurance,institutional operations,,,,not_approved,
driver,vehicle safety lead,,,,not_approved,
data_protection,institutional data protection lead,,,,not_approved,
```

- [ ] **Step 7: Write incident escalation rules**

Include serious safety incident, physical threshold exceedance, unexecuted stop/skip, algorithm envelope violation, data breach, route/vehicle hazard, notification owners, immediate containment, documentation, and resumption authority.

- [ ] **Step 8: Review against authoritative requirements**

Verify the packet addresses risk/benefit, understandable informed consent, unconditional withdrawal, fair recruitment, compensation, privacy, algorithm transparency/control, emergency response, and result publication.

- [ ] **Step 9: Prepare the approval submission and activation rule**

The Task 1 registry remains `not_approved` until the forms, SOPs, software risk controls, Stage 0 protocol, privacy plan, and institutional attachments from Tasks 2–7 are complete. Submit the full packet through the institutional process. Do not change `status` to `approved` without a real reference and effective date. Stage 0 requires route, vehicle, insurance, driver, and data-protection gates; recruitment and participant testing additionally require ethics approval and Stage 0 go/no-go.

- [ ] **Step 10: Create a governance checkpoint**

Run:

```powershell
python .\user_study\src\checkpoint_manifest.py --root .\user_study\governance --out .\user_study\checkpoints\01_governance_sha256.csv
```

Expected: one manifest row per governance file; no direct participant identifier values.

---

### Task 2: Freeze the study configuration and canonical schema

**Owners:** Data/algorithm lead, study coordinator.

**Files:**
- Create: `user_study/config/study_config.json`
- Create: `user_study/config/data_dictionary.csv`
- Create: `user_study/src/config.py`
- Create: `user_study/src/schema.py`
- Create: `user_study/tests/test_config.py`
- Create: `user_study/tests/test_schema.py`

**Interfaces:**
- Consumes: approved design specification and versioned protocol draft; approval status remains an explicit runtime gate.
- Produces: `load_study_config(path: Path) -> StudyConfig`, `validate_trial_record(record: dict) -> None`, and canonical trial/participant schemas used by the session runner and analyses.

- [ ] **Step 1: Write failing configuration tests**

```python
def test_config_rejects_more_than_twelve_formal_trials():
    cfg = valid_config()
    cfg["trial_budget"] = 13
    with self.assertRaises(ValueError):
        load_study_config_dict(cfg)

def test_tau_sensitivity_is_frozen():
    cfg = load_study_config(FIXTURE)
    self.assertEqual(cfg.primary_tau, 0.70)
    self.assertEqual(cfg.sensitivity_tau, (0.60, 0.80))
```

- [ ] **Step 2: Run tests and confirm they fail**

Run:

```powershell
python -m unittest user_study.tests.test_config -v
```

Expected: FAIL because configuration loaders do not exist.

- [ ] **Step 3: Implement immutable configuration validation**

Required values include `trial_budget=12`, `initialization_trials=[1,2,3]`, `anchor_trials=[8,12]`, `adaptive_trials=[4,5,6,7,9,10,11]`, `primary_tau=0.70`, `sensitivity_tau=[0.60,0.80]`, one maneuver direction, safety thresholds, response anchors, rest limits, algorithm/model versions, and approved protocol version.

- [ ] **Step 4: Write failing schema separation tests**

```python
def test_safety_and_protocol_fields_are_independent():
    record = valid_trial_record()
    record["protocol_deviation"] = True
    record["safety_event"] = False
    validate_trial_record(record)

def test_analysis_record_rejects_direct_identifiers():
    record = valid_trial_record()
    record["participant_name"] = "example"
    with self.assertRaises(ValueError):
        validate_trial_record(record)
```

- [ ] **Step 5: Implement and test schema validation**

Run:

```powershell
python -m unittest user_study.tests.test_config user_study.tests.test_schema -v
```

Expected: PASS; missing required trial fields, illegal direct identifiers, out-of-range ratings, and illegal trial roles are rejected.

- [ ] **Step 6: Freeze data dictionary units and enum values**

The dictionary must define variable, scope, dtype, units, allowed values, missing rule, source, privacy class, model inclusion, and exclusion rule. Do not encode status only by color.

- [ ] **Step 7: Create checkpoint manifest**

Expected: config, dictionary, source, and tests all hashed in `02_config_schema_sha256.csv`.

---

### Task 3: Produce participant-facing forms and operator SOPs for ethics review and approved use

**Owners:** Study coordinator, ethics contact, safety lead.

**Files:**
- Create: all files under `user_study/forms/`
- Create: `user_study/config/questionnaire_codebook.csv`
- Create: all files under `user_study/sops/`

**Interfaces:**
- Consumes: `study_config.json`, institutional templates, exact wording from the specification, and data dictionary.
- Produces: exact participant questions, scale anchors, stop/skip script, daily checklists, and event reporting used in soft launch and main collection.

- [ ] **Step 1: Write the screening form**

Use the eight screening domains from the specification. Store only eligibility decision and minimum risk category in analysis data. Route any health-detail review to restricted operations records.

- [ ] **Step 2: Write consent and safety briefing**

State real-vehicle motion risks, algorithm role, driver veto, possible discomfort, confidentiality, exact GPS handling, compensation independent of completion, withdrawal without penalty, emergency contact, and data retention.

- [ ] **Step 3: Write baseline and trial-level forms**

Use the exact primary acceptability wording and all 1–7 anchors from the specification. The trial interface must show stop prominently on every screen and log response latency.

- [ ] **Step 4: Write post-session and interview forms**

Use the nine post-session statements and five interview questions verbatim. Mark the aggressive-probe item as reverse-interpreted in the codebook while preserving raw direction.

- [ ] **Step 5: Write driver/operator SOP**

Include roles, no-go weather/route conditions, command display, driver override, trial marker sequence, participant monitoring, rest, stop, recovery, sensor failure, algorithm failure, and incident escalation.

- [ ] **Step 6: Conduct comprehension review**

Two staff members unfamiliar with the project must independently explain: what acceptable means, who can stop, whether compensation changes, and whether the algorithm controls the vehicle. Any disagreement requires wording revision before ethics finalization.

- [ ] **Step 7: Submit forms/SOPs and activate only the approved versions**

After the institutional decision, incorporate only required approved amendments, update every version identifier, and record the real approval reference in `approvals_registry.csv`. Draft files must not be presented to participants.

- [ ] **Step 8: Create forms/SOP checkpoint**

Expected: all approved versions have unique hashes and their version identifiers match `study_config.json`.

---

### Task 4: Freeze and test the signal-processing pipeline

**Owners:** Sensor/data engineer, vehicle safety lead.

**Files:**
- Create: `user_study/src/signal_pipeline.py`
- Create: `user_study/tests/test_signal_pipeline.py`
- Create: `user_study/sops/stage0_execution_calibration_sop.md`

**Interfaces:**
- Consumes: raw timestamped IMU and trial markers.
- Produces: `extract_trial_features(samples, markers, config) -> TrialFeatures` containing vehicle-frame acceleration, jerk, duration, speed delta, QC status, and `realized_motion_intensity`.

- [ ] **Step 1: Build deterministic synthetic fixtures**

Create fixtures for constant acceleration, known ramp jerk, irregular timestamps, duplicate timestamps, dropped samples, gravity/orientation transformation, sensor clipping, and missing markers.

- [ ] **Step 2: Write failing physics and QC tests**

```python
def test_linear_ramp_returns_known_jerk():
    features = extract_trial_features(ramp_fixture(), markers(), config())
    self.assertAlmostEqual(features.peak_longitudinal_jerk, EXPECTED, places=2)

def test_missing_end_marker_is_not_usable():
    features = extract_trial_features(samples(), markers_without_end(), config())
    self.assertFalse(features.usable_for_boundary_model)
```

- [ ] **Step 3: Run tests and confirm failure**

Run:

```powershell
python -m unittest user_study.tests.test_signal_pipeline -v
```

Expected: FAIL because the pipeline does not exist.

- [ ] **Step 4: Implement coordinate, filter, derivative, and feature extraction**

Configuration must carry units, coordinate transform, gravity method, filter type/cutoff/order/phase, resampling rule, marker window, clipping rule, and intensity definition. No parameter may be inferred from participant outcomes.

- [ ] **Step 5: Validate against a known maneuver or reference IMU**

Record sign, magnitude, timing, phase, and speed-change agreement. A visually plausible chart is not enough; write numeric tolerances into the Stage 0 SOP.

- [ ] **Step 6: Run signal tests**

Expected: PASS for known signals; invalid marker, clipping, non-monotonic time, and excessive loss are explicitly flagged.

- [ ] **Step 7: Freeze feature pipeline version and checkpoint**

Expected: `feature_pipeline_version` in the config matches source hash and Stage 0 registry.

---

### Task 5: Implement the monotone boundary model and correct tau semantics

**Owners:** Algorithm lead, statistical reviewer.

**Files:**
- Create: `user_study/src/boundary_model.py`
- Create: `user_study/tests/test_boundary_model.py`
- Reference only: `comfort_boundary_bo_research_package/simulation/run_uncertain_input_bo_extended.py`
- Reference only: `long_horizon_audit/06_code_and_reproducibility_audit.md`

**Interfaces:**
- Consumes: valid `(m_t, y_t)` observations and frozen priors.
- Produces: `fit_boundary_model(observations, config) -> BoundaryPosterior`, with `probability(m)`, `boundary(tau)`, interval, monotonicity check, and censoring status.

- [ ] **Step 1: Write the tau-correctness test**

```python
def test_tau_boundary_is_not_midpoint():
    posterior = known_logistic_posterior(alpha=2.0, beta=1.0)
    b50 = posterior.boundary(0.50)
    b70 = posterior.boundary(0.70)
    self.assertNotEqual(b50, b70)
    self.assertLess(b70, b50)
```

- [ ] **Step 2: Write monotonicity and censoring tests**

```python
def test_probability_is_nonincreasing():
    posterior = fit_boundary_model(SYNTHETIC_DATA, config())
    probs = [posterior.probability(m) for m in GRID]
    self.assertTrue(all(a >= b for a, b in zip(probs, probs[1:])))

def test_right_censored_when_no_crossing_inside_envelope():
    posterior = fit_boundary_model(ALL_ACCEPTABLE_DATA, config())
    self.assertEqual(posterior.boundary(0.70).status, "right_censored")
```

- [ ] **Step 3: Run tests and confirm failure**

Expected: FAIL because the corrected model does not exist.

- [ ] **Step 4: Implement minimal Bayesian logistic/probit model**

Enforce nonnegative slope magnitude, return posterior uncertainty, distinguish estimated/left-censored/right-censored/not-estimable, and keep raw observations auditable. Do not use the historical real-vehicle questionnaire as label training data.

- [ ] **Step 5: Run recovery simulations**

Test low/high boundaries, noisy feedback, all acceptable, all unacceptable, repeated anchors, missing trials, and 6/8/10/12 usable-trial budgets. Record interval coverage and censoring, not only point MAE.

- [ ] **Step 6: Pass statistical review**

Reviewer verifies likelihood, prior, monotonicity, tau transformation, interval/censoring behavior, and small-sample limitations against the specification.

- [ ] **Step 7: Create model checkpoint**

Expected: model source, tests, simulation fixtures, and review note hashed; config contains the model version.

---

### Task 6: Implement uncertain-input acquisition and hard safety constraints

**Owners:** Algorithm lead, vehicle safety lead.

**Files:**
- Create: `user_study/src/acquisition.py`
- Create: `user_study/tests/test_acquisition.py`

**Interfaces:**
- Consumes: `BoundaryPosterior`, Stage 0 `ExecutionModel`, candidate commands, participant state, and safety envelope.
- Produces: `select_next_command(state, config) -> AcquisitionDecision`, containing candidate scores, exclusions, selected command, expected exposure, and versioned rationale.

- [ ] **Step 1: Write hard-envelope tests**

```python
def test_never_selects_command_outside_physical_envelope():
    decision = select_next_command(state_with_boundary_near_limit(), config())
    self.assertLessEqual(decision.command, config().max_command)

def test_driver_or_participant_downgrade_restricts_candidates():
    state = base_state(downgrade_active=True)
    decision = select_next_command(state, config())
    self.assertLessEqual(decision.command, state.downgrade_ceiling)
```

- [ ] **Step 2: Write truth/belief separation test**

The simulator must hold separate `execution_truth` and `execution_belief`. Changing truth bias without updating belief must change realized data but not candidate expectation until observations update the belief.

- [ ] **Step 3: Run tests and confirm failure**

Expected: FAIL because acquisition is not implemented.

- [ ] **Step 4: Implement expected information minus exposure/risk score**

Log every candidate, rejection reason, expected information, expected unacceptable probability, expected physical risk, final score, and selected command. Hard constraints filter before ranking.

- [ ] **Step 5: Add stop/downgrade state transitions**

Two consecutive unacceptable trials activate downgrade; discomfort 5/7 or safety 3/7 requires extended rest and readiness confirmation; stop rules return no command.

- [ ] **Step 6: Run stress tests**

Use biased/heteroscedastic/nonstationary execution truth, noisy responses, near-envelope posterior, all-unacceptable history, and algorithm latency failure. Expected: no unsafe command and explicit no-decision/fallback status.

- [ ] **Step 7: Obtain safety sign-off and checkpoint**

Safety lead reviews candidate envelope and independent driver veto; they do not approve based only on simulation performance.

---

### Task 7: Build the session runner, logging, and fail-safe dry-run harness

**Owners:** Software/data lead, study coordinator.

**Files:**
- Create: `user_study/src/session_runner.py`
- Create: `user_study/tests/test_session_runner.py`
- Create: `user_study/README.md`

**Interfaces:**
- Consumes: configuration, schema, signal pipeline, model, acquisition, operator input, and participant feedback.
- Produces: append-only NDJSON trial log, sensor-file references, participant state, next-command decision, stop/downgrade state, and checkpoint manifests.

- [ ] **Step 1: Write the complete trial-state test**

```python
def test_trial_sequence_is_three_initialization_seven_adaptive_two_anchor():
    session = simulated_session()
    roles = session.run_to_completion().trial_roles
    self.assertEqual(roles, [
        "initialization", "initialization", "initialization",
        "adaptive", "adaptive", "adaptive", "adaptive",
        "anchor", "adaptive", "adaptive", "adaptive", "anchor"
    ])
```

- [ ] **Step 2: Write fail-safe tests**

Test immediate stop, skip, driver veto, missing marker, sensor failure, acquisition exception, first low-command recovery, second algorithm failure termination, and hard safety event termination.

- [ ] **Step 3: Run tests and confirm failure**

Expected: FAIL because the runner does not exist.

- [ ] **Step 4: Implement append-only logging and role separation**

The runner must never overwrite raw sensor files or prior trial events. Driver input, operator input, participant response, model update, and acquisition decision receive separate timestamps and actor fields.

- [ ] **Step 5: Implement identity separation**

The session runner accepts only `participant_id`; schedule/contact lookup occurs outside the program. Schema validation rejects direct identifiers.

- [ ] **Step 6: Run full automated test suite**

Run:

```powershell
python -m unittest discover -s .\user_study\tests -v
```

Expected: all tests pass; no participant/session data needed.

- [ ] **Step 7: Conduct tabletop and stationary-vehicle dry runs**

Simulate 12 trials, stop at trials 1/6/12, skip, driver override, acquisition crash, sensor dropout, participant symptom, and incident escalation. Staff must follow SOP without developer coaching.

- [ ] **Step 8: Create software-lock checkpoint**

Expected: all source/config/tests/forms/SOPs hashed in `07_software_lock_sha256.csv`; later participant sessions reference this checkpoint.

---

### Task 8: Execute Stage 0 calibration and make the go/no-go decision

**Owners:** Vehicle safety lead, fixed driver, sensor engineer, algorithm lead.

**Files:**
- Create: `user_study/calibration/stage0_run_registry.csv`
- Create: `user_study/calibration/stage0_summary.md`
- Create: `user_study/calibration/execution_model.json`

**Interfaces:**
- Consumes: locked signal pipeline, controlled route, five target commands, 8+ repeats per target.
- Produces: validated `ExecutionModel`, physical envelope, Stage 0 decision, and command cue card.

- [ ] **Step 1: Complete daily vehicle/sensor/no-go checklist**

Do not start if weather, route, vehicle, driver, sensor synchronization, insurance, or emergency readiness fails.

- [ ] **Step 2: Run at least 40 balanced calibration maneuvers**

Five commands × at least eight repeats. Record initial speed, route context, command, realized features, driver override, protocol deviation, technical failure, and safety event.

- [ ] **Step 3: Run automated QC**

Expected: at least 95% full command-marker-sensor linkage; no unexplained hard-threshold exceedance; coordinate and unit checks pass.

- [ ] **Step 4: Analyze controllability and execution distribution**

Calculate target-realized Spearman correlation, ordered medians, within-target variation, heteroscedasticity, tail risk, duration, speed delta, and context effects. Use the exact go/no-go rules from the spec.

- [ ] **Step 5: Conduct multidisciplinary go/no-go review**

`go_continuous`: all gates pass. `revise_and_repeat`: technical/calibration issue is correctable. `fallback_templates`: continuous command not sufficiently controllable. `stop`: safety/governance failure.

- [ ] **Step 6: Freeze execution model and physical thresholds**

Write model version, input ranges, context limits, uncertainty parameters, validation metrics, and source data hashes. No participant starts on an unversioned model.

- [ ] **Step 7: Create Stage 0 checkpoint**

Expected: registry, summary, model, cue card, raw calibration references, and threshold sign-off all hashed.

---

### Task 9: Run two-person soft launch and protocol-version review

**Owners:** Study coordinator, safety lead, data/algorithm lead, PI.

**Files:**
- Update: `user_study/governance/approvals_registry.csv` only if amendments are actually approved.
- Create: `user_study/analysis/soft_launch_review.md`

**Interfaces:**
- Consumes: approved protocol, software-lock checkpoint, Stage 0 go decision.
- Produces: retain/separate decision for soft-launch data and permission to begin main cohort.

- [ ] **Step 1: Verify all participant-facing gates are active**

Ethics, route, vehicle, insurance, driver, data protection, software-lock, and Stage 0 status must all be approved/go with unexpired references. If any gate is missing, do not recruit or consent a participant.

- [ ] **Step 2: Recruit and consent the first two participants**

Use the same inclusion, compensation, questionnaires, safety rules, and 12-probe protocol intended for the main cohort.

- [ ] **Step 3: Run participant 1 and perform same-day safety/data review**

Review only operational metrics: safety, stop/skip, marker/sensor linkage, algorithm legality/latency, question comprehension, response time, and staff SOP adherence.

- [ ] **Step 4: Run participant 2 only if no red event occurred**

An unresolved red event pauses recruitment.

- [ ] **Step 5: Classify every proposed change**

Use the specification's material-change list. Material changes require version increment, appropriate ethics amendment, separate soft-launch analysis, and replacement recruitment.

- [ ] **Step 6: Apply soft-launch go criteria**

Required: 0 serious incidents, stop/skip executed correctly, no envelope violation, complete logs for at least 90% of started trials, and no recurring comprehension failure.

- [ ] **Step 7: Freeze main-study version and checkpoint**

Expected: `soft_launch_review.md` states `proceed`, `revise_repeat`, or `stop`, with evidence and source hashes.

---

### Task 10: Recruit and run the main cohort

**Owners:** Study coordinator, fixed driver, experimenter, data/algorithm operator.

**Files:**
- Append only: participant/session registries in restricted operations storage.
- Append only: `user_study/data/raw_sensor/`, `raw_questionnaire/`, `algorithm_logs/`, `incidents/`.
- Create after every session: `user_study/checkpoints/session_<session_id>_sha256.csv`.

**Interfaces:**
- Consumes: main-study frozen version and approved scheduling pool.
- Produces: 12–16 valid completed participant sessions plus full feasibility records for all started participants.

- [ ] **Step 1: Recruit 16–18 candidates without susceptibility enrichment**

Use fair recruitment and neutral language. Do not advertise algorithm benefits or pressure participants to tolerate high motion.

- [ ] **Step 2: Schedule with cancellation/no-go flexibility**

Reserve weather/vehicle contingency slots and at least two replacement slots.

- [ ] **Step 3: Perform pre-session checklist**

Confirm approvals current, staff roles, vehicle/route/weather, sensor sync, algorithm/config hashes, participant eligibility, consent, baseline, and emergency readiness.

- [ ] **Step 4: Execute session exactly once per participant**

Run familiarization, 12 formal probes or early stop, post questionnaire, interview, recovery check, and compensation. Do not repeat a participant because their responses are inconvenient.

- [ ] **Step 5: Perform immediate post-session QC**

Confirm raw files exist, hashes recorded, 12 or fewer formal trials, stop/skip/override captured, incidents documented, and no direct identifiers entered analysis/logging files.

- [ ] **Step 6: Apply ongoing pause rules**

Pause for any red event or recurring amber pattern. Do not wait until all participants finish to review safety.

- [ ] **Step 7: Stop recruitment at the predeclared target**

Complete between 12 and 16 valid sessions; do not extend based on favorable or unfavorable boundary results without a new approved plan.

---

### Task 11: Freeze data, run QC, and produce processed datasets

**Owners:** Data lead, independent QC reviewer.

**Files:**
- Create: `user_study/analysis/freeze_manifest.csv`
- Create: processed trial- and participant-level CSV files under `user_study/data/processed/`
- Create: `user_study/analysis/data_qc_report.md`

**Interfaces:**
- Consumes: all raw/session checkpoint manifests and frozen pipeline.
- Produces: immutable analysis freeze, trial usability flags, analysis-population membership, and QC report.

- [ ] **Step 1: Reconcile session inventory**

Every enrolled participant must map to consent status, started/completed status, stop reason, compensation, and data disposition. Every started trial must have a retained record even if unusable for boundary inference.

- [ ] **Step 2: Verify hashes and raw-data immutability**

Compare each session manifest with current raw files. Any mismatch blocks analysis until explained.

- [ ] **Step 3: Generate processed trial features using the locked pipeline**

No per-participant manual filter or window tuning. Save source hash and feature pipeline version on every row.

- [ ] **Step 4: Apply usability and population rules**

Retain invalid trials in feasibility/safety tables; exclude from boundary model only under predeclared rules. Early stops remain in feasibility population.

- [ ] **Step 5: Run privacy scan**

Search processed/analysis files for names, phone numbers, emails, IPs, device IDs, and exact GPS. Confirm linkage path is not referenced by analysis code.

- [ ] **Step 6: Independent QC sign-off**

Reviewer samples at least one initialization, adaptive, and anchor trial per participant; checks command, markers, realized features, feedback, event flags, and source lineage.

- [ ] **Step 7: Freeze analysis manifest**

Expected: hashes for raw references, processed tables, code, config, questionnaires, and exclusion decisions.

---

### Task 12: Analyze feasibility, execution, boundary, anchors, and interviews

**Owners:** Statistical lead, HCI qualitative lead, independent reviewer.

**Files:**
- Create: `user_study/analysis/feasibility_summary.py`
- Create: `user_study/analysis/execution_analysis.py`
- Create: `user_study/analysis/boundary_analysis.py`
- Create: `user_study/analysis/anchor_analysis.py`
- Create: `user_study/analysis/qualitative_codebook.md`

**Interfaces:**
- Consumes: frozen processed data and analysis manifest.
- Produces: tables/figures for predefined feasibility endpoints, execution validity, interval/censoring, anchors, user cost, UX, carryover, and qualitative themes.

- [ ] **Step 1: Produce participant flow and denominators**

Report recruited, screened, excluded, enrolled, started, completed 10+, completed 12, stopped, and boundary-population counts with reasons.

- [ ] **Step 2: Produce primary feasibility table**

Include completion, linkage, usable trials, normal algorithm decisions, failures/recoveries, stop/skip/override, deviations, safety events, timings, and boundary status.

- [ ] **Step 3: Produce execution diagnostics**

Target-realized scatter, bias, heteroscedasticity, anchor execution repeatability, Stage 0 vs participant-session drift, and context notes.

- [ ] **Step 4: Fit individual boundary models**

Report posterior median/interval and estimated/left/right-censored/not-estimable status at tau 0.70 plus sensitivity at 0.60/0.80. Do not compute historical-data ground-truth MAE.

- [ ] **Step 5: Analyze anchors and user cost**

Report command/realized repeatability, response agreement conditional on realized closeness, unacceptable count, cumulative/max discomfort, minimum safety, and overshoot only when boundary estimable.

- [ ] **Step 6: Analyze UX and qualitative data**

Report median/IQR/individual points for burden, control, trust, understanding, personalization, willingness, and aggressive-probe item. Code interviews with a documented codebook and retain negative cases.

- [ ] **Step 7: Run carryover sensitivity**

Assess trial order, previous discomfort, rest duration, and cumulative discomfort. If they materially affect the curve, recommend time-aware calibration.

- [ ] **Step 8: Independent results audit**

Reviewer traces every primary number to frozen rows, checks units and denominators, confirms simulation and human results are separated, and verifies no superiority claim.

---

### Task 13: Apply progression criteria, report, archive, and decide next study

**Owners:** PI, safety lead, statistical lead, study coordinator.

**Files:**
- Create: `user_study/analysis/final_decision_memo.md`
- Update: `user_study/README.md`
- Create: final archival checkpoint under `user_study/checkpoints/`.

**Interfaces:**
- Consumes: audited results and incident/deviation summary.
- Produces: `go`, `modify_and_repeat_feasibility`, or `stop` decision and a reproducible archive.

- [ ] **Step 1: Score every Green/Amber/Red criterion**

Use prespecified denominators. Do not change thresholds to match observed data.

- [ ] **Step 2: Write claim-bounded conclusions**

Allowed: operational feasibility, command-realized uncertainty, participant understanding/control/burden, interval/censoring, anchor repeatability, and protocol amendments. Not allowed: algorithm superiority, population efficacy, universal tau, or exact SafeOpt guarantee.

- [ ] **Step 3: Decide the next study**

`go`: design a larger repeatability or comparator study. `modify_and_repeat_feasibility`: specify exact changes and repeat soft launch. `stop`: document safety/scientific reasons and do not repurpose failed protocol as efficacy evidence.

- [ ] **Step 4: Archive approvals, versions, logs, code, forms, data dictionaries, analyses, and decisions**

Keep linkage and exact GPS under stricter access and retention rules than analysis data.

- [ ] **Step 5: Run final verification**

Run:

```powershell
python -m unittest discover -s .\user_study\tests -v
python .\user_study\src\checkpoint_manifest.py --root .\user_study --out .\user_study\checkpoints\13_final_archive_sha256.csv
```

Expected: all tests pass; final manifest exists; no unresolved red event or unexplained hash mismatch.

---

## Calendar after approvals are effective

| Period | Outcome |
|---|---|
| Weeks 1–2 | Config/schema, forms/SOPs, signal pipeline, BO model, acquisition, runner and automated tests locked |
| Week 3 | Tabletop, stationary-vehicle and full-route dry runs; software-lock checkpoint |
| Week 4 | Stage 0 40+ maneuvers, execution model, physical envelope and go/no-go |
| Week 5 | Two-person soft launch and version review |
| Weeks 6–7 | Main recruitment and participant sessions |
| Week 8 | Data freeze, privacy/QC and processed datasets |
| Week 9 | Feasibility, execution, boundary, anchor, UX and qualitative analysis |
| Week 10 | Independent audit, traffic-light decision memo, report and archive |

Ethics, route, vehicle, insurance, or amendment review time precedes this schedule and cannot be compressed by starting participant recruitment early.

## Completion definition

The project is complete only when:

- 12–16 valid completed participants are available or a Red stop decision is formally documented;
- all started participants remain in feasibility accounting;
- all raw/processed/log/form versions are traceable by hash;
- no serious or unresolved safety/data event is hidden;
- BO closed-loop, failure recovery, stop/skip and driver override are reported;
- boundary results use realized motion and correct tau/censoring semantics;
- questionnaires, data dictionary, exclusions and progression criteria match the approved protocol;
- the final memo chooses go/modify/stop without claiming algorithm superiority.
