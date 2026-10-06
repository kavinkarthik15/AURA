import time
from copy import deepcopy
from typing import Any, Dict, List, Optional

from backend.compatibility.mg_compatibility import MGCompatibilityLayer
from backend.compatibility.mg_config import MGCompatibilityConfig
from backend.models.calibration_parameters import CalibrationParameters
from backend.models.simulated_state import SimulatedState
from backend.models.user_state import UserState
from backend.planning.probabilistic_transition import ProbabilisticTransitionModel
from backend.services.experience_service import experience_service
from backend.services.transition_engine import TransitionEngine
from backend.services.state_diff import calculate_state_diff


class SimulationEngine:
    def __init__(
        self,
        transition_engine: TransitionEngine | None = None,
        probabilistic_model: ProbabilisticTransitionModel | None = None,
        calibration_parameters: CalibrationParameters | None = None,
        mg_config: Optional[MGCompatibilityConfig] = None,
        shadow_event_recorder: Any | None = None,
    ) -> None:
        self.calibration_parameters = calibration_parameters
        self.transition_engine = transition_engine or TransitionEngine(experiences=experience_service.get_all_experiences())
        self.probabilistic_model = probabilistic_model or ProbabilisticTransitionModel()
        self.shadow_event_recorder = shadow_event_recorder
        
        # MG compatibility layer (disabled by default)
        self.mg_config = mg_config or MGCompatibilityConfig()
        self.mg_layer = MGCompatibilityLayer(self.mg_config)

    def _record_shadow_event(self, event: Dict[str, Any]) -> None:
        """Record shadow-only observations without affecting the production path."""
        if self.shadow_event_recorder is None:
            return

        try:
            if hasattr(self.shadow_event_recorder, "record"):
                self.shadow_event_recorder.record(event)
                return
            if isinstance(self.shadow_event_recorder, list):
                self.shadow_event_recorder.append(event)
                return
            if callable(self.shadow_event_recorder):
                self.shadow_event_recorder(event)
                return
        except Exception:
            # Shadow logging must never fail the production response path.
            return

    def _classify_outcome(self, probability: float) -> str:
        if probability >= 0.75:
            return "Positive"
        if probability >= 0.45:
            return "Neutral"
        return "Negative"

    def simulate_action(self, current_state: Dict[str, int], action: str, category: Optional[str] = None) -> Dict:
        predicted_growth = self.transition_engine.predict_skill_growth(current_state, action)
        predicted_success = self.transition_engine.predict_success_probability(current_state, action)

        future_state = dict(current_state)
        for skill, gain in predicted_growth.items():
            future_state[skill] = int(current_state.get(skill, 0) + gain)

        confidence = max(0.0, min(1.0, 0.5 + predicted_success * 0.4))
        if self.calibration_parameters is not None:
            future_state, confidence = self._apply_calibration_bias(future_state, confidence)

        expected_outcome = self._classify_outcome(predicted_success)
        legacy_prediction = {
            "current_state": dict(current_state),
            "predicted_future_state": future_state,
            "confidence": round(confidence, 2),
            "expected_outcome": expected_outcome,
        }

        # MG Compatibility Layer Hook (< 5 lines, minimal integration)
        # Measure latency of actual MG computation for observability
        mg_start_time = time.perf_counter() if self.shadow_event_recorder is not None else None
        corrected_prediction, mg_metadata = self.mg_layer.apply(
            legacy_prediction, current_state, action, category=category
        )
        mg_latency_ms = (time.perf_counter() - mg_start_time) * 1000 if mg_start_time is not None else 0
        
        if self.mg_config.emit_diagnostic_metadata:
            corrected_prediction["_mg_metadata"] = mg_metadata.to_dict()

        if self.shadow_event_recorder is not None:
            record = {
                "experience_id": None,
                "seed": None,
                "category": category,
                "action": action,
                "legacy_prediction": dict(legacy_prediction),
                "mg_shadow_prediction": dict(corrected_prediction),
                "mg_correction": {
                    "source": mg_metadata.source,
                    "correction_applied": mg_metadata.correction_applied,
                    "correction_value": mg_metadata.correction_value,
                },
                "motivation_signal": mg_metadata.motivation_signal,
                "goals_signal": mg_metadata.goals_signal,
                "fallback_triggered": mg_metadata.fallback_triggered,
                "fallback_reason": mg_metadata.fallback_reason,
                "legacy_latency_ms": 0,
                "mg_latency_ms": mg_latency_ms,
                "mg_error": mg_metadata.computation_error,
            }
            self._record_shadow_event(record)

        return corrected_prediction

    def _apply_calibration_bias(self, future_state: Dict[str, int], confidence: float) -> tuple[Dict[str, int], float]:
        calibrated = dict(future_state)
        for key, bias in self.calibration_parameters.expected_state_bias.items():
            calibrated[key] = int(calibrated.get(key, 0) + float(bias))

        adjusted_confidence = confidence + (self.calibration_parameters.confidence - 0.5) * 0.2
        adjusted_confidence -= self.calibration_parameters.uncertainty * 0.1
        adjusted_confidence = round(min(0.99, max(0.0, adjusted_confidence)), 2)
        return calibrated, adjusted_confidence

    def simulate_plan(self, current_state: Dict[str, int], actions: List[str]) -> Dict:
        state = dict(current_state)
        steps = []
        for action in actions:
            result = self.simulate_action(state, action)
            state = result["predicted_future_state"]
            steps.append(
                {
                    "action": action,
                    "predicted_future_state": state,
                    "confidence": result["confidence"],
                    "expected_outcome": result["expected_outcome"],
                }
            )

        success_probability = min(1.0, 0.5 + (len(steps) * 0.08))
        expected_outcome = self._classify_outcome(success_probability)
        return {
            "steps": steps,
            "predicted_future_state": state,
            "final_state": state,
            "success_probability": round(success_probability, 2),
            "expected_outcome": expected_outcome,
            "summary": f"Python: {current_state.get('python', 0)} -> {state.get('python', 0)}",
        }

    def simulate_snapshot_action(self, snapshot: SimulatedState, action: str) -> Dict:
        return self.apply_action(snapshot, action)

    def apply_action(self, snapshot: SimulatedState, action: str, context: Dict | None = None) -> Dict:
        if not isinstance(action, str) or not action.strip():
            raise ValueError("Action must be a non-empty string")

        current_state = UserState(
            skills=dict(snapshot.skills),
            knowledge=dict(snapshot.knowledge),
            projects=dict(snapshot.projects),
            goals=dict(snapshot.goals),
            learning=dict(snapshot.learning),
        )
        simulated_result = self.simulate_action(snapshot.skills, action)

        next_state = UserState(
            skills=dict(current_state.skills),
            knowledge=dict(current_state.knowledge),
            projects=dict(current_state.projects),
            goals=dict(current_state.goals),
            learning=dict(current_state.learning),
        )
        next_state.skills = dict(next_state.skills)
        next_state.skills.update(simulated_result["predicted_future_state"])

        next_snapshot = SimulatedState(
            skills=dict(next_state.skills),
            knowledge=dict(next_state.knowledge),
            projects=dict(next_state.projects),
            goals=dict(next_state.goals),
            learning=dict(next_state.learning),
            source_state_id=snapshot.snapshot_id or snapshot.source_state_id,
            simulation_id=snapshot.simulation_id,
            step=snapshot.step + 1,
            parent_snapshot_id=snapshot.snapshot_id,
            snapshot_id=None,
            metadata={
                "action": action,
                "confidence": simulated_result["confidence"],
                "context": dict(context or {}),
            },
        )
        diff = calculate_state_diff(current_state, next_state)
        return {
            "previous_snapshot": snapshot,
            "next_snapshot": next_snapshot,
            "diff": diff,
            "action": action,
            "confidence": simulated_result["confidence"],
            "expected_outcome": simulated_result["expected_outcome"],
        }

    def _snapshot_from_state(self, snapshot: SimulatedState, state: Dict[str, Any], step: int, snapshot_id: str | None = None, probability: float | None = None) -> SimulatedState:
        skills = deepcopy(snapshot.skills)
        knowledge = deepcopy(snapshot.knowledge)
        projects = deepcopy(snapshot.projects)
        goals = deepcopy(snapshot.goals)
        learning = deepcopy(snapshot.learning)

        for key, value in state.items():
            if key == "confidence":
                continue
            if not isinstance(value, (int, float)):
                continue
            val = int(value)
            if key in skills:
                skills[key] = val
            elif key in knowledge:
                knowledge[key] = val
            elif key in projects:
                projects[key] = val
            elif key in goals:
                goals[key] = val
            elif key in learning:
                learning[key] = val
            else:
                skills[key] = val

        metadata = {
            "action": state.get("action") if "action" in state else None,
            "probability": probability,
        }
        metadata = {k: v for k, v in metadata.items() if v is not None}

        return SimulatedState(
            skills=skills,
            knowledge=knowledge,
            projects=projects,
            goals=goals,
            learning=learning,
            source_state_id=snapshot.snapshot_id or snapshot.source_state_id,
            simulation_id=snapshot.simulation_id,
            step=step,
            parent_snapshot_id=snapshot.snapshot_id,
            snapshot_id=snapshot_id,
            metadata=metadata,
        )

    def make_snapshot(
        self,
        current_state: Dict[str, Any],
        *,
        simulation_id: str,
        step: int,
        snapshot_id: str | None = None,
        parent_snapshot_id: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> SimulatedState:
        skills = {k: int(v) for k, v in current_state.items() if isinstance(v, (int, float))}
        return SimulatedState(
            skills=skills,
            knowledge={},
            projects={},
            goals={},
            learning={},
            source_state_id=parent_snapshot_id,
            simulation_id=simulation_id,
            step=step,
            parent_snapshot_id=parent_snapshot_id,
            snapshot_id=snapshot_id,
            metadata=dict(metadata or {}),
        )

    def simulate_probabilistic_action(self, snapshot: SimulatedState, action: str, context: Dict | None = None) -> Dict:
        if not isinstance(action, str) or not action.strip():
            raise ValueError("Action must be a non-empty string")

        current_state = {**snapshot.skills, **snapshot.knowledge, **snapshot.projects, **snapshot.goals, **snapshot.learning}
        transition = self.probabilistic_model.predict(current_state, action, context=context)

        branches = []
        for index, (state, probability) in enumerate(zip(transition.possible_states, transition.probabilities), start=1):
            snapshot_id = f"{snapshot.snapshot_id}.{index}" if snapshot.snapshot_id else None
            next_snapshot = self._snapshot_from_state(
                snapshot=snapshot,
                state=state,
                step=snapshot.step + 1,
                snapshot_id=snapshot_id,
                probability=probability,
            )
            # ensure the originating action is recorded on the branch snapshot
            try:
                next_snapshot.metadata["action"] = str(action)
            except Exception:
                next_snapshot.metadata = {**next_snapshot.metadata, "action": str(action)}
            diff = calculate_state_diff(snapshot, next_snapshot)
            branches.append(
                {
                    "next_snapshot": next_snapshot,
                    "probability": probability,
                    "diff": diff,
                    "evidence": list(transition.evidence),
                }
            )

        return {
            "previous_snapshot": snapshot,
            "transition": transition,
            "branches": branches,
        }

    def simulate_sequence(self, snapshot: SimulatedState, actions: List[str], context: Dict | None = None) -> Dict:
        """Apply a sequence of actions to a snapshot, returning the trajectory.

        Returns a dict with:
          - initial_snapshot
          - steps: list of {previous_snapshot, next_snapshot, diff, action, confidence, expected_outcome}
          - final_snapshot
          - stopped_early: True if an action failed
        """
        trajectory = []
        current = snapshot
        stopped_early = False

        for action in actions:
            try:
                result = self.apply_action(current, action, context=context)
            except Exception as exc:
                # stop the sequence and report where we failed
                stopped_early = True
                trajectory.append({
                    "previous_snapshot": current,
                    "error": str(exc),
                    "action": action,
                })
                break

            trajectory.append(result)
            current = result["next_snapshot"]

        return {
            "initial_snapshot": snapshot,
            "steps": trajectory,
            "final_snapshot": current,
            "stopped_early": stopped_early,
        }

    def simulate_trajectory(self, snapshot: SimulatedState, actions: List[str], context: Dict | None = None):
        """Higher-level trajectory builder that returns a SimulationTrajectory.

        - Uses existing apply_action for deterministic steps
        - Uses simulate_probabilistic_action when probabilistic branches are desired
        - Does not change BeamNode or evaluator semantics
        """
        from backend.models.simulation_trajectory import SimulationTrajectory, BranchInfo

        traj = SimulationTrajectory(initial_snapshot=snapshot)
        traj.actions = list(actions or [])
        current = snapshot
        cumulative_prob = 1.0

        for action in actions or []:
            # apply deterministic step to get a next snapshot and diff
            try:
                result = self.apply_action(current, action, context=context)
            except Exception:
                # on error, invalidate the trajectory
                return traj

            next_snapshot = result["next_snapshot"]
            diff = result.get("diff", {})

            # attach
            traj.snapshots.append(next_snapshot)
            traj.diffs.append(diff)
            traj.branch_info.append(None)

            # next
            current = next_snapshot

        traj.cumulative_probability = cumulative_prob
        return traj

    def simulate_branching_trajectory(self, snapshot: SimulatedState, actions: List[str], context: Dict | None = None, max_branches: int | None = None):
        """Simulate a branching trajectory (probabilistic tree) using `simulate_probabilistic_action`.

        - Each edge carries `probability_from_parent`.
        - Parent links are weak refs (non-serialized).
        - `max_branches` caps per-node branching (sets `stopped_early` when applied).
        - On invalid action, stops expansion and marks tree `stopped_early`.
        """
        from backend.models.simulation_trajectory_tree import SimulationTrajectoryTree, SimulationTrajectoryNode

        root = SimulationTrajectoryNode(snapshot=snapshot, action_from_parent=None, diff_from_parent=None, probability_from_parent=1.0, _parent_ref=None)
        tree = SimulationTrajectoryTree(root=root, stopped_early=False)

        frontier: List[SimulationTrajectoryNode] = [root]

        for action in list(actions or []):
            new_frontier: List[SimulationTrajectoryNode] = []
            for node in frontier:
                try:
                    result = self.simulate_probabilistic_action(node.snapshot, action, context=context)
                except Exception:
                    tree.stopped_early = True
                    return tree

                branches = list(result.get("branches", []))
                if max_branches is not None and len(branches) > max_branches:
                    branches = branches[:max_branches]
                    tree.stopped_early = True

                for branch in branches:
                    next_snapshot = branch.get("next_snapshot")
                    probability = float(branch.get("probability", 0.0))
                    diff = branch.get("diff", {})

                    child = SimulationTrajectoryNode(
                        snapshot=next_snapshot,
                        action_from_parent=action,
                        diff_from_parent=diff,
                        probability_from_parent=probability,
                        _parent_ref=None,
                    )
                    child.parent = node
                    node.children.append(child)
                    new_frontier.append(child)

            frontier = new_frontier

        return tree


simulation_engine = SimulationEngine()
