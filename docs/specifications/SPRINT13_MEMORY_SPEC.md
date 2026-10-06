# Sprint 13 Memory Specification

## Overview

Sprint 13 introduces a unified memory layer for AURA. The goal is to make memory an active orchestration capability rather than a set of disconnected helpers.

## Scope

### 13.1 MemoryManager
- Introduce a central MemoryManager that owns all memory operations.
- Ensure planners, reasoners, and meta-reasoners use MemoryManager instead of calling storage components directly.

### 13.2 Working Memory
- Implement short-lived working memory for the active reasoning cycle.
- Support create, update, retrieve, clear, and expiry semantics.

### 13.3 Episodic Memory
- Store execution episodes with context, outcomes, actions, and metadata.
- Support similarity-based retrieval and recent-success retrieval.

### 13.4 Semantic Memory
- Store stable facts, preferences, rules, and entity relationships.
- Support fact creation, retrieval, updating, and merge behavior.

### 13.5 Procedural Memory
- Store reusable workflows and successful plan fragments.
- Support workflow storage, retrieval, and updates.

### 13.6 Reflection Memory Integration
- Connect reflection outcomes to the memory layer.
- Allow reflection records to be retrieved for failure-pattern analysis and improvement review.

### 13.7 Consolidation
- Promote high-value memories from episodic traces into semantic and procedural memory.
- Define lightweight consolidation heuristics.

### 13.8 Forgetting
- Implement conservative forgetting based on decay, usefulness, and age.
- Preserve auditability and avoid destructive deletion without policy support.

### 13.9 Benchmark
- Add memory benchmarks for retrieval quality, consolidation quality, and forgetting effectiveness.

### 13.10 Full Integration
- Integrate MemoryManager into planning, reasoning, reflection, and evaluation flows.
- Preserve existing public interfaces while adding memory support behind them.

## Constraints

- Do not break existing planner or reasoner interfaces unless absolutely necessary.
- Prefer extension over replacement.
- Ensure tests and documentation accompany each implementation increment.
