# Episodic Memory Architecture v1

## Status

Frozen for the next episodic-memory implementation sprint.

This document defines the episodic-memory contract independently from storage technology. It is aligned with the current `Experience` model, `ExperienceRetriever`, and `EpisodicMemory` adapter. Sprint 13.3 implements this contract while preserving the existing planner-facing retrieval behavior.

## 1. Purpose

Episodic Memory stores concrete episodes in their temporal and situational context. An episode records what AURA attempted, the state before and after the attempt, the actions taken, the outcome, and the evidence available at the time.

Episodic Memory is not:
- a generalized knowledge store,
- a workflow or policy store,
- transient Working Memory,
- or an unstructured event log without retrieval metadata.

## 2. Ownership and Gateway

All episodic-memory operations must go through `MemoryManager`.

```text
Planner / Reasoner / Execution Logger
                |
                v
         MemoryManager
                |
                v
         EpisodicMemory
                |
                v
      Experience Index
              |
              v
      ExperienceRetriever
```

`EpisodicMemory` owns the canonical experiences. `Experience Index` organizes encoded experiences for efficient lookup. `ExperienceRetriever` performs search over the index and returns ranked retrieval views. Callers must not instantiate or access either the index or `ExperienceRetriever` directly.

`MemoryManager` owns routing, policies, lifecycle orchestration, and analytics exposure. EpisodicMemory owns episode encoding and the canonical record lifecycle. The Experience Index owns lookup structures, while ExperienceRetriever owns search, scoring, ranking, and diversity selection. Neither the index nor retriever owns canonical episode data.

This separation permits the lookup implementation to change from JSON or an in-process index to FAISS, ChromaDB, BM25, or a hybrid search system without changing the EpisodicMemory or MemoryManager APIs.

### 2.1 Component responsibilities

| Component | Owns | Must not own |
|---|---|---|
| `EpisodicMemory` | Canonical experiences, validation, normalization, revisions, archive state | Search algorithm or planner policy |
| `ExperienceIndex` | Index entries, lookup structures, index version, rebuild/update operations | Canonical episode authority or business decisions |
| `ExperienceRetriever` | Query normalization, similarity scoring, ranking, diversity filtering, retrieval views | Canonical persistence or store lifecycle |
| `MemoryManager` | Gateway, routing, policies, lifecycle and analytics orchestration | Episodic records or index internals |

### 2.2 Experience Index interface

The index is an implementation boundary, not a public memory gateway:

```python
class ExperienceIndex:
    def build(self, episodes) -> None: ...
    def add(self, episode) -> None: ...
    def update(self, episode) -> None: ...
    def remove(self, memory_id: str) -> None: ...
    def candidates(self, query, top_k: int) -> list: ...
    def health(self) -> dict: ...
```

The first implementation may use the current JSON-backed index behavior. Future implementations may provide vector, lexical, graph, or hybrid lookup while retaining this contract.

## 3. Episode Schema

### 3.1 Required identity and time fields

| Field | Type | Meaning |
|---|---|---|
| `memory_id` | string | Stable memory identifier, for example `EXP-2026-000182`. |
| `experience_id` | string | Backward-compatible source experience identifier. |
| `episode_id` | string, optional | Episode-level identifier when one episode contains multiple events. |
| `created_at` | datetime | Time the episode was encoded into memory. |
| `updated_at` | datetime | Time the episode was last changed. |
| `occurred_at` | datetime | Time the episode happened, if known. |
| `last_accessed` | datetime, optional | Last successful retrieval or inspection time. |
| `retrieval_count` | integer | Number of successful retrievals. |

`memory_id` is the canonical memory reference. `experience_id` remains for compatibility with the existing experience dataset and retrieval APIs.

### 3.2 Episode content fields

| Field | Type | Meaning |
|---|---|---|
| `user_id` | string | User or subject associated with the episode. |
| `goal` | string | Goal being pursued. Accept `goal_name` as a legacy input alias. |
| `experience_type` | string | Episode category, such as `learning`, `planning`, or `execution`. |
| `state_before` | mapping | State before the episode. Must not be empty. |
| `actions` | list[string] | Actions considered or executed. |
| `completed_actions` | list[string] | Actions actually completed. |
| `state_after` | mapping | State after the episode. |
| `state_delta` | mapping | Computed or recorded state change. |
| `context` | mapping | Situational context at the time of the episode. |
| `outcome` | mapping or string | Structured or summarized result. |
| `outcome_value` | float | Normalized outcome value in the range `[-1.0, 1.0]`. |
| `success` | boolean | Whether the episode met its success criterion. |
| `goal_completion` | float | Goal completion score, normally in the range `[0.0, 1.0]`. |

### 3.3 Memory metadata fields

| Field | Type | Meaning |
|---|---|---|
| `importance` | float | Long-term value of retaining this episode, in `[0.0, 1.0]`. |
| `confidence` | float | Confidence that the record and outcome are reliable, in `[0.0, 1.0]`. |
| `source` | string | Subsystem or external source that created the episode. |
| `tags` | list[string] | Retrieval and analysis labels. |
| `supersedes` | string, optional | `memory_id` replaced by this revision. |
| `revision` | integer | Monotonic record revision number. |
| `archived` | boolean | Whether the episode is retained but excluded from active retrieval. |

### 3.4 Compatibility normalization

The encoder must normalize existing records as follows:

- `goal_name` or `goal` -> `goal`
- `initial_state` or `state_before` -> `state_before`
- `timestamp`, `created`, or `created_at` -> `occurred_at` or `created_at`
- `outcome_value > 0` -> default `success=True` when `success` is absent
- missing `completed_actions` -> empty list
- missing `state_delta` -> computed delta when possible, otherwise empty mapping
- missing `memory_id` -> generated once and persisted; it must not change on re-indexing

## 4. Storage Lifecycle

```text
Observed Episode
      |
      v
Validate and Normalize
      |
      v
Encode with memory metadata
      |
      v
Store in EpisodicMemory
      |
      v
Encode and publish to Experience Index
      |
      v
ExperienceRetriever searches the index
      |
      v
Retrieve and record access analytics
      |
      v
Update or revise when corrected
      |
      v
Archive, consolidate, or forget by later policy
```

### 4.1 Creation

An execution logger, simulation, or completed planning episode submits a raw episode to `MemoryManager.store("episodic", episode)`.

### 4.2 Encoding

EpisodicMemory validates required fields, normalizes legacy aliases, assigns stable identity and metadata, and produces an indexable representation containing:

- state features,
- goal text,
- action sequence,
- success and completion signals,
- timestamp and freshness data,
- importance and confidence.

EpisodicMemory then publishes the representation to Experience Index. Index entries are projections of canonical episodes and may be rebuilt without changing episode identity.

### 4.3 Active retrieval

Only non-archived episodes are eligible for normal retrieval. Retrieval updates `last_accessed` and `retrieval_count` through the episodic store and records analytics through MemoryManager.

### 4.4 Update and revision

Updates are versioned. A correction must not silently overwrite the historical episode. The preferred behavior is:

1. create a new revision,
2. set `supersedes` to the previous `memory_id`,
3. preserve the previous record in audit history,
4. exclude superseded records from default retrieval unless explicitly requested.

### 4.5 Archive and deletion

Archiving is reversible and preserves auditability. Physical deletion is a policy-controlled operation and must support an audit entry containing the memory ID, actor, reason, and timestamp.

Consolidation and forgetting are deferred to later Phase 13 work. This design only defines their boundaries.

## 5. Similarity and Retrieval Flow

```text
Retrieval query
      |
      v
MemoryManager retrieval policy
      |
      v
EpisodicMemory query normalization
      |
      v
Experience Index candidate lookup
      |
      v
ExperienceRetriever search and scoring
      |
      +--> state similarity
      +--> goal similarity
      +--> action overlap
      +--> optional embedding similarity
      +--> freshness adjustment
      +--> success/outcome adjustment
      |
      v
Composite similarity score and retrieval view
      |
      v
Sort, diversity filter, and Top-K selection
      |
      v
Retrieved episodes + retrieval metadata
```

### 5.1 Query contract

A query may contain:

```json
{
  "state": {"python": 50},
  "goal": "Python Growth",
  "actions": ["Python Project"],
  "user_id": "default_user",
  "top_k": 5,
  "include_failures": true,
  "include_archived": false
}
```

The current planner-facing compatibility API remains:

```python
retrieve_experiences(state, goal, actions, top_k, diversity_threshold)
```

### 5.2 Composite score

The exact metric is configurable, but the default score is conceptually:

```text
similarity =
    state_weight * state_similarity
  + goal_weight * goal_similarity
  + action_weight * action_overlap
  + embedding_weight * embedding_similarity
```

The score is then adjusted by:

```text
effective_similarity =
    similarity
  * freshness_factor
  * outcome_factor
  * confidence_factor
```

The implementation must record the metric version and weights used for each benchmarkable retrieval configuration.

### 5.3 Diversity

Top-K selection must avoid returning near-duplicate episodes. A candidate may be excluded when its state/action overlap with an already selected result exceeds the configured diversity threshold.

### 5.4 Retrieval result contract

Each result must expose at least:

- `memory_id` or compatible `experience_id`,
- similarity score,
- state and goal summary,
- actions and completed actions,
- success and goal completion,
- freshness or timestamp metadata,
- reason or provenance for retrieval.

The current `RetrievedExperience` object remains a valid compatibility view over the canonical episodic record.

## 6. Importance Scoring

Importance is distinct from similarity and confidence.

- `similarity`: relevance to the current query.
- `confidence`: reliability of the record and its outcome.
- `importance`: value of retaining the episode for future reasoning.

### 6.1 Initial importance inputs

The initial policy should consider:

```text
importance = clamp(
    0.25 * outcome_significance
  + 0.20 * goal_completion
  + 0.20 * confidence
  + 0.15 * novelty
  + 0.10 * recurrence_signal
  + 0.10 * reflection_value,
  0.0,
  1.0
)
```

These weights are policy configuration, not a permanent storage contract.

### 6.2 Importance rules

- Successful episodes are not automatically important.
- Rare failures may be highly important for reflection and avoidance.
- Repeated near-duplicate episodes should not accumulate unlimited importance.
- User corrections and explicit feedback may raise or lower importance.
- Importance changes must be auditable through revisions or metadata history.

## 7. Update and Merge Rules

### 7.1 Update

Use update when the same episode receives corrected metadata or a late-arriving outcome. Preserve the original identity and increment `revision` only when the logical episode remains the same.

### 7.2 Merge

Merge is permitted only when records represent the same episode or an explicitly equivalent duplicate. It must:

1. select a surviving canonical `memory_id`,
2. preserve all source IDs in `merged_from`,
3. combine non-conflicting metadata,
4. resolve conflicts using confidence, recency, and explicit user correction,
5. retain an audit record of the merge,
6. rebuild the retrieval index.

Episodes with different outcomes, goals, or action sequences must not be merged merely because they are similar.

### 7.3 Conflict policy

When fields conflict:

- explicit user or execution correction wins,
- a higher-confidence observation wins over a lower-confidence observation,
- a newer observation wins only when confidence is comparable,
- unresolved conflicts remain visible rather than being silently discarded.

## 8. Analytics Interfaces

Analytics are exposed through MemoryManager and implemented by EpisodicMemory or its retrieval adapter.

### 8.1 Required interfaces

```python
get_analytics_summary() -> dict
get_episode_analytics(memory_id: str) -> dict
record_retrieval(memory_id: str, similarity: float, latency_ms: float) -> None
record_outcome(memory_id: str, success: bool, goal_completion: float) -> None
```

### 8.2 Required aggregate metrics

- total stored episodes,
- active and archived episode counts,
- retrieval count,
- unique episodes retrieved,
- average similarity,
- average retrieval latency,
- cache hit rate,
- success rate of retrieved episodes,
- average goal completion,
- retrieval coverage by goal or experience type,
- duplicate and merge counts,
- update and correction counts.

### 8.3 Benchmark interfaces

Benchmark evaluation must be able to provide:

```python
evaluate_recall(queries, relevant_ids) -> dict
evaluate_precision(queries, relevant_ids) -> dict
evaluate_latency(queries) -> dict
evaluate_diversity(queries) -> dict
```

Every benchmark result must identify the dataset version, retrieval metric, policy version, and configuration used.

## 9. Failure and Safety Rules

- A malformed episode must be rejected or placed in an explicit quarantine path; it must not silently enter the active index.
- Missing identity must be generated once and persisted.
- Retrieval failures must return an observable error or empty result with diagnostics, not fabricated evidence.
- Archived or superseded episodes must not appear in default retrieval.
- Analytics failures must not corrupt the episode record.
- No episodic operation may bypass MemoryManager.

## 10. Implementation Boundary

The first implementation sprint after this design freeze should focus on:

- canonical episodic record normalization,
- stable memory IDs and metadata,
- MemoryManager gateway methods,
- compatibility with the current ExperienceRetriever,
- retrieval analytics interfaces,
- focused tests for lifecycle, retrieval, updates, and analytics.

The following remain outside this design's first implementation increment:

- semantic extraction,
- procedural promotion,
- consolidation policy execution,
- forgetting execution,
- vector database migration,
- autonomous importance learning.

## 11. Design Freeze Checklist

- [x] Experience schema defined.
- [x] Storage lifecycle defined.
- [x] Similarity and retrieval flow defined.
- [x] Importance scoring defined.
- [x] Update and merge rules defined.
- [x] Analytics interfaces defined.
- [x] MemoryManager ownership preserved.
- [x] Compatibility with current retriever documented.

This document is the authority for episodic-memory implementation until superseded by an explicitly versioned architecture decision.
