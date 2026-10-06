# 17.16B Architecture and Ground-Truth Assessment

**Assessment date:** 2026-10-04  
**Status:** BLOCKED - no verified independent outcome cohort in the repository  
**Scope:** Read-only repository inspection; no experiment execution or production/data changes

## Executive Finding

The repository contains state-shaped fields named `state_after`, `actual_state`, and `actual_future_state`, but field names do not establish that values were independently observed. The available experience corpora are documented as synthetic, simulation paths produce predictions/branches rather than observed outcomes, and the execution/logging path does not itself measure a user's resulting state.

The proposed approach of matching the 2,400 17.15 rows to `experiences.json` is not a valid effectiveness evaluation:

- `docs/specifications/milestone_sprint5.md` explicitly says experience data is synthetic for testing and iteration.
- The production default `ExperienceService` loads both `experiences.json` and `synthetic_experiences.json`.
- `TransitionEngine` uses those same experiences to produce the legacy baseline. Evaluating against their `state_after`/`state_delta` would reuse training evidence as test outcomes (leakage/circularity).
- 17.15 rows have no `experience_id`, `seed`, context, event timestamp, or actual resulting state. They are four repeated scenario signatures, 600 rows per signature, not 2,400 independent action outcomes.
- No repository path captures independently measured post-action user state and links it to an executed single action with measurement provenance.

**Decision:** Do not implement or run 17.16B effectiveness statistics against current repository data. Obtain or prospectively collect eligible observed action-outcome records first. The existing 17.15 and 17.16A results remain mechanical/descriptive evidence only, not predictive-effectiveness evidence.

## 1. Scope and Files Inspected

Inspection covered the following relevant code and artifacts:

- Experience/state: [backend/models/experience.py](backend/models/experience.py), [backend/models/user_state.py](backend/models/user_state.py), [backend/models/simulated_state.py](backend/models/simulated_state.py), [backend/models/decision_outcome.py](backend/models/decision_outcome.py), [backend/models/experience_log.py](backend/models/experience_log.py)
- State/prediction: [backend/services/state_service.py](backend/services/state_service.py), [backend/services/state_history.py](backend/services/state_history.py), [backend/services/state_similarity.py](backend/services/state_similarity.py), [backend/services/transition_engine.py](backend/services/transition_engine.py), [backend/services/simulation_engine.py](backend/services/simulation_engine.py), [backend/services/digital_twin.py](backend/services/digital_twin.py), [backend/planning/probabilistic_transition.py](backend/planning/probabilistic_transition.py)
- MG: [backend/compatibility/mg_compatibility.py](backend/compatibility/mg_compatibility.py), [backend/compatibility/mg_config.py](backend/compatibility/mg_config.py)
- Logging/evaluation: [backend/services/execution_engine.py](backend/services/execution_engine.py), [backend/services/experience_logger.py](backend/services/experience_logger.py), [backend/services/experience_service.py](backend/services/experience_service.py), [backend/services/prediction_error_evaluator.py](backend/services/prediction_error_evaluator.py), [backend/services/closed_loop_validation.py](backend/services/closed_loop_validation.py), [backend/experiments/experiment_runner.py](backend/experiments/experiment_runner.py)
- Data: [backend/data/experiences.json](backend/data/experiences.json), [backend/data/synthetic_experiences.json](backend/data/synthetic_experiences.json), [backend/data/experience_dataset.json](backend/data/experience_dataset.json), [backend/data/user_state.json](backend/data/user_state.json), research benchmark generator/data and 17.15/17.16A artifacts
- Existing tests: [backend/tests/test_transition_engine.py](backend/tests/test_transition_engine.py), [backend/tests/test_simulation_engine.py](backend/tests/test_simulation_engine.py), [backend/tests/test_experience_logger.py](backend/tests/test_experience_logger.py), [backend/tests/test_complete_aura_pipeline.py](backend/tests/test_complete_aura_pipeline.py), and related evaluation/closed-loop tests
- Repository instructions: no `AGENTS.md` files were found.

No files were modified during this inspection. The only outputs created by this task are this report and the requested checkpoint.

## 2. Actual Data Flow

### User state

`StateService.load_state()` reads one `UserState` snapshot from `backend/data/user_state.json`. `update_skill`/`increment_skill` can mutate a value and `save_state()` persists the whole document. The stored document has a `last_updated` timestamp, but there is no event/action ID, paired pre-state snapshot, measurement source, or action-linked post-state record. A current snapshot therefore cannot establish which action caused a change.

### Experience and action

`Experience` is a schema for a transition record: `state_before`, `action`, `context`, `state_after`, and `state_delta`, plus outcome/confidence/weight fields. The schema validates that mappings are non-empty where required; it does not establish how the state was measured or whether the event was real. `state_delta` can be derived by `build_experience_delta(state_before, state_after)`.

`ExperienceService` reads the file corpus and, by default, appends `synthetic_experiences.json` to `experiences.json`. There is no provenance/source field that would separate measured episodes from generated examples.

### Base prediction

`TransitionEngine` calls `find_similar_transitions()` and computes weighted averages of matching experiences' `state_delta` and `outcome_value`. The similarity function considers state overlap and action-token overlap; it does not compare context. Its fallback action similarity is positive even when tokens do not overlap, and it admits every positive combined score without an explicit minimum threshold. In the normal engine configuration, the loaded experience corpus is therefore the prediction evidence, not an independent outcome source.

`SimulationEngine.simulate_action()`:

1. Gets predicted growth and success probability from `TransitionEngine`.
2. Adds predicted growth to a copy of current state and optionally applies calibration.
3. Labels the predicted outcome from predicted success probability.
4. Builds a `legacy_prediction` containing `current_state`, `predicted_future_state`, confidence, and predicted outcome.
5. Calls MG to produce an adjusted prediction.

This function predicts; it does not execute a human action or observe a future state.

### MG correction

`MGCompatibilityLayer.apply()` extracts motivation/goals signals, computes the frozen linear correction, and applies it to recognized future-state keys with 0-100 clamping. It returns a corrected prediction and metadata. It does not mutate user state, execute an action, or produce an outcome. The 17.15 shadow recorder captures these predictions and diagnostics only.

### Simulation and `state_after`

`DigitalTwin` and `SimulationEngine.simulate_plan()` advance local state by using predicted states as the next simulated state. `ProbabilisticTransitionModel` creates possible/expected states from hand-coded action rules and probabilities. These are model-generated or simulated states, not observed results.

`ExecutionEngine` records whether action items were marked completed, failed, or skipped. It does not update skill values or measure post-action state. `ExperienceLogger.log_experience()` accepts `actual_state` as a required caller-supplied argument and stores it; it has no independent observation/validation mechanism. The logger call sites in the repository are tests, and tests pass hard-coded `actual_state` dictionaries. A field accepted by the logger is not by itself a ground-truth collection mechanism.

`PredictionErrorEvaluator` can compute errors when given an `actual_state`, but cannot certify its provenance. `ExperimentRunner.generate_synthetic_experiences()` explicitly generates synthetic values by adding seeded noise to a base prediction.

## 3. Ground-Truth Source Classification

| Candidate source | Classification | Finding / eligibility |
|---|---|---|
| `backend/data/experiences.json` (15 rows) | **C - Simulated/synthetic outcome**; **F - not suitable as independent ground truth** | Sprint 5 documentation explicitly identifies experience data as synthetic for testing/iteration. Rows have `state_after`, but no measurement provenance. Not eligible. |
| `backend/data/synthetic_experiences.json` (22 rows) | **C - Simulated/synthetic outcome** | Explicitly synthetic by file and service semantics. Loaded into the standard prediction corpus. Not eligible. |
| `backend/data/experience_dataset.json` (341 rows) | **C/F - synthetic or unverified derived/logged values; not established observations** | Sprint 9.1 calls the experience dataset a synthetic corpus. Rows have `actual_state` but no user ID, measurement source, measurement time/horizon, or provenance. Only 69 distinct execution IDs occur in 341 rows. `ExperienceLogger` accepts caller-provided values; tests write literal examples and some use the default persistent path. Do not treat as verified ground truth without external provenance audit. |
| `backend/experiments/data/research_benchmark_v1_seed_*.json` | **C - simulated/synthetic outcome** | `ResearchBenchmarkGenerator` explicitly generates synthetic experiences. Its `actual_future_state` is constructed from predicted values plus category-specific bias/noise. A train/held-out split does not make synthetic labels observed outcomes. |
| `backend/experiments/experiment_runner.py` output | **C - simulated/synthetic outcome** | `generate_synthetic_experiences()` generates outcomes from a base prediction plus seeded random deviation. Not an empirical target. |
| `DecisionOutcome.actual_state` and prediction/closed-loop evaluators | **E - supplied/derived value until provenance is established** | The schema allows an optional state and the evaluator computes errors from it. Neither schema nor evaluator acquires/verifies an observation. Existing tests supply fixture states. |
| `SimulationEngine` / `DigitalTwin` / probabilistic transition output | **D - model-generated prediction** or **C - simulated state** | Future states are calculated/branched from existing model logic. Never use these as actual outcomes for evaluating the same prediction. |
| `StateService` current persisted snapshot | **F - not suitable as an action-linked ground-truth record** | A latest state snapshot exists, but no recorded action linkage, fixed follow-up horizon, source, or paired pre-state for each 17.15 event. |
| 17.15 `legacy_prediction` and `mg_shadow_prediction` | **D - model-generated prediction** | Both are forecasts. The artifact contains no actual resulting state. |
| Independently measured, action-linked post-action state | **A/B - potentially valid, if independently sourced and held out** | No qualifying cohort or source was found in this repository. This is the required data for 17.16B. |

**Conclusion:** No source currently qualifies as verified true observed ground truth (A) or verified historical observed experience (B) for this study. The `state_after` label alone is insufficient evidence.

## 4. 17.15 Matching Feasibility

The frozen event artifact has 2,400 rows, but its design and schema make it unsuitable as a 2,400-unit evaluation cohort:

- Read-only inventory found exactly four unique `(action, category, current_state)` scenario signatures, each repeated 600 times.
- Every event has `experience_id=null`, `seed=null`; there is no event timestamp, context, or `actual_state_after`.
- The four scenario signatures are predetermined validation inputs, not 2,400 independently executed user actions. The 600 `category=null` / empty-state / unknown-action rows are a robustness case, not a defined skill forecast target.
- 17.15 invokes the same four inputs for each seed and simulation index. MG rollout is 100%, and the correction is deterministic; the seed does not create independent outcomes. The seed is not written into each event.
- The 17.16A script reconstructs seed groups by row position (`400` rows per presumed seed); this is not an event-level recorded seed. Its per-seed equality is a consequence of repeated inputs/deterministic computation, not evidence of cross-seed outcome generalization.
- Category and action matching would be weak for several rows (`Complete Python Basics`, `Lead Large Team Project`, `Unknown action`). The current matcher uses token overlap/state values, ignores context, has no explicit acceptance threshold, and is not an outcome-linking rule.
- Event state keys do not align fully with MG's recognized correction keys or the sparse experience data. A valid metric must predefine the measured dimensions; missing keys must not silently become zero.
- Matching would reuse the same small experience records many times. Those records are already part of the base predictor's corpus, so the outcome would not be independent of the prediction being evaluated.

**Effective evaluation cohort in the present repository: zero verified independent observed outcomes.** Four scenario signatures are not four observed outcomes; 2,400 repetitions do not increase ground-truth sample size.

## 5. Scientific Risk Assessment

| Risk | Level | Why it applies |
|---|---|---|
| Data leakage / train-test contamination | **Critical** | `TransitionEngine` prediction uses the same experience records proposed as targets. The standard service also loads synthetic records. |
| Circularity | **Critical** | Using the legacy prediction as a fallback “actual” would guarantee a baseline match and mechanically bias comparison; even tagging it synthetic cannot make it an outcome. The earlier `17_16B_OUTCOME_GENERATION_READY.md` and `RESEARCH_CHECKPOINT_17_16B_ARCHITECTURE_READY.json` propose this invalid fallback and must be treated as superseded by this assessment. |
| Synthetic ground truth mislabeling | **Critical** | Sprint milestone docs and the benchmark generator explicitly identify/generate synthetic outcomes. |
| Pseudoreplication | **Critical** | 2,400 rows are four repeated scenario inputs; the same historical rows could be reused for every row. Event-level tests would inflate n and understate uncertainty. |
| Dependence / user clustering | **High** | The 15-row experience corpus names one `user_001`; the larger logged dataset has no user ID. Repeated episodes from one person would not be independent population units. |
| Temporal leakage | **High** | 17.15 rows have no event time or linked experience ID; no temporal train/test ordering can be reconstructed from the event record. |
| Action/context mismatch | **High** | No context is recorded in 17.15, and existing matching ignores context. Some action pairs only have superficial token overlap. |
| Target/measurement mismatch | **High** | No fixed prediction horizon, measurement source, state schema/version, or action-linked post-state is recorded. |
| Insufficient sample size | **Critical** | Verified independent outcomes: zero. The 15 historical rows are documented synthetic examples, not empirical sample size. |

The existing 17.16A correction-pattern analysis remains descriptive of the four scripted inputs. It does not provide predictive-effectiveness evidence. Its seed breakdown is reconstructed, not stored, and should not be cited as independent seed-level validation.

## 6. Proposed Valid 17.16B Design (Not Yet Frozen or Executed)

### Evaluation population and unit

Use prospectively collected, real, completed single-action experience episodes from the intended AURA population. One evaluation unit is one unique action episode with a verified pre-action state and an independently measured post-action state. The current repository has no eligible units.

Before collection, specify whether the claim is within-user future forecasting, across-user generalization, or both. For a personalized model, keep users separate in reporting and treat user as the top-level dependence cluster. One user's repeated episodes cannot support a claim about a population of users.

### Prediction horizon and ground-truth definition

At time `t0`, freeze the measured initial state, standardized action ID, relevant context, model version, and both predictions before the outcome is observed. Define one common follow-up horizon in advance (for example, a specified assessment window after action completion) and use the same validated measurement process for `state_after` at `t1`. The repository does not define that horizon or measurement instrument; these are blocking protocol decisions, not values to infer after the fact.

Ground truth must be an independently observed state from the same episode, with source/measurement method, timestamps, state schema/version, and linkage ID. Do not aggregate neighbors to synthesize a label, use a model prediction as a fallback label, or reuse an outcome that trained either predictor.

### Inclusion and exclusion

**Include:** unique real action episodes; action actually completed and status evidenced; same event has pre-action state, action, context, both frozen predictions, independently measured post-state, timestamps and provenance; dimensions follow one predeclared schema and compatible scale; prediction was recorded before the outcome.

**Exclude:** synthetic/generated/benchmark records; simulated transitions; incomplete or unverified actions; missing or untraceable post-state; events used to fit/calibrate the base model or coefficients; post-outcome predictions; duplicate/replayed rows; mismatched state schema; and empty/unknown-state cases with no predeclared measurable target. Preserve exclusion reasons and counts.

### Matching and leakage controls

Do not match 17.15 rows post hoc to `experiences.json`. Pair base and MG forecasts directly within the same newly observed event ID. If historical observations are later recovered, first audit row-level provenance, then perform a time-ordered split: only records strictly before the evaluation cutoff may train the base predictor; every evaluation episode must be held out from transition fitting, MG fitting, coefficient selection, calibration, and threshold selection. Deduplicate by source episode and prevent a single outcome from serving as labels for multiple purported independent rows.

For a new prospective cohort, both predictions must be generated from exactly the same pre-action state/action/context, with frozen 17.13B coefficients. No tuning or refitting during evaluation. The 17.15 frozen data remains untouched and is not retroactively assigned outcomes.

### Error and comparison metric

The target is a vector of skill-state values, not an outcome label. Predefine a stable set of numeric skill dimensions and scale. For episode `i`, primary score should be per-event mean absolute error over the same predeclared observed dimensions:

`MAE_base_i = mean_k(abs(actual_ik - base_prediction_ik))`

`MAE_MG_i = mean_k(abs(actual_ik - MG_prediction_ik))`

`delta_i = MAE_MG_i - MAE_base_i`

Both forecasts are scored against the same actual state. Use only valid shared dimensions specified before results; do not take a union and treat missing dimensions as zero. Also report per-skill errors, and report state-level and growth/delta errors separately if both are scientifically relevant. Do not call a prediction shift an improvement.

### Dependence-aware statistical analysis

The paired unit is the same episode scored under both predictors, but episodes may be clustered within a user and over time. The current data cannot support any test. For a future multi-user cohort, pre-register a cluster-aware primary analysis: estimate mean paired `delta`; obtain a confidence interval by resampling users (and, if needed, time blocks within user); use a paired sign-flip/permutation procedure at the independent cluster level for the primary null test. Do not use 2,400 row-level t-tests or treat simulation seeds as independent subjects. Report medians, distribution, win/tie/loss proportions, per-skill, per-category, and per-user results descriptively. Select any supplementary paired t/Wilcoxon test only after validating the actual independent-unit structure and distribution.

### Protocol decisions to freeze before outcome access

- **Alpha:** two-sided `0.05` for the primary paired test.
- **Practical threshold:** define a domain-approved minimum meaningful improvement `delta_min` in MAE units before data collection/unblinding; repository evidence does not justify a numeric threshold.
- **Effect size:** report mean paired delta, 95% cluster-aware CI, and paired standardized effect `d_z` with CI; treat conventional 0.2/0.5/0.8 magnitudes as descriptive only, not deployment thresholds.
- **Sample size:** choose the number of independent clusters by an a priori power analysis (at least 80% power for `delta_min`, alpha 0.05), using a blinded pilot or defensible external variance estimate. Do not count repeated simulation rows as sample size.
- **Improvement:** upper bound of the 95% CI for mean `delta` is below `-delta_min`, primary test meets alpha, and the precomputed cluster sample-size requirement is met.
- **No meaningful difference:** a predeclared equivalence test supports the entire equivalence interval `[-delta_min, +delta_min]` (e.g. TOST at alpha 0.05); a nonsignificant superiority test alone is not evidence of equivalence.
- **Degradation:** lower bound of the 95% CI is above `+delta_min`, with the predeclared primary test meeting alpha.
- **Inconclusive:** all other cases, including insufficient independent clusters, failed provenance, wide intervals, or conflicting results.

This is a proposed protocol, not a frozen preregistration. It becomes frozen only after the target population, measurement horizon/instrument, `delta_min`, and power/sample-size plan are approved and written to a versioned protocol before outcome values are examined.

## 7. Files for a Future Implementation

No source files should be changed now. Once independent outcomes and a frozen protocol exist, the smallest research-only implementation would be:

**Create:**
- `17_16B_EVALUATION_PROTOCOL.json` - approved, immutable population, horizon, metric, test, alpha, `delta_min`, sample-size/power plan, exclusions and versions.
- `backend/models/observed_transition_outcome.py` - strict research-record schema with event/user pseudonymous IDs, action/context, before/after measurements, timestamps, provenance, model versions and pre-outcome prediction timestamp.
- `backend/validation/behavioral_evaluation_17_16b.py` - read-only validator/analysis of eligible records; no outcome generation or fallback labels.
- `backend/tests/test_behavioral_evaluation_17_16b.py` - schema, leakage/exclusion, paired metric, clustering and immutable-input tests.
- A new, separately named observed-outcome input file outside version control if it contains sensitive user data; never reuse or overwrite the frozen 17.15 event file.

**Potentially modify only after separate approval:**
- A research-only capture/ingestion adapter if no independent export exists. It must record independently measured action-level outcomes and provenance; it must not turn `SimulationEngine` output into an actual state or alter production prediction behavior.

**Do not modify:** 17.15 artifacts, frozen MG coefficients/configuration, production prediction logic, or previous result files. This assessment supersedes the earlier architecture-ready recommendation without rewriting those files.

## 8. Decision and Next Step

**Implementation ready:** No.  
**17.16B result:** Not available; no effectiveness test was run.  
**Data required:** Yes - a provenance-verified, independently observed, action-linked cohort with a predeclared post-action measurement horizon.  
**Recommended next step:** Locate an external/operational source of actual executed-action and measured-state records, or begin prospective collection under an approved measurement protocol. Audit and freeze the cohort/protocol before generating comparative results.

Until that evidence exists, retain the research status as:

- 17.15 mechanical/infrastructure validation: pass as reported.
- 17.16A correction-pattern description: descriptive only; not effectiveness evidence.
- 17.16B predictive effectiveness: unknown / blocked for insufficient independent outcomes.
- 17.17 tuning and 17.18 production activation: not justified by current evidence.
