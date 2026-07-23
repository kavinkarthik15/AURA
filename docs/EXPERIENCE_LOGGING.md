# Experience Logging

## Architecture
Execution results flow through the logging pipeline so that future planning can learn from actual outcomes.

## Data Flow
1. The execution engine runs a recommended plan.
2. The tracker records execution events.
3. The experience logger converts the execution outcome into a persistent experience entry.
4. The outcome analyzer computes prediction and execution metrics.
5. The experience dataset becomes the foundation for future retraining and evaluation.

## Experience Schema
Each experience stores:
- execution_id
- plan_name
- goal_name
- initial_state
- predicted_state
- actual_state
- predicted_growth
- actual_growth
- prediction_error
- actions
- completed_actions
- failed_actions
- skipped_actions
- execution_time
- success
- created_at

## Outcome Metrics
The outcome analyzer reports:
- prediction_error
- goal_progress
- completion_rate
- success_rate
- confidence_error

## Integration with Continual Learning
These experiences will later serve as the training corpus for model updates and planner improvement.
