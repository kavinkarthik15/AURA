# 17.14A Observability Contract

**Status**: FROZEN BEFORE IMPLEMENTATION  
**Date**: 2026-08-14  
**Phase**: 17.14A  
**Purpose**: Define the minimal shadow-only event contract needed to validate deployment safety without allowing MG to influence production behavior.

---

## 1. Contract objective

The purpose of 17.14A observability is to answer one question:

> Can the system record what MG would have done without allowing MG to control the production result?

This is an observational requirement only. The production path must remain legacy-controlled.

---

## 2. Hard invariants

The following are immutable:

- 17.13B implementation remains frozen
- 17.13C Run 1 remains frozen
- MG coefficients remain unchanged
- MG formula remains unchanged
- acceptance criteria remain unchanged
- production activation remains forbidden
- legacy simulation authority remains authoritative
- default MG state remains enabled=False, rollout=0%

### Required behavior

```
shadow_observation_failure ≠ prediction_failure
```

Logging or observability failures must never become a production failure path.

---

## 3. Event model

Each shadow request produces one observational record.

### Event subject

- request context
- dynamic state
- action
- category
- legacy output
- MG shadow output
- metadata and error state

### Event semantics

The shadow record must be observational only:

- it may record what MG would have computed
- it must not alter the user-visible result
- it must not mutate production state
- it must not change decision authority
- it must not alter downstream execution paths

---

## 4. Required fields

Each event record must include at minimum:

```json
{
  "experience_id": "string or null",
  "seed": 0,
  "category": "string or null",
  "action": "string",
  "legacy_prediction": {},
  "mg_shadow_prediction": {},
  "mg_correction": {},
  "motivation_signal": 0.0,
  "goals_signal": 0.0,
  "fallback_triggered": false,
  "fallback_reason": "string or null",
  "legacy_latency_ms": 0,
  "mg_latency_ms": 0,
  "mg_error": null
}
```

### Field requirements

1. `experience_id`
   - stable identifier for request/experience trace
   - may be null for synthetic or non-identity cases

2. `seed`
   - dataset seed identity for research validation and comparison

3. `category`
   - action/category context used by shadow logic

4. `action`
   - action under evaluation

5. `legacy_prediction`
   - exact legacy result used in production

6. `mg_shadow_prediction`
   - shadow-only MG prediction result

7. `mg_correction`
   - difference or delta between legacy and MG shadow prediction

8. `motivation_signal`
   - numeric signal value extracted by MG logic

9. `goals_signal`
   - numeric signal value extracted by MG logic

10. `fallback_triggered`
    - true when MG falls back to legacy or safe path

11. `fallback_reason`
    - failure cause or fallback reason if triggered

12. `legacy_latency_ms`
    - latency for legacy execution path

13. `mg_latency_ms`
    - latency for shadow-only MG processing path

14. `mg_error`
    - null or error string; must not crash production

---

## 5. Optional fields

Optional fields may be included for richer analysis, but they must not be required for gate acceptance:

- `request_id`
- `timestamp`
- `trace_id`
- `state_snapshot`
- `state_hash`
- `production_decision`
- `shadow_decision`
- `dataset_name`
- `artifact_version`
- `is_synthetic`
- `context_tags`

Optional data must not alter required fields or change the production flow.

---

## 6. Data types and null semantics

The event record must obey the following semantics:

- `experience_id`: string or null
- `seed`: integer or null
- `category`: string or null
- `action`: string
- `legacy_prediction`: object or null
- `mg_shadow_prediction`: object or null
- `mg_correction`: object or null
- `motivation_signal`: float or null
- `goals_signal`: float or null
- `fallback_triggered`: boolean
- `fallback_reason`: string or null
- `legacy_latency_ms`: integer or float
- `mg_latency_ms`: integer or float
- `mg_error`: string or null

### Error semantics

- if MG produces an error, the event still records the failure
- production continues with legacy output
- `mg_error` stores the error text
- no exception should escape the production response path

---

## 7. Event identity and seed identity

Each event must support linkage to both the request and the benchmark context.

Required identity metadata:

- `experience_id`
- `seed`
- `category`
- `action`

This allows downstream analysis of:

- per-request comparison
- per-seed difference
- per-category behavior
- fallback frequency
- correction stability

---

## 8. Legacy vs MG relationship

The event must preserve the relationship:

```
legacy_prediction + mg_shadow_prediction + mg_correction
```

and must not rewrite or substitute the legacy result.

The essential relationship is:

- `legacy_prediction` is the production output
- `mg_shadow_prediction` is the shadow-only estimate
- `mg_correction` is the delta used for analysis

The event should be purely descriptive and never act as a control input.

---

## 9. Fallback semantics

If MG fails or cannot compute a valid signal, the event must still be recorded with:

- `fallback_triggered = true`
- `fallback_reason = ...`
- `legacy_prediction` retained
- `mg_shadow_prediction` null or legacy-equivalent
- `mg_error` set if relevant

Fallback must never alter the production path.

---

## 10. Logging failure behavior

The logging pipeline must be best-effort and non-blocking.

Required invariants:

- logging failure must never block the request
- logging failure must never affect legacy output
- logging failure must never trigger production fallback
- logging failure must be recorded in a separate error channel if available

This ensures:

```
shadow_observation_failure ≠ prediction_failure
```

---

## 11. Privacy and retention

The event record must not capture sensitive user information beyond what is necessary for the experiment.

Before any production-like shadow run, define:

- retention period
- redaction rules
- storage location
- access boundary
- anonymization policy if required

The event record must not store secrets, tokens, credentials, or unrestricted user content.

---

## 12. Validation requirements

The minimally acceptable observability implementation must validate all of the following:

1. Every shadow event includes all required fields
2. Production output remains unchanged
3. Legacy path remains authoritative
4. MG path remains shadow-only
5. Fallback records are captured
6. Errors are captured without interrupting production
7. Seed and experience identity are preserved
8. Event schema remains stable across phase runs
9. Event payload is serializable to JSON
10. Production behavior is unaffected by observability instrumentation

---

## 13. Allowed implementation boundary

The implementation may add only the following:

- a shadow event recorder
- an event schema serializer
- shadow-only logging output
- metadata capture for legacy vs MG comparison
- failure/fallback record capture

It may not:

- modify any MG coefficient
- change the MG equation
- alter the production decision path
- alter legacy output
- change the 17.13C acceptance criteria
- alter the historical 17.13C artifact

---

## 14. Freeze status

This contract is frozen before implementation and acts as the 17.14A observability specification.

Any implementation that violates this contract is not a valid 17.14A run.
