# Execution Engine

## Execution Lifecycle
1. Start execution with a recommended plan and goal.
2. The engine marks the execution as RUNNING and sets the first action as current.
3. Actions can be completed, skipped, or failed.
4. Progress is calculated as completed actions divided by total actions.
5. When all actions are processed, the execution reaches COMPLETED.

## State Transitions
- NOT_STARTED -> RUNNING
- RUNNING -> PAUSED
- RUNNING -> COMPLETED
- RUNNING -> FAILED
- RUNNING -> CANCELLED

## API Methods
- start_execution(plan_name, goal_name, actions, confidence=0.0)
- complete_current_action()
- skip_current_action()
- fail_current_action()
- next_action()
- finish_execution()
- get_execution()

## Event Model
Each state change creates an event with:
- timestamp
- action
- status
- step

These events will later support experience logging in Sprint 10.2.

## Integration Notes
The execution engine is designed to work on top of the recommendation flow from the planning stack, without changing the search and simulation pipeline.
