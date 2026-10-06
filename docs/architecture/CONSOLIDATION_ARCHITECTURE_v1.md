# Consolidation Architecture v1

## 1. Purpose

This architecture defines how AURA converts repeated episodic experiences into generalized semantic knowledge. The consolidation layer is the bridge between raw memory of events and reusable knowledge for reasoning.

### Why consolidation exists
- Episodic memory captures what happened.
- Semantic memory stores what is generally true.
- Consolidation turns repeated evidence into durable knowledge that can support future planning and reasoning.

### Difference between Episodic and Semantic Memory
- Episodic memory stores event-based experiences with time, context, and outcome.
- Semantic memory stores generalized knowledge that is stable, reusable, and traceable to supporting evidence.
- Not every experience should become knowledge. Only experiences that are repeated, meaningful, or structurally significant should be promoted.

---

## 2. High-Level Architecture

```text
Working Memory
        │
        ▼
Episodic Memory
        │
        ▼
Consolidation Engine
        │
 ┌──────┼────────┐
 │      │        │
 ▼      ▼        ▼
Pattern Detector
Knowledge Generator
Knowledge Merger
        │
        ▼
MemoryManager
        │
        ▼
Semantic Memory
```

### Architectural role
The Consolidation Engine is an orchestration layer. It does not own persistent data. It coordinates the flow of evidence from episodic memory into semantic memory through validation and merge operations.

---

## 3. Components

### Pattern Detector
Responsibilities:
- Cluster experiences by topic, behavior, or outcome
- Detect repetition
- Detect trends
- Detect habits
- Detect failure patterns
- Detect success patterns

#### Inputs
- Episodic records from Episodic Memory
- Working Memory context when available

#### Outputs
- Candidate patterns
- Evidence sets
- Suggested knowledge topics

### Knowledge Generator
Responsibilities:
- Transform episodic evidence into candidate KnowledgeRecord objects
- Produce generalized statements from repeated observations
- Attach evidence references to generated knowledge

#### Inputs
- Pattern output from Pattern Detector
- Episodic evidence

#### Outputs
- Candidate knowledge objects
- Candidate confidence estimates
- Candidate support evidence

### Knowledge Validator
Responsibilities:
- Check confidence against supporting evidence
- Check evidence count thresholds
- Check contradiction risk
- Check duplication against existing semantic knowledge
- Reject weak or insufficient candidates

#### Validation checks
- Minimum evidence count
- Stability over time
- Consistency across episodes
- Not too generic to be meaningless

### Knowledge Merger
Responsibilities:
- Compare a candidate knowledge object against existing semantic knowledge
- Decide whether to:
  - revise
  - merge
  - replace
  - ignore

#### Merge decision policy
- If the candidate is a refinement of existing knowledge, revise it.
- If the candidate overlaps strongly with existing knowledge, merge them.
- If the candidate contradicts existing knowledge without sufficient support, do not promote it automatically.
- If the candidate is redundant, ignore it.

### Consolidation Engine
Responsibilities:
- Coordinate Pattern Detector, Knowledge Generator, Knowledge Validator, and Knowledge Merger
- Invoke each stage in sequence
- Pass validated knowledge to MemoryManager for semantic storage

#### Design constraint
The Consolidation Engine owns no data itself. It acts as a workflow coordinator.

---

## 4. Knowledge Promotion Rules

Promotion should be conservative. AURA should only promote knowledge when it is both repeated and meaningful.

### Trigger model
Consolidation is not triggered on every single episode. In v1, the system uses a staged trigger model:

1. Every new episode is stored in Episodic Memory.
2. Consolidation runs when one of the following is true:
   - a batch of new episodes reaches the threshold of $N$ new episodes, where $N = 3$ for initial v1 promotion checks;
   - an explicit API call requests a consolidation pass;
   - a scheduled background cycle runs, such as once per hour or once per day.
3. Idle/background execution is allowed, but it must not replace the explicit and batch-based paths.

This makes consolidation predictable while still allowing asynchronous background execution.

### Promotion thresholds (v1)
The following thresholds are proposed for initial design:
- Minimum evidence count: 3 episodes
- Minimum confidence: 0.65
- Minimum repetition consistency: 70%
- Minimum support diversity: at least 2 distinct contexts
- Minimum meaningfulness score: above a defined baseline

These thresholds should be treated as defaults and may be tuned experimentally later.

### Configuration strategy
Promotion thresholds are not hardcoded as the only source of truth. In v1, they should live in a configuration layer such as a JSON or YAML policy file, with runtime defaults that can be overridden by the engine. This keeps the behavior explicit and makes future adaptive policies easier to introduce.

### Not promoted
- "Finished one assignment."
- "Tried a new framework once."
- "Had a short-lived successful run."

### Candidate
- "Finished ten Python assignments."
- "The user repeatedly completes backend tasks after studying core concepts."

### Promote
- "The user is proficient in Python."
- "The user learns backend technologies quickly."

### Promotion thresholds (v1)
The following thresholds are proposed for initial design:
- Minimum evidence count: 3 episodes
- Minimum confidence: 0.65
- Minimum repetition consistency: 70%
- Minimum support diversity: at least 2 distinct contexts
- Minimum meaningfulness score: above a defined baseline

These thresholds should be treated as defaults and may be tuned experimentally later.

---

## 5. Confidence Model

Confidence should grow gradually as more evidence accumulates.

### Expected behavior
- A single episode should not generate high-confidence knowledge.
- Confidence should increase with repeated support.
- Confidence should be reduced when evidence conflicts or is weak.

### Example progression
- 3 episodes -> confidence around 0.42
- 8 episodes -> confidence around 0.68
- 15 episodes -> confidence around 0.87

### Confidence rules
- Confidence should rise slowly and asymptotically.
- Contradictory evidence should lower confidence.
- Confidence should never jump instantly from one episode to a very high score.

### Confidence inputs
- Number of supporting episodes
- Consistency across episodes
- Strength of outcome
- Presence of contradictions
- Recency of evidence

---

## 6. Evidence Model

Every promoted knowledge record must remain traceable to supporting episodes.

### Required evidence structure
Each KnowledgeRecord should record:
- the knowledge statement
- supporting episode IDs
- supporting context summaries
- evidence timestamps
- evidence quality indicators
- promotion reason
- confidence calculation trace
- merge or revision history

### Explainability requirement
Every promoted knowledge record must be explainable. The engine should be able to answer:
- Why was this knowledge promoted?
- Which episodes supported it?
- How was confidence computed?
- Was it merged, revised, or created from scratch?

### Example
```text
Knowledge: User learns backend technologies quickly.

Evidence:
- Episode A
- Episode B
- Episode C
- Episode D
```

### Design requirement
Knowledge should never be opaque. Every semantic record should preserve its lineage back to episodic memory.

---

## 7. Revision Rules

Knowledge revision should be explicit and conservative.

### Example
Existing knowledge:
- "User prefers Flutter."

New evidence:
- "User has used React Native for six months."

### Revision policy
1. If the new evidence is a small refinement, update the existing statement.
2. If the new evidence supports the same concept with a different phrasing, merge the evidence and keep a single generalized statement.
3. If the new evidence strongly contradicts the old statement, create a new knowledge object or mark the prior knowledge as superseded.
4. If the evidence is weak or noisy, keep the original and add the evidence as supporting context only.

### Revision guidance
- Prefer revision over replacement when the semantic meaning remains similar.
- Prefer replacement only when the old knowledge is clearly obsolete.
- Prefer keeping both when the evidence indicates distinct concepts rather than one concept changing.

---

## 8. Conflict Resolution

Conflicts will occur when evidence points to different conclusions.

### Example
Knowledge A:
- "User enjoys morning study."

Knowledge B:
- "User studies mostly at night."

### Conflict policy
- If one statement is supported by much stronger evidence, prefer it.
- If both are true in different contexts, preserve both with distinct context labels.
- If the contradiction is due to noise, do not promote the conflicting candidate.
- If evidence is balanced but context differs, represent the knowledge as context-sensitive rather than globally true.

### Design rule
Contradictions should not be silently overwritten. They should be resolved through evidence quality, recency, and contextual fit.

---

## 9. Consolidation Pipeline

```text
Working Memory

↓

Episodic Memory

↓

Pattern Detection

↓

Knowledge Generation

↓

Validation

↓

Merge

↓

MemoryManager

↓

Semantic Memory
```

### Pipeline contract
- Working Memory supplies transient context.
- Episodic Memory provides the evidence base.
- The Consolidation Engine orchestrates the promotion flow.
- MemoryManager is the gateway for storing finalized semantic knowledge.
- Semantic Memory is the destination of validated and merged knowledge.

---

## 10. Metrics

Consolidation should be evaluated using explicit metrics.

### Evaluation strategy
The v1 evaluation strategy should combine unit tests, integration tests, and benchmark-style analysis.

### Unit tests
Unit tests should validate:
- threshold enforcement
- evidence aggregation logic
- confidence scoring
- merge/revision decisions
- explainability payload generation

### Integration tests
Integration tests should validate end-to-end behavior for:
- promotion after a threshold of new episodes
- promotion triggered through an explicit API call
- periodic scheduled consolidation
- storage and retrieval of promoted knowledge in Semantic Memory

### Benchmark and analysis approach
A small benchmark dataset should be assembled from repeated episodes with known semantic outcomes. The system should be evaluated on:
- Promotion Precision: how often promoted knowledge is later validated as useful
- Promotion Recall: how often meaningful knowledge is successfully promoted
- Duplicate Rate: frequency of near-duplicate knowledge objects
- Merge Accuracy: how often merge decisions are correct
- Knowledge Coverage: breadth of semantic knowledge relative to episodic evidence
- Knowledge Freshness: how current the promoted semantic knowledge remains
- Knowledge Confidence: average confidence of semantic records
- Consolidation Latency: time required to run a consolidation cycle

### Metric intent
These metrics should be used to evaluate whether consolidation improves reasoning quality and memory usefulness over time.

---

## 11. Deferred Features

The following features are explicitly out of scope for v1.

- LLM-generated knowledge
- Online learning
- Reinforcement-based updates
- Graph reasoning for knowledge relations
- Multi-user consolidation
- Self-supervised abstraction
- Distributed consolidation
- Fully autonomous semantic extraction

These are future enhancements and should not be included in the Sprint 13.5A design freeze.

---

## 12. Design Summary

Sprint 13.5A defines the consolidation architecture as a conservative, evidence-driven pipeline that converts repeated experiences into semantic knowledge. The system is intended to be:
- traceable
- cautious
- explainable
- merge-aware
- validation-driven

The design emphasizes stable knowledge formation without over-promoting weak or noisy evidence.
