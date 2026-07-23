import time
from typing import Dict, List

from backend.models.goal_state import GoalState
from backend.models.search_metrics import SearchMetrics
from backend.services.action_library import action_library
from backend.services.plan_expander import PlanExpander
from backend.services.planner_config import DEFAULT_BEAM_WIDTH, DEFAULT_MAX_DEPTH
from backend.services.search_state import SearchState


class BeamSearchPlanner:
    def __init__(self, action_library_instance=None, expander: PlanExpander | None = None) -> None:
        self.action_library = action_library_instance or action_library
        self.expander = expander or PlanExpander(action_library_instance=self.action_library)

    def search(self, current_state: Dict[str, int], goal_state: GoalState, beam_width: int = DEFAULT_BEAM_WIDTH, max_depth: int = DEFAULT_MAX_DEPTH) -> Dict:
        start_time = time.perf_counter()
        root = SearchState(actions=[], current_state=current_state.copy(), score=0.0, depth=0)
        beam = [root]
        metrics = SearchMetrics(beam_width=beam_width, search_depth=max_depth)
        search_trace: Dict[str, List[Dict]] = {}

        for depth in range(max_depth):
            expanded_states: List[SearchState] = []
            for state in beam:
                next_actions = self.expander.get_possible_next_actions(state.current_state, goal_state)
                metrics.plans_generated += len(next_actions)
                for action in next_actions:
                    next_state = state.current_state.copy()
                    next_state = self._apply_action(next_state, action)
                    new_state = SearchState(
                        actions=[*state.actions, action],
                        current_state=next_state,
                        score=self._score_state(next_state, goal_state),
                        depth=state.depth + 1,
                        goal_progress=self._goal_progress(next_state, goal_state),
                        confidence=self._confidence(next_state, goal_state),
                    )
                    expanded_states.append(new_state)

            if not expanded_states:
                break

            ranked_states = sorted(expanded_states, key=lambda item: (item.score, item.goal_progress, item.confidence), reverse=True)
            beam = ranked_states[:beam_width]
            metrics.plans_evaluated += len(ranked_states)
            search_trace[f"depth_{depth + 1}"] = [
                {
                    "actions": state.actions,
                    "score": state.score,
                    "goal_progress": state.goal_progress,
                    "confidence": state.confidence,
                }
                for state in ranked_states[:beam_width]
            ]

        if not beam:
            return {
                "best_plan": [],
                "score": 0.0,
                "plans_evaluated": metrics.plans_evaluated,
                "search_depth": max_depth,
                "beam_width": beam_width,
                "search_metrics": metrics.to_dict(),
            }

        best_state = max(beam, key=lambda item: (item.score, item.goal_progress, item.confidence))
        metrics.search_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "best_plan": best_state.actions,
            "score": round(best_state.score, 2),
            "plans_evaluated": metrics.plans_evaluated,
            "search_depth": max_depth,
            "beam_width": beam_width,
            "search_metrics": metrics.to_dict(),
            "search_trace": search_trace,
        }

    def _apply_action(self, state: Dict[str, int], action_name: str) -> Dict[str, int]:
        updated = state.copy()
        action = self.action_library.get_action(action_name)
        if not action:
            return updated

        for skill in ["python", "dsa", "projects"]:
            if skill in updated:
                updated[skill] = updated.get(skill, 0) + int(action.get("estimated_skill_gain", 0) / 3)
        if "projects" in updated:
            updated["projects"] = updated.get("projects", 0) + 1
        return updated

    def _score_state(self, state: Dict[str, int], goal_state: GoalState) -> float:
        if not goal_state.target_skills:
            return 0.0

        progress_values = []
        for skill, target_goal in goal_state.target_skills.items():
            current_value = state.get(skill, 0)
            progress_values.append(max(0, min(1, current_value / max(1, target_goal))))
        return round(sum(progress_values) / len(progress_values), 2) if progress_values else 0.0

    def _goal_progress(self, state: Dict[str, int], goal_state: GoalState) -> float:
        progress_values = []
        for skill, target_goal in goal_state.target_skills.items():
            current = state.get(skill, 0)
            progress_values.append(min(1.0, current / max(1, target_goal)))
        return round(sum(progress_values) / len(progress_values), 2) if progress_values else 0.0

    def _confidence(self, state: Dict[str, int], goal_state: GoalState) -> float:
        return round(min(1.0, self._goal_progress(state, goal_state) + 0.1), 2)
