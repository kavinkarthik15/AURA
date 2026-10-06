# Architecture

## Overview
AURA now has a layered memory architecture that separates short-lived working state from long-term knowledge stores.

## Memory Layer
- Working Memory remains independent and stores transient session data.
- Episodic Memory stores event-like experiences and is backed by an experience index and retriever.
- Semantic Memory now stores generalized knowledge objects and is backed by a knowledge index and retriever.

## Core Components
- MemoryManager is the single public gateway for memory operations.
- SemanticMemory owns canonical knowledge records, lifecycle state, and retrieval events.
- KnowledgeIndex provides index, update, delete, search, rebuild, and statistics operations for knowledge records.
- KnowledgeRetriever performs explainable ranking over semantic knowledge using similarity, importance, confidence, and freshness.

## Data Flow
1. Working Memory captures transient reasoning context.
2. Episodic Memory persists experiences for later retrieval.
3. Semantic Memory stores generalized knowledge derived from repeated or meaningful experiences.
4. MemoryManager routes CRUD and lifecycle operations to the appropriate store.

## Status
- Working Memory: implemented
- Episodic Memory: implemented
- Semantic Memory: implemented
- Registry integration: enabled
