# 17.16B Prospective Ground-Truth Collection Architecture

**Status:** Infrastructure ready; effectiveness evaluation remains blocked pending legitimate prospective outcomes
**Implementation date:** 2026-10-06

## Why prospective collection is needed

The existing experience corpora are synthetic or are used to generate baseline predictions. Simulation/digital-twin output is predicted state, not observed state. The existing experience logger accepts caller-supplied `actual_state` without row-level evidence of how it was measured. The 17.15 events contain paired predictions but no independently observed, action-linked outcomes. Relabeling any of those values as ground truth would be circular or unsupported.

This implementation creates a prospective collection path only. It does not import existing data, change prediction behavior, run an effectiveness analysis, or establish that any recorded claim is true. Human/research review of the referenced evidence remains necessary.

## Data model and target boundary

`ProspectivePredictionEpisode` stores a unique user-scoped episode containing:

- server-generated episode ID and prediction-freeze timestamp;
- career skill pre-action state, proposed action, and JSON context;
- paired base and MG predictions plus model, coefficient, and MG-configuration SHA-256 identifiers;
- a frozen target with skill name, dimension, unit, scale, measurement method, valid range, and positive horizon;
- action start/completion timestamps and the exact performed action;
- nullable observed outcome, provenance, quality, status, and exclusion/missing-outcome reasons.

The first target is deliberately limited to an existing AURA `skills` dimension (integer 0–100), represented as a skill score on the declared scale. Health, relationships, finance, arbitrary future state, and unsupported dimensions are rejected. The collection caller must declare the measurement method and horizon; the service does not invent either protocol decision.

## Prediction freeze and episode lifecycle

Creation calls an injected prediction provider before any outcome can be passed to the service. `SimulationEnginePredictionProvider` captures the existing base/MG pair through the engine's existing shadow-event interface; it does not alter the engine or coefficients. The target must be present and in range in both predictions. Creation accepts no observed-outcome argument, and frozen prediction inputs are kept separately from mutable lifecycle data.

Lifecycle:

1. `PREDICTION_FROZEN` — predictions, initial state, action, context, target, and horizon are recorded.
2. `ACTION_STARTED` — an explicit caller reports action start.
3. `ACTION_COMPLETED` — an explicit caller reports completion and the performed action. A mismatch from the frozen proposed action immediately excludes the episode.
4. `AWAITING_OUTCOME` — entered only when the declared horizon after action completion is due.
5. `OUTCOME_RECORDED` — a validated measured value and provenance are recorded once.
6. `EXCLUDED` or `MISSING_OUTCOME` — terminal non-eligible outcomes with reasons.

An action recommendation is not evidence that it happened. An unstarted action can be excluded; incomplete or mismatched actions cannot qualify. The initially estimated due time is recalculated from action completion, so the declared horizon is post-action.

## Outcome provenance and leakage controls

An outcome requires an allowed source (`USER_REPORTED`, `SYSTEM_OBSERVED`, `ASSESSMENT`, `EXTERNAL_MEASUREMENT`, or `VERIFIED_EVENT`), collection method matching the frozen target, recorder identity, evidence ID, timezone-aware observation timestamp, target/value, and a 0–1 quality indicator. Quality is retained as provenance; it is not fed to MG or converted into an MG score.

The schema rejects prediction/simulation/digital-twin/synthetic/legacy-prediction source labels. The outcome API accepts a target-specific scalar measurement, not a prediction object or arbitrary state payload; it does not accept training-dataset rows. Outcome timestamps before the due time, timestamps in the future, target/unit/scale/method mismatches, and out-of-range values are rejected. No retrospective prediction-update or outcome-overwrite operation is exposed.

Software cannot prove that a human-supplied evidence ID represents an independent measurement. Numeric equality between a measurement and a forecast is not, by itself, treated as leakage: a real measurement can legitimately equal a prediction. Source provenance and the external evidence must be audited before a research cohort is declared verified.

## Persistence and audit

Episodes are stored in a dedicated SQLite database at `backend/data/prospective_outcomes/prospective_outcomes.sqlite3`, separate from synthetic/training datasets. The SQLite database is ignored by the repository's existing `*.sqlite3` rule. Each lifecycle event is append-only, and database triggers prevent event update/deletion and frozen-field mutation in both the frozen-payload record and serialized episode projection. Lifecycle writes use expected-snapshot compare-and-swap so concurrent updates cannot silently duplicate or reorder transitions. Reads require the matching user ID.

Tests use temporary database files only. Test outcome values and evidence IDs are synthetic fixtures for validating code behavior and are not research observations.

## Evaluation eligibility

`is_episode_evaluation_eligible` returns a boolean and structured rejection reasons. It requires a recorded outcome, prediction before observation, a started/completed exact action match, the same frozen target and unit, an observation at/after the due horizon, positive provenance quality, and no exclusion/missing-outcome state. This is a software gate, not evidence that provenance has passed independent human audit, and it does not itself compute metrics.

## What remains blocked

At implementation time, the independently verified prospective cohort remains **zero**. The evaluation protocol is still draft: population, validated measurement instrument/horizon, minimum meaningful effect, and a priori power plan require approval and must be frozen before outcomes are examined. No MG win rate, accuracy/MAE change, effectiveness statistic, or significance test was run. 17.16B remains blocked until sufficient legitimate outcomes are collected and their provenance, independence, linkage, and protocol eligibility are reviewed.

**Next step:** approve the target-specific measurement instrument, population, horizon, `delta_min`, and power/sample-size protocol; then operate prospective collection and audit the evidence before any effectiveness analysis.
