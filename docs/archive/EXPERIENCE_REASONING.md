# Experience Reasoning

## Overview

Sprint 11.3 adds an experience reasoning layer so the planner can explain why a plan was recommended and compare similar historical executions before committing to an action.

## Components

- ExperienceReasoner compares retrieved experiences and extracts common success and failure patterns.
- PlanExplainer turns those findings into human-readable explanations.
- CounterfactualPlanner generates simple alternative plan variants.
- ContradictionDetector highlights conflicts between experiences.
- ExperienceClusterer groups experiences into high-level goal categories.
- CausalPatternMiner surfaces simple causal-style rules from successful episodes.
