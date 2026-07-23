# AURA Architecture V1

## Overview

AURA is a skill-learning intelligence system that models how a user grows over time through experiences, predicts future state transitions, and recommends plans that maximize progress toward goals.

The architecture is intentionally grounded in observed experience data rather than external models. The core loop is:

Experience
↓
Transition Engine
↓
Digital Twin
↓
Goal Planner
↓
Recommendation

---

## 1. State Schema

AURA maintains a structured state that captures the user’s current capability profile.

### Core State Blocks

- skills
  - numeric skill values such as python, dsa, ml, sql, statistics
- knowledge
  - domain knowledge areas such as machine learning, data science, industry knowledge
- projects
  - project accomplishments or project-specific progress indicators
- learning
  - behavioral and learning traits such as consistency, focus, confidence, communication
- goals
  - target outcomes or aspirational milestones

### Example

```json
{
  "skills": {
    "python": 50,
    "dsa": 30,
    "ml": 20
  },
  "knowledge": {
    "machine_learning": 20,
    "industry_knowledge": 15
  },
  "projects": {
    "python_project": 1
  },
  "learning": {
    "consistency": 60,
    "focus": 55,
    "confidence": 40
  },
  "goals": {
    "python_mastery": 80
  }
}
```

---

## 2. Experience Schema

Experiences are the main training signals for AURA. Each experience records what happened, how the state changed, and how successful it was.

### Required Fields

- state_before
  - the state before the action occurred
- action
  - the activity or experience name
- context
  - metadata such as hours spent, stress, semester, or environment
- state_after
  - the resulting state after the action
- state_delta
  - the measured change in the state
- outcome
  - the observed result of the experience
- confidence
  - the confidence of the experience data
- weight
  - a weight used to influence transition learning

### Example

```json
{
  "state_before": {
    "python": 50,
    "dsa": 30
  },
  "action": "Python Project",
  "context": {
    "hours_spent": 12,
    "stress": 60,
    "semester": 6
  },
  "state_after": {
    "python": 60,
    "dsa": 32
  },
  "state_delta": {
    "python": 10,
    "dsa": 2
  },
  "outcome": 0.82,
  "confidence": 0.8,
  "weight": 1.2
}
```

---

## 3. Learning Pipeline

AURA learns and reasons through a sequential pipeline.

### Pipeline Overview

1. Experience
   - A user action or observed event is recorded.
2. Transition Engine
   - The system compares the current state and action against historical experiences.
3. Digital Twin
   - The system simulates future states across candidate action sequences.
4. Goal Planner
   - The system identifies actions that help close the gap to the target state.
5. Recommendation
   - The system selects the best plan and produces a predicted outcome.

### Purpose of Each Stage

- Experience
  - supply the empirical evidence that drives the model
- Transition Engine
  - estimate how an action changes a state
- Digital Twin
  - simulate future states over multiple steps
- Goal Planner
  - generate candidate plans toward a target goal
- Recommendation
  - rank and select the best plan

---

## 4. Core Design Principles

- Use observed experiences as the primary source of truth.
- Prefer transparent, explainable heuristics over opaque black-box decisions.
- Simulate plans step-by-step before recommending action sequences.
- Base progress reporting on goal attainment rather than only raw numeric gain.

---

## 5. Sprint 6 Intent

The current architecture supports:

- state modeling
- experience recording
- transition-based prediction
- multi-step simulation
- candidate plan generation
- plan evaluation and recommendation

This establishes the first working digital-twin-style prototype for AURA.
