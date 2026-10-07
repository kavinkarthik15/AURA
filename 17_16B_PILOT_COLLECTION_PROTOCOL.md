# 17.16B Pilot Collection Protocol Audit

Status: `AUDIT_REVISIONS_REQUIRED`

## 1. Selected target

Selected target: `python`

- target_name: `python`
- target_dimension: `skill`
- target_scale: `0-100`
- valid_range: `0` to `100`

This selection remains the strongest first pilot target because it is already represented in AURA's current state model and is numerically scored on an existing 0-100 skill scale. It is still a design target rather than a proven measurement instrument.

## 2. Measurement instrument status

`measurement_instrument_ready = false`

Versioned v1 blueprint and Form A/B JSON artifacts now define the item set, item domains, objective scoring, and form hashes. These artifacts are still unapproved and must not be used for collection. The code-execution path is a restricted-exec subprocess with a timeout, not a secure sandbox; this is a technical blocker for participant-submitted code.

- 10 items per form, each worth 10 points
- actual computed domain points are tested against the blueprint
- code tasks use deterministic function contracts and test cases
- code outputs are compared by behavior, not source text
- required submission validity criteria include completeness, evidence ID, valid form/version/hash, valid timestamps, and verified score transformation

The scoring helper does not yet enforce the full evidence-ID, timestamp, assignment-phase, and provenance lifecycle end-to-end. Collection remains blocked.

### Required instrument definition before collection

Before collection, the protocol must define:

- assessment name and version
- structure (for example: x coding tasks, y multiple-choice items, z rubric dimensions)
- scoring rule and per-task weightings
- raw score range
- deterministic transformation from raw score to AURA 0-100 value
- baseline and follow-up use of the same instrument or a parallel validated form
- minimum completeness and quality thresholds
- rule for invalid or incomplete assessment records

If no implementation yet exists, the instrument remains `MEASUREMENT_INSTRUMENT_REQUIRES_FINALIZATION`.

## 3. Baseline and follow-up assessment design

Counterbalanced assignment:

- deterministic SHA-256-based user-ID assignment to AB or BA
- AB: T0 Form A, T1 Form B
- BA: T0 Form B, T1 Form A
- participant does not choose the form; the assigned follow-up form is validated

Status: `PARALLEL_FORMS_BLUEPRINT_MATCHED_NOT_EMPIRICALLY_EQUIVALENT`. No form-equivalence claim is made.

## 4. Score transformation status

`score_transformation` is frozen as an identity mapping for these forms.

Each form has 10 items x 10 points = 100 possible points. Therefore `aura_python_skill = raw_score` (0-100), without post-hoc, data-dependent, MG, or base-prediction adjustment. The AURA scale remains operational and is not claimed as an externally validated psychometric scale.

## 5. Action module definition status

`action_module_ready = false`

The versioned module manifest exists and is hash-checked, but remains unapproved and collection-blocked. It specifies:

- module identifier/version
- content scope
- required exercises
- expected duration
- completion threshold
- permitted retries
- completion evidence
- start timestamp and completion timestamp

Without a fixed module version and content description, the action is not standardized and could vary by participant.

## 6. External-learning / confounder metadata

The pilot should record structured metadata for real-world exposures during the 7-day horizon, including:

- external_python_learning_minutes
- other_python_courses
- project_activity
- ai_assistance_used
- relevant_classroom_instruction

These are confounder descriptors only and must not be used to condition predictions or to create outcome values.

## 7. Horizon and timing window

Primary horizon: `7 days`

Allowed timing window: `T+7 days` to `T+10 days`

This is a pragmatic feasibility horizon, not a scientifically proven optimum. It is acceptable as a preregistered pilot horizon if described accordingly, but it must remain explicitly labeled as a feasibility horizon rather than a validated optimum.

## 8. Primary endpoint

Future primary endpoint:

- `delta_error = abs(observed_outcome - mg_prediction) - abs(observed_outcome - base_prediction)`
- negative values favor MG on that episode

The formula is frozen, but it is not calculated in this audit. The future confirmatory analysis should aggregate episode-level values using one pre-registered summary statistic; other metrics remain secondary/exploratory.

## 9. Delta_min status

`delta_min = TO_BE_ESTIMATED_FROM_PILOT`

This is the correct status. No numeric threshold should be invented from current synthetic or heuristic assumptions. The pilot should estimate:

- paired delta_error distribution
- SD of paired delta_error
- measurement noise
- missingness
- exclusion rate

Then the final delta_min should be frozen before the confirmatory cohort.

## 10. Sample-size status

`sample_size_strategy = PILOT_SAMPLE_ONLY`

The protocol may include a pragmatic Stage A feasibility target such as 30-50 valid episodes, but this must not be described as statistically powered. The confirmatory sample size remains `PENDING_PILOT_VARIANCE_ESTIMATE`.

## 11. Leakage / blinding controls

Where practical, the person entering outcome data should not see:

- base prediction
- MG prediction

The collection interface must not pre-populate predicted values. The protocol must document any unavoidable lack of perfect blinding.

Additional controls remain:

- prediction freezing before action
- immutable protocol and prediction values after freeze
- no retrospective cohort editing
- separate synthetic and real outcome stores

## 12. Protocol and artifact hashes

- protocol_version: `2026-10-07-audit-v2`
- protocol_hash is stored in `17_16B_PILOT_PROTOCOL_CONFIG.json`
- blueprint, Form A, Form B, and module IDs, versions, and SHA-256 hashes are explicitly bound in that config

This hash supports integrity tracking for protocol changes. It is not a substitute for scientific validation.

## 13. Collection blockers

`collection_ready = false`

Current blockers:

- submitted Python is not isolated from the host OS; the restricted execution mechanism is not a secure sandbox
- evidence ID, timestamps, assignment phase, and provenance validity are not enforced end-to-end by a collection workflow
- explicit pilot-owner approval remains pending

## 14. Final status flags

- `protocol_design_ready`: true
- `measurement_instrument_ready`: false
- `action_module_ready`: false
- `collection_ready`: false
- `effectiveness_evaluation_status`: `BLOCKED_INDEPENDENT_OUTCOME_DATA_REQUIRED`
- `eligible_real_outcomes`: `0`
- `analysis_performed`: `false`

## 15. The correct conclusion

The protocol remains a design scaffold and is not collection-ready. The artifacts have reproducible hashes and deterministic scoring definitions, but the execution-security and evidence-validation blockers remain open. Effectiveness evaluation also remains blocked until independent outcomes exist.

This is the correct stopping point for the current phase: a blocked audit-safe design, not a collection launch.

## 16. Final technical approval gate

- `security_execution_gate`: `FAIL` (no Docker runtime or digest-pinned worker image is available on the audit host)
- `hash_binding_gate`: `PASS`
- `measurement_logic_gate`: `PASS` for the verified 10-item/100-point raw score and identity mapping; this does not certify execution security or collection readiness
- `action_module_gate`: `PASS` for exercise/domain/required/optional/retry consistency and behavioral exercise scoring
- `protocol_integrity_gate`: `PASS` for artifact binding, protocol hash, and blocked readiness/approval state
- `technical_artifacts_complete`: `false`
- `RECOMMENDATION`: `REVISIONS_REQUIRED`

The development executor runs restricted code in a subprocess, but it is not OS-level isolation and Python object introspection can escape the restriction. Participant-facing assessment and module execution now default to `SECURE_CONTAINER`; the development executor must be explicitly selected and is not approved for real submissions. Docker CLI/runtime and a digest-pinned worker image were unavailable on this audit host, so the secure execution and end-to-end evidence lifecycle remain blockers. Syntax errors and runtime errors are surfaced as failed execution results, and worker execution is timeout- and output-bounded; these controls do not make the restricted development executor safe.

### Version-freeze policy

Before human owner approval, v1 artifacts may still be corrected during audit. After owner approval and the first real collection, v1 becomes immutable. Any subsequent change requires a new v2 artifact; an approved v1 artifact must not be changed in place.


## 17. Assessment evidence lifecycle

Assessment sessions are validated against participant assignment, episode owner/pilot, baseline/follow-up phase, bound form version/hash, timezone-aware start/submission timestamps, completeness, identity score mapping, and ASSESSMENT-only provenance. Sessions and finalized outcome references use an append-only SQLite evidence store with uniqueness constraints and update/delete triggers. A follow-up can become an observed outcome only after a baseline exists, persisted successful practice-module evidence matches the module binding, and follow-up timing is within T+7 through T+10. The evidence lifecycle requires SECURE_CONTAINER scoring; the development executor is rejected for that mode. A valid real container-backed lifecycle has not been run on this host.
