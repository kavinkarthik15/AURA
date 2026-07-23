# AURA ER Diagram v1

Users
│
├── Goals
│      └── Tasks
│
├── Projects
│
├── Memories
│
├── User States
│
├── Experiences
│
└── Knowledge Assets

Relationships

Users (1) → (N) Goals

Goals (1) → (N) Tasks

Users (1) → (N) Projects

Users (1) → (N) Memories

Users (1) → (N) User States

Users (1) → (N) Experiences

Users (1) → (N) Knowledge Assets

User State Design Recommendation

For future AI modeling, the recommended approach is:

- Store one complete JSONB state snapshot per version
- Each version represents a full view of the user's state at a point in time
- This supports transition modeling as:

State(t) → Action → State(t+1)

This makes it easier to train predictive and planning systems later.