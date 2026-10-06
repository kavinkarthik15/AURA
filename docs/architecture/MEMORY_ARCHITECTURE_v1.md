# Memory Architecture v1

## 1. Introduction

This document defines the first complete memory architecture for AURA. It is intentionally design-first and implementation-neutral, with Sprint 13.1 now providing the first implementation boundary for the design.

This specification answers:
- What is memory in AURA?
- What memory types exist?
- What does every memory object contain?
- How do planning, reasoning, and learning use memory?
- How does forgetting work?
- How does consolidation work?
- How should memory be benchmarked?

AURA's memory system is a new cognitive capability layer, one that transforms the current experience-centric system into an integrated memory architecture.

### Sprint 13.1 implementation status

Sprint 13.1 is implemented as the MemoryManager foundation:
- `backend/memory/MemoryManager` is the single gateway for memory operations.
- Episodic Memory delegates retrieval to the existing `ExperienceRetriever`.
- Working, Context, Semantic, Procedural, and Reflection stores are registered; non-episodic stores remain placeholders except for reflection persistence integration.
- Planner retrieval and Meta-Reasoner reflection writes are routed through MemoryManager.
- Consolidation and forgetting remain deferred to later Phase 13 sprints.

### Sprint 13.2 implementation status

Working Memory is now a transient planning-session store:
- Each planning request creates a `working_memory_id` session.
- `WorkingMemoryRecord` stores typed active information with importance and timestamps.
- Planner state includes the goal, constraints, retrieved experiences, candidate plan, reasoning, strategy, confidence, and reflection.
- The planner exposes a `working_memory_snapshot` for debugging and benchmarking.
- Sessions are ended and cleared after the decision; snapshots are returned without making Working Memory persistent.
- Working Memory does not search, consolidate, or participate in long-term forgetting.

### Sprint 13.3 implementation status

Episodic Memory now owns canonical experience records and delegates lookup through a replaceable `ExperienceIndex` to `ExperienceRetriever`. The implementation includes metadata, revisions, relationships, soft lifecycle statuses, analytics, and registry health reporting. Semantic extraction, consolidation, forgetting, and automatic promotion remain deferred.

## 2. Memory Philosophy

### 2.1 Why AURA needs memory

AURA needs memory to:
- preserve useful knowledge across interactions,
- support fast context-aware reasoning,
- avoid re-learning facts already known,
- recognize recurring patterns,
- evaluate its own thinking over time,
- and adapt behavior based on long-term usage.

Memory is the component that turns isolated experiences into a coherent, persistent cognitive foundation.

### 2.2 Definitions

#### Database
A database is an external storage mechanism for raw data. It holds records, logs, and structured tables. It is not by itself a cognitive system.

#### Experience
Experience is a specific episode of interaction: a user goal, a plan, execution details, observed outcomes, and context. Experience is raw or semi-structured evidence from actual or simulated events.

#### Knowledge
Knowledge is generalized, abstracted information derived from experiences, facts, and semantics. It includes rules, facts, stable preferences, and relationships.

#### Memory
Memory is the system that stores, organizes, retrieves, consolidates, and forgets experiences and knowledge. Memory is not just storage; it is an active cognitive substrate with lifecycle behavior.

### 2.3 Memory versus other data concepts

- A database can hold both memory and non-memory data. Memory is the cognitive interpretation layer above storage.
- Experience becomes memory only when it is encoded, indexed, and made retrievable.
- Knowledge is a subset of memory, usually stored in semantic memory and procedural memory, but not all memory is knowledge.
- Memory is the union of episodic traces, semantic facts, procedural patterns, and reflection signals.

## 3. Memory Taxonomy

AURA's memory taxonomy is the foundation for capability design.

```
Memory
│
├── Working Memory
├── Episodic Memory
├── Semantic Memory
├── Procedural Memory
└── Reflection Memory
```

### 3.1 Working Memory

#### Role
Working Memory is the short-duration, task-specific information used during an active planning and reasoning episode.

#### Contents
- current beam search nodes,
- candidate plans,
- temporary evaluation state,
- retrieved experiences for the current cycle,
- intermediate reasoning structures.

#### Properties
- highly transient,
- tightly scoped to the current decision cycle,
- updated continuously during planning and reasoning,
- cleared or refreshed after each decision cycle.

### 3.2 Context Memory

#### Role
Context Memory stores ongoing environmental and situational context that persists across reasoning cycles but is not long-term knowledge.

#### Contents
- current location,
- current schedule,
- active conversation context,
- current environment status (connectivity, available resources),
- temporal context such as day, time, and deadlines.

#### Properties
- longer-lived than Working Memory,
- updated when the external situation changes,
- available across multiple reasoning episodes,
- separate from transient planning state.

### 3.3 Episodic Memory

#### Role
Episodic Memory stores concrete experiences in their full temporal context.

#### Contents
- execution episodes,
- plan traces,
- states before and after actions,
- goals, tasks, outcomes,
- time, location, and circumstance metadata,
- emotional or confidence metadata if available.

#### Properties
- indexed by time, goal, user, and outcome,
- supports retrieval of similar episodes,
- preserves the chain of events that led to success or failure.

The detailed episodic-memory contract is frozen in [EPISODIC_MEMORY_ARCHITECTURE_v1.md](EPISODIC_MEMORY_ARCHITECTURE_v1.md).

### 3.3 Semantic Memory

#### Role
Semantic Memory stores generalized facts, stable preferences, rules, and knowledge about the user, environment, and domain.

#### Contents
- user facts (skills, preferences, capabilities),
- environment facts (device availability, resource constraints),
- domain knowledge (task hierarchies, skill taxonomies),
- relationships and entity attributes,
- definitions and heuristics.

#### Properties
- durable and stable,
- updated slowly,
- used for reasoning, planning, and personalization,
- supports query-based retrieval and inference.

### 3.4 Procedural Memory

#### Role
Procedural Memory stores reusable workflows, patterns, heuristics, and action sequences.

#### Contents
- learned plan templates,
- skill-building routines,
- successful workflows for similar goals,
- action selection strategies,
- reusable subplans and policy fragments.

#### Properties
- encodes how to do things,
- is richer than a lookup table,
- can be parameterized for new goals,
- forms the basis for procedural generalization.

### 3.5 Reflection Memory

#### Role
Reflection Memory stores the system's self-assessments, meta-cognitive evaluations, and revision history.

#### Contents
- reflection decisions (accept/replan/reject),
- reasoning quality scores,
- evidence sufficiency assessments,
- detected assumptions,
- contradictions,
- self-critique logs,
- lessons learned and improvement suggestions,
- revision outcomes.

#### Properties
- used to calibrate meta-reasoning,
- supports retrospective learning,
- links memory, reasoning, and planning quality over time.

## 4. Information Flow

The memory system forms a cognitive pipeline.

```
Goal
↓
Planner
↓
MemoryManager
↓
Working Memory
↓
Retriever
↓
Episodic Memory
↓
Reasoner
↓
Reflection
↓
Memory Update
↓
Consolidation
↓
Semantic Memory
```

### 4.1 Stage: Goal to Planner
- When a goal is received, the Goal Manager populates Working Memory with current situation, constraints, and applicable context.
- The planner requests retrieval through MemoryManager and does not access storage directly.

### 4.2 Stage: Planner to MemoryManager
- The planner queries MemoryManager for supporting experiences, facts, and workflow templates.
- MemoryManager decides which memory stores to search and returns the relevant data.

### 4.3 Stage: Working Memory to Reasoning

- When a goal is received, the Goal Manager populates Working Memory with current situation, constraints, and applicable context.
- The planner, retriever, and reasoner read from Working Memory to seed the decision process.

### 4.2 Stage: Working Memory to Reasoning

- Reasoning uses Working Memory plus retrieved episodic and semantic data.
- Intermediate reasoning results remain in Working Memory for evaluation and revision.

### 4.3 Stage: Reasoning to Reflection

- The Meta-Reasoner evaluates the output of reasoning and planning.
- Reflection Memory records the decision, supporting evidence, assumptions, and confidence.

### 4.4 Stage: Reflection to Consolidation

- Reflection Memory signals whether the current plan should or should not be consolidated.
- Successful and reliable experiences may be promoted to Episodic, Semantic, or Procedural Memory.

### 4.5 Stage: Consolidation to Long-Term Memory

- Consolidation selects high-value memory fragments for long-term storage.
- Low-value or obsolete items are decayed or removed.
- Consolidated knowledge becomes part of the persistent memory architecture.

## 5. Memory Life Cycle

Memory objects have a lifecycle from creation to deletion.

```
Creation
↓
Encoding
↓
Retrieval
↓
Reasoning
↓
Consolidation
↓
Decay
↓
Deletion
```

### 5.1 Creation

Memory creation occurs when:
- a new experience is observed,
- a goal or constraint is introduced,
- a fact or preference is learned,
- a procedural pattern is discovered,
- a reflection evaluation is produced.

Creation is triggered by the planner, retriever, reasoner, execution engine, or meta-reasoner.

### 5.2 Encoding

Encoding transforms raw data into indexed memory objects.

#### Encoding dimensions
- semantics: what the memory means,
- temporal context: when it occurred,
- source: which subsystem generated it,
- strength: confidence or importance,
- structure: typed fields for retrieval.

Encoding applies to:
- episodic events,
- semantic facts,
- procedural templates,
- reflection judgments.

### 5.3 Retrieval

Retrieval is the process of locating relevant memories for a decision.
It can be:
- direct lookup,
- similarity search,
- pattern matching,
- context-aware ranking.

Retrieval is used during planning, reasoning, and reflection.

### 5.4 Reasoning

Reasoning consumes memory retrieval results.
- Episodic Memory provides comparative cases.
- Semantic Memory provides facts and constraints.
- Procedural Memory provides workflows and routines.
- Working Memory provides current context.
- Reflection Memory provides meta-feedback.

During reasoning, memory items are evaluated for relevance, coherence, and support.

### 5.5 Consolidation

Consolidation is the process of promoting selected memories into long-term storage or strengthening their representation.

It includes:
- capturing recurrent patterns,
- generalizing successful routines into procedural memory,
- converting stable facts into semantic memory,
- archiving significant episodes.

### 5.6 Decay

Decay gradually reduces the salience of memory objects over time or use.

Mechanisms include:
- age decay,
- importance decay,
- confidence decay,
- duplicate removal,
- usage-based reprioritization.

### 5.7 Deletion

Deletion occurs when memory objects are no longer valuable, redundant, or incorrect.

Deletion rules must be conservative and audit-safe. The system should track why a memory was removed.

## 6. Retrieval Pipeline

Memory retrieval is a core cognitive operation. It is responsible for bringing the most relevant memories into the current reasoning context.

### 6.1 Retrieval architecture

The retrieval pipeline is composed of:
- index construction,
- query generation,
- candidate search,
- scoring,
- ranking,
- result selection.

### 6.2 Query generation

Queries are built from:
- current goal state,
- working memory context,
- user profile,
- task constraints,
- previous reflections and lessons,
- desired memory type (episodic, semantic, procedural, reflection).

Queries may be generated by the planner, reasoner, or memory manager.

### 6.3 Candidate search

Candidate search selects memory objects matching the query dimensions.
It can use:
- exact keys,
- embedding similarity,
- semantic matching,
- metadata filtering,
- temporal constraints.

### 6.4 Scoring

Each candidate is scored along multiple axes:
- relevance to query,
- similarity to current context,
- recency,
- importance,
- confidence,
- frequency of prior use,
- support from other memory types.

Possible scoring formula:
- `score = w1 * similarity + w2 * recency + w3 * importance + w4 * confidence`
- weights are tunable and may vary by memory type.

### 6.5 Ranking

Rank results based on score and select the top-K for consumption.
Ranking may also use diversity heuristics to avoid redundant memory retrieval.

### 6.6 Recency and importance

Recency and importance are separate signals.
- Recency captures how recently a memory was updated or used.
- Importance measures long-term value and reliability.

A memory object can be old but still important; ranking should respect both.

### 6.7 Similarity

Similarity measures must be defined for each memory type:
- episodic similarity: state and trajectory similarity,
- semantic similarity: concept and fact proximity,
- procedural similarity: workflow structure and goal alignment,
- reflection similarity: meta-decision pattern match.

Similarity may combine vector embeddings, symbolic matching, and metadata overlap.

### 6.8 Memory types in retrieval

The retrieval pipeline should support type-specific retrieval strategies:
- Working Memory retrieval should be fast and exact.
- Episodic Memory retrieval should emphasize pattern and temporal similarity.
- Semantic Memory retrieval should focus on facts and attribute matching.
- Procedural Memory retrieval should emphasize workflow reusability.
- Reflection Memory retrieval should prioritize prior self-assessment in similar cognitive contexts.

### 6.9 Unified retrieval view

A MemoryManager can expose a unified retrieval API that hides the type-specific retrieval details. Consumers request relevant memory items; the manager decides which types to search.

## 7. Consolidation

Consolidation is the transformation of memories from raw episodes into stable cognitive structures.

### 7.1 What gets promoted?

Promote memories that are:
- repeatedly useful,
- associated with successful outcomes,
- reinforced by multiple episodes,
- conceptually generalizable,
- linked to stable user preferences.

### 7.2 When consolidation occurs

Consolidation triggers:
- after successful execution,
- after repeated retrieval of the same memory,
- after a reflection signal indicates a lesson learned,
- during low-load periods,
- during periodic maintenance cycles.

### 7.3 How consolidation works

#### Episodic to semantic
- extract stable facts and user preferences from episodes,
- generalize repeated contextual elements into semantic entries,
- create knowledge nodes from recurring environment facts.

#### Episodic to procedural
- identify repeated action sequences that led to success,
- abstract them into workflow templates,
- store reusable procedures with parameterized inputs.

#### Episodic to reflection
- archive reflection outcomes from important episodes,
- associate them with similar future situations.

#### Semantic to procedural
- build procedures from stable facts and heuristics.

#### Reflection-informed consolidation
- reflection memory influences what should be consolidated,
- if a plan was accepted with high confidence and later succeeded, it is a strong consolidation candidate.

### 7.4 Consolidation policies

Consolidation policies should include:
- minimum evidence threshold,
- repeat frequency threshold,
- diversity filtering,
- confidence weighting,
- temporal spacing.

The system should avoid premature consolidation of low-value or noisy data.

## 8. Forgetting

AURA's memory system should forget intentionally to remain efficient and relevant.

### 8.1 Why forgetting is needed

- reduce storage and retrieval overhead,
- eliminate obsolete or misleading memories,
- keep reasoning focused on relevant patterns,
- adapt to changing user needs.

### 8.2 Forgetting design

Forgetting is managed by:
- age decay,
- importance decay,
- duplicate removal,
- confidence decay,
- usage frequency.

### 8.3 Age decay

Memory strength gradually decreases over time unless reinforced. Older memories become less likely to be retrieved.

### 8.4 Importance decay

Importance decays if a memory is not used or if it is contradicted by later evidence.

### 8.5 Duplicate removal

Duplicate or near-duplicate memory items should be consolidated or removed to prevent clutter. Duplicates are defined by high similarity and overlapping context.

### 8.6 Confidence decay

If a memory's confidence is not reinforced by recent success, its effective retrieval score should decrease.

### 8.7 Deletion policies

Deletion should be conservative. Possible rules:
- remove memories below a low importance threshold after long inactivity,
- remove duplicates when a superior version exists,
- remove memories flagged as incorrect by reflection or by user correction,
- preserve audit logs of deletions to support traceability.

### 8.8 Memory prioritization

Memories should be ranked for retention using a combined score:
- `retention_score = alpha * importance + beta * recency + gamma * usage + delta * confidence`

Low retention score objects are candidates for decay or deletion.

## 9. Benchmarks

A purpose-built memory benchmark evaluates memory quality independently of planner or reasoner performance.

### 9.1 Memory Recall

Measures the fraction of relevant memories successfully retrieved for a given query or context.

### 9.2 Memory Precision

Measures the relevance of retrieved memories out of the retrieved set.

### 9.3 Memory Coverage

Measures how much of the useful experience space is represented in memory. Coverage can be measured by episode type, domain concepts, and user preference dimensions.

### 9.4 Memory Latency

Measures retrieval and encoding latency within the memory system.

### 9.5 Memory Utilization

Measures storage efficiency, growth rate, and the ratio of active to archived memories.

### 9.6 Consolidation Effectiveness

Measures how well the system promotes useful memories without promoting noise.

### 9.7 Forgetting Effectiveness

Measures whether obsolete memories are removed without degrading recall of important content.

### 9.8 Reflection-augmented memory metrics

Since AURA includes reflection memory, also measure:
- reflection recall for similar cognitive contexts,
- historical calibration of self-assessment,
- improvement rate following reflection.

## 10. Memory Interfaces and Integration

This section describes how subsystems should interact with the memory architecture.

### 10.1 MemoryManager concept

Every memory operation in AURA must go through MemoryManager. Nothing else may touch storage.

The MemoryManager is a coordination layer that exposes unified APIs for memory operations and delegates to specialized memory stores.

Its responsibilities are:
- manage memory type lifecycle,
- route retrieval requests to the appropriate memory types,
- orchestrate consolidation and forgetting,
- provide a unified memory view to the planner and reasoner,
- audit memory creation, update, and deletion,
- never store memory data itself.

MemoryManager also owns the memory policies that decide how stores are used:
- `RetrievalPolicy` selects eligible memory types for an automatic query.
- `ImportancePolicy` ranks returned records.
- `ConsolidationPolicy` defines future promotion eligibility.
- `ForgettingPolicy` defines future retention and removal eligibility.

Policies contain routing and decision rules only. They do not store memory records.

### 10.2 Subsystem integration

#### Goal Manager
- writes current goals and constraints into Working Memory,
- requests user preference facts from Semantic Memory,
- populates Working Memory with goal-related episodic context.

#### Beam Search Planner
- reads Working Memory for active constraints,
- asks MemoryManager to retrieve procedural options and episodic examples,
- writes candidate plans into Working Memory,
- does not access storage or retrieval engines directly.

#### Retrieval + Policy
- use MemoryManager to fetch relevant episodic and semantic data,
- write retrieval metadata into Working Memory for planning.

#### Experience Reasoner
- uses episodic and semantic memories to explain candidate plans,
- uses procedural memory to compare plan fragments,
- writes reasoning trace into Working Memory,
- reads Reflection Memory for prior self-assessments.

#### Meta-Reasoner
- evaluates reasoning outputs,
- writes reflection decisions into Reflection Memory via MemoryManager,
- may consult Reflection Memory for similar prior cognitive cases through MemoryManager.

#### Execution Logger
- completes episode records,
- writes raw episode data into Episodic Memory,
- flags outcomes for consolidation processes.

#### Memory Consolidation Engine
- periodically scans memory stores,
- promotes episodic patterns into procedural and semantic memory,
- triggers forgetting when needed,
- updates retention scores.

### 10.3 Memory API examples

A minimal MemoryManager interface includes:
- `store_working_memory(context)`
- `retrieve_working_memory(query)`
- `clear_working_memory()`
- `store_context_memory(context)`
- `retrieve_context_memory(query)`
- `update_context_memory(context_id, updates)`
- `store_episode(episode)`
- `retrieve_episodes(query, top_k)`
- `retrieve_similar_episodes(query, top_k)`
- `store_fact(fact)`
- `retrieve_facts(query)`
- `update_fact(fact_id, updates)`
- `store_procedure(procedure)`
- `retrieve_procedures(query)`
- `update_procedure(procedure_id, updates)`
- `store_reflection(reflection)`
- `retrieve_reflections(query)`
- `retrieve_auto(query, top_k)`
- `retrieve_failure_patterns(query)`
- `consolidate()`
- `decay()`
- `audit_log()`

### 10.4 Memory consistency and auditability

Memory operations must be auditable. Each memory object should carry:
- creation timestamp,
- source subsystem,
- confidence or strength,
- last access timestamp,
- update history or revision metadata.

The MemoryManager should expose a history view for tracing how a memory object evolved.

## 11. Component Roles and Responsibilities

### 11.1 MemoryManager

Coordinates all memory activity. It is not itself a memory store, but it controls flows and enforces policies.

Every subsystem uses MemoryManager to read or write memory. MemoryManager must never itself contain the data.

### 11.2 Working Memory Store

Holds in-flight items for the current decision episode. It is optimized for speed and short lifecycle.

### 11.3 Episodic Memory Store

Persists episodic events, indexing them by user, goal, outcome, and temporal features.

### 11.4 Semantic Memory Store

Stores stable facts and relationships. This store is optimized for query and attribute lookup.

### 11.5 Procedural Memory Store

Stores reusable workflows, templates, and subplans.

### 11.6 Reflection Memory Store

Stores self-assessment artifacts and meta-cognitive traces.

## 12. Memory Object Schemas

### 12.1 Working Memory Object

Fields:
- `memory_id`
- `context_id`
- `goal_id`
- `constraints`
- `current_state`
- `temporary_variables`
- `candidate_plans`
- `retrieval_results`
- `reasoning_state`
- `importance`
- `confidence`
- `last_accessed`
- `retrieval_count`
- `created_at`
- `updated_at`
- `source`

### 12.2 Episodic Memory Object

Fields:
- `memory_id`
- `episode_id`
- `user_id`
- `goal_description`
- `initial_state`
- `final_state`
- `actions`
- `outcome`
- `duration`
- `environment`
- `resources`
- `importance`
- `confidence`
- `last_accessed`
- `retrieval_count`
- `success_label`
- `metadata`
- `created_at`
- `updated_at`

### 12.3 Semantic Memory Object

Fields:
- `memory_id`
- `fact_id`
- `entity`
- `attribute`
- `value`
- `source`
- `valid_from`
- `valid_to`
- `confidence`
- `importance`
- `last_accessed`
- `retrieval_count`
- `tags`
- `created_at`
- `last_verified_at`

### 12.4 Procedural Memory Object

Fields:
- `memory_id`
- `procedure_id`
- `name`
- `description`
- `input_pattern`
- `steps`
- `goal_alignment`
- `success_rate`
- `usage_count`
- `confidence`
- `importance`
- `last_accessed`
- `retrieval_count`
- `tags`
- `created_at`
- `last_used_at`

### 12.5 Reflection Memory Object

Fields:
- `memory_id`
- `reflection_id`
- `episode_id`
- `plan_id`
- `decision`
- `reflection_score`
- `confidence`
- `evidence_sufficiency`
- `assumptions`
- `contradictions`
- `recommendation`
- `lessons`
- `importance`
- `last_accessed`
- `retrieval_count`
- `created_at`
- `updated_at`

## 13. Memory Metrics and Benchmarks

### 13.1 Memory Recall

Definition: the proportion of relevant memories retrieved for a query.

Formula: `recall = relevant_retrieved / relevant_total`

### 13.2 Memory Precision

Definition: the proportion of retrieved memories that are relevant.

Formula: `precision = relevant_retrieved / retrieved_total`

### 13.3 Memory Coverage

Definition: the degree to which memory stores relevant knowledge and experience for expected domains.

### 13.4 Memory Latency

Definition: time taken for retrieval and encoding operations.

### 13.5 Memory Utilization

Definition: storage efficiency and active memory ratio.

### 13.6 Consolidation Effectiveness

Definition: the ratio of promoted memories that remain useful.

### 13.7 Forgetting Effectiveness

Definition: the ratio of removed memories that were obsolete or low-value, without harming overall recall.

### 13.8 Reflection Memory Metrics

- reflection recall,
- self-assessment calibration,
- improvement rate after reflection.

## 14. Memory Governance

### 14.1 Memory policies

Define policies for:
- what counts as high-value memory,
- what can be consolidated,
- when forgetting is permitted,
- how to handle user-corrected memories.

### 14.2 Audit and traceability

Every memory operation should be auditable. Memory objects should preserve a revision and deletion history.

### 14.3 Privacy and safety

Memory should preserve user privacy and respect constraints on sensitive data. MemoryManager should support redaction, obfuscation, and deletion requests.

## 15. Implementation Guidance

This specification is intentionally architecture-first. Implementation should follow these principles:
- do not create unnecessary new modules,
- every memory operation must go through MemoryManager,
- keep memory operations centralized through the MemoryManager,
- keep memory type responsibilities clear,
- MemoryManager must not store the data itself,
- reuse existing planning, retrieval, reasoning, and reflection infrastructure,
- make memory interfaces stable and backward-compatible.

## 16. Next Steps

1. Freeze this memory architecture design.
2. Review and refine with engineering partners.
3. Define data model schemas in a follow-up document.
4. Only then begin implementation.

## Appendix A: Example Flows

### A.1 Retrieval-assisted planning with memory
1. Goal Manager receives a goal.
2. Working Memory is populated with current context.
3. Beam Search Planner asks MemoryManager for supporting memories.
4. MemoryManager retrieves episodic cases, semantic facts, procedural templates, and context.
5. Beam Search Planner uses memory-enhanced candidates.
6. Experience Reasoner explains the top plan.
7. Meta-Reasoner evaluates the reasoning.
8. MemoryManager stores the reflection outcome in Reflection Memory.
9. MemoryManager triggers consolidation and forgetting as needed.
8. Execution occurs.
9. The Episode is written to Episodic Memory.
10. Consolidation is triggered after outcome evaluation.

### A.2 Memory consolidation example
1. A repeated action sequence is identified across episodes.
2. Procedural Memory candidate is generated.
3. The candidate is scored by success rate and generality.
4. If thresholds are met, the candidate is promoted to Procedural Memory.
5. The consolidated procedure becomes available for future planning.

### A.3 Forgetting example
1. An episodic record has low usage and low confidence.
2. Its retention score falls below threshold.
3. The item is flagged for decay.
4. After a grace period, the object is removed or archived.
5. Deletion is logged for audit.
