from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Protocol
from uuid import uuid4

from pydantic import ValidationError

from backend.models.prospective_prediction_episode import (
    EligibilityResult,
    EpisodeAuditEvent,
    EpisodeEventType,
    EpisodeStatus,
    ObservedOutcome,
    OutcomeSource,
    PracticeActionEvidence,
    PredictionBundle,
    PredictionTarget,
    ProspectivePredictionEpisode,
)
from backend.services.prospective_episode_store import ProspectiveEpisodeStore


class PredictionProvider(Protocol):
    def predict_pair(
        self,
        pre_action_state: dict[str, int],
        action: str,
        context: dict[str, Any],
    ) -> PredictionBundle: ...


class SimulationEnginePredictionProvider:
    """Captures the existing base/MG pair without changing SimulationEngine behavior."""

    def __init__(
        self,
        simulation_engine: Any,
        *,
        base_model_version: str,
        mg_model_version: str,
        mg_coefficients_version: str,
    ) -> None:
        self.simulation_engine = simulation_engine
        self.base_model_version = base_model_version
        self.mg_model_version = mg_model_version
        self.mg_coefficients_version = mg_coefficients_version

    def predict_pair(
        self,
        pre_action_state: dict[str, int],
        action: str,
        context: dict[str, Any],
    ) -> PredictionBundle:
        events: list[dict[str, Any]] = []
        source = self.simulation_engine
        from backend.services.simulation_engine import SimulationEngine

        capture_engine = SimulationEngine(
            transition_engine=source.transition_engine,
            probabilistic_model=source.probabilistic_model,
            calibration_parameters=source.calibration_parameters,
            mg_config=source.mg_config,
            shadow_event_recorder=events,
        )
        category = context.get("category")
        capture_engine.simulate_action(pre_action_state, action, category=category if isinstance(category, str) else None)
        if len(events) != 1:
            raise RuntimeError("simulation engine did not produce exactly one paired prediction record")
        event = events[0]
        configuration = source.mg_config.to_dict()
        config_bytes = json.dumps(configuration, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return PredictionBundle(
            base_prediction=deepcopy(event["legacy_prediction"]),
            mg_prediction=deepcopy(event["mg_shadow_prediction"]),
            base_model_version=self.base_model_version,
            mg_model_version=self.mg_model_version,
            mg_coefficients_version=self.mg_coefficients_version,
            mg_configuration_sha256=hashlib.sha256(config_bytes).hexdigest(),
        )


class ProspectiveEpisodeService:
    def __init__(
        self,
        store: ProspectiveEpisodeStore,
        prediction_provider: PredictionProvider,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.store = store
        self.prediction_provider = prediction_provider
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def create_prospective_episode(
        self,
        *,
        user_id: str,
        pre_action_state: dict[str, int],
        action: str,
        context: dict[str, Any],
        target: PredictionTarget,
        pilot_id: str | None = None,
        enrollment_id: str | None = None,
        baseline_assessment_session_id: str | None = None,
        baseline_submitted_at: datetime | None = None,
    ) -> ProspectivePredictionEpisode:
        normalized_user = self._required_text(user_id, "user_id")
        normalized_action = self._required_text(action, "action")
        if pilot_id is not None:
            if not enrollment_id or not baseline_assessment_session_id or baseline_submitted_at is None:
                raise ValueError("pilot episode creation requires a finalized baseline assessment")
            if baseline_submitted_at.tzinfo is None or baseline_submitted_at.utcoffset() is None:
                raise ValueError("baseline_submitted_at must include a timezone")
        elif any(value is not None for value in (enrollment_id, baseline_assessment_session_id, baseline_submitted_at)):
            raise ValueError("baseline linkage requires a pilot_id")
        if not isinstance(pre_action_state, dict) or not pre_action_state:
            raise ValueError("pre_action_state must be a non-empty career skills mapping")
        state = deepcopy(pre_action_state)
        for name, value in state.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("pre_action_state skill names must be non-empty strings")
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
                raise ValueError(f"pre_action_state[{name!r}] must be an integer on the 0-100 skill scale")
        if not isinstance(target, PredictionTarget):
            raise TypeError("target must be a validated PredictionTarget")
        target = PredictionTarget.model_validate(target.model_dump(mode="python"))
        if target.target_dimension != "skill" or target.target_name not in state:
            raise ValueError("target must identify an existing career skill in pre_action_state")
        if not isinstance(context, dict):
            raise ValueError("context must be a JSON object")
        safe_context = deepcopy(context)
        forbidden_context_keys = {
            "actual_outcome",
            "actual_state",
            "actual_state_after",
            "actual_future_state",
            "outcome",
            "outcome_value",
            "observed_outcome",
            "observed_result",
            "observed_state",
            "post_action_state",
        }
        self._reject_outcome_context(safe_context, forbidden_context_keys)
        try:
            json.dumps(safe_context, allow_nan=False)
        except (TypeError, ValueError) as error:
            raise ValueError("context must contain only finite JSON-compatible values") from error

        predictions = self.prediction_provider.predict_pair(deepcopy(state), normalized_action, deepcopy(safe_context))
        if not isinstance(predictions, PredictionBundle):
            raise TypeError("prediction provider must return a validated PredictionBundle")
        predictions = PredictionBundle.model_validate(deepcopy(predictions.model_dump(mode="python")))
        self._validate_target_predictions(predictions, target)

        frozen_at = self._now()
        if baseline_submitted_at is not None and baseline_submitted_at >= frozen_at:
            raise ValueError("baseline assessment must precede prediction freeze")
        episode_id = f"episode_{uuid4().hex}"
        episode = ProspectivePredictionEpisode(
            episode_id=episode_id,
            user_id=normalized_user,
            created_at=frozen_at,
            prediction_timestamp=frozen_at,
            pre_action_state=state,
            action=normalized_action,
            context=safe_context,
            predictions=predictions,
            target=target,
            pilot_id=pilot_id,
            enrollment_id=enrollment_id,
            baseline_assessment_session_id=baseline_assessment_session_id,
            outcome_due_at=frozen_at + timedelta(seconds=target.horizon_seconds),
            status=EpisodeStatus.PREDICTION_FROZEN,
        )
        self.store.create_episode(
            episode,
            [
                self._event(
                    episode,
                    EpisodeEventType.EPISODE_CREATED,
                    frozen_at,
                    {
                        "enrollment_id": enrollment_id,
                        "baseline_assessment_session_id": baseline_assessment_session_id,
                    },
                ),
                self._event(episode, EpisodeEventType.PREDICTION_FROZEN, frozen_at),
            ],
        )
        return episode

    def mark_action_started(self, episode_id: str, user_id: str) -> ProspectivePredictionEpisode:
        episode = self._get(episode_id, user_id)
        self._require_status(episode, EpisodeStatus.PREDICTION_FROZEN)
        started_at = self._now()
        if started_at <= episode.prediction_timestamp:
            raise ValueError("action must start after prediction freeze")
        updated = episode.model_copy(update={"status": EpisodeStatus.ACTION_STARTED, "action_started_at": started_at})
        self.store.update_episode(
            updated,
            [self._event(updated, EpisodeEventType.ACTION_STARTED, started_at)],
            expected_episode=episode,
        )
        return updated

    def record_action_completion_evidence(
        self,
        episode_id: str,
        user_id: str,
        evidence: PracticeActionEvidence | dict[str, Any],
    ) -> ProspectivePredictionEpisode:
        episode = self._get(episode_id, user_id)
        self._require_status(episode, EpisodeStatus.ACTION_COMPLETED)
        if episode.action_evidence is not None:
            raise ValueError("action completion evidence is immutable once recorded")
        try:
            payload = evidence.model_dump(mode="python") if isinstance(evidence, PracticeActionEvidence) else evidence
            validated = PracticeActionEvidence.model_validate(deepcopy(payload))
        except ValidationError as error:
            raise ValueError(f"action evidence failed schema validation: {error}") from error
        if episode.action_completed_at is None:
            raise ValueError("action must be completed before recording action evidence")
        if validated.participant_id != episode.user_id:
            raise ValueError("action evidence participant does not match episode owner")
        if episode.action_started_at is None or validated.started_at < episode.action_started_at:
            raise ValueError("module completion evidence must occur during the episode action")
        if validated.completed_at > episode.action_completed_at:
            raise ValueError("module completion evidence must not postdate episode action completion")
        if validated.started_at >= validated.completed_at:
            raise ValueError("module completion evidence must start before it completes")
        if validated.completion_status != "complete":
            raise ValueError("action evidence must prove a completed practice module")
        updated = episode.model_copy(update={"action_evidence": validated})
        self.store.update_episode(
            updated,
            [
                self._event(
                    updated,
                    EpisodeEventType.ACTION_EVIDENCE_RECORDED,
                    self._now(),
                    {
                        "module_id": validated.module_id,
                        "module_version": validated.module_version,
                        "module_hash": validated.module_hash,
                        "evidence_id": validated.evidence_id,
                    },
                )
            ],
            expected_episode=episode,
        )
        return updated

    def mark_action_completed(
        self,
        episode_id: str,
        user_id: str,
        *,
        performed_action: str,
    ) -> ProspectivePredictionEpisode:
        episode = self._get(episode_id, user_id)
        self._require_status(episode, EpisodeStatus.ACTION_STARTED)
        actual_action = self._required_text(performed_action, "performed_action")
        completed_at = self._now()
        if episode.action_started_at is None or completed_at <= episode.action_started_at:
            raise ValueError("action completion must be after action start")
        due_at = completed_at + timedelta(seconds=episode.target.horizon_seconds)
        action_matches = actual_action == episode.action
        updated = episode.model_copy(
            update={
                "status": EpisodeStatus.ACTION_COMPLETED if action_matches else EpisodeStatus.EXCLUDED,
                "action_completed_at": completed_at,
                "performed_action": actual_action,
                "outcome_due_at": due_at,
                "exclusion_reason": None if action_matches else "performed_action_did_not_match_frozen_action",
            }
        )
        events = [
            self._event(
                updated,
                EpisodeEventType.ACTION_COMPLETED,
                completed_at,
                {"performed_action": actual_action, "matched_frozen_action": action_matches},
            ),
        ]
        if not action_matches:
            events.append(
                self._event(
                    updated,
                    EpisodeEventType.EPISODE_EXCLUDED,
                    completed_at,
                    {"reason": updated.exclusion_reason},
                )
            )
        self.store.update_episode(updated, events, expected_episode=episode)
        return updated

    def mark_outcome_due(self, episode_id: str, user_id: str) -> ProspectivePredictionEpisode:
        episode = self._get(episode_id, user_id)
        self._require_status(episode, EpisodeStatus.ACTION_COMPLETED)
        now = self._now()
        if now < episode.outcome_due_at:
            raise ValueError("outcome follow-up is not due yet")
        updated = episode.model_copy(update={"status": EpisodeStatus.AWAITING_OUTCOME})
        self.store.update_episode(
            updated,
            [
                self._event(
                    updated,
                    EpisodeEventType.OUTCOME_DUE,
                    now,
                    {"scheduled_for": episode.outcome_due_at.isoformat()},
                )
            ],
            expected_episode=episode,
        )
        return updated

    def record_observed_outcome(
        self,
        episode_id: str,
        user_id: str,
        outcome: ObservedOutcome | dict[str, Any],
    ) -> ProspectivePredictionEpisode:
        episode = self._get(episode_id, user_id)
        self._require_status(episode, EpisodeStatus.AWAITING_OUTCOME)
        try:
            payload = outcome.model_dump(mode="python") if isinstance(outcome, ObservedOutcome) else outcome
            observed = ObservedOutcome.model_validate(deepcopy(payload))
        except ValidationError as error:
            raise ValueError(f"observed outcome failed provenance/schema validation: {error}") from error
        if observed.target_name != episode.target.target_name or observed.target_dimension != episode.target.target_dimension:
            raise ValueError("observed outcome target does not match the frozen prediction target")
        if observed.target_unit != episode.target.target_unit:
            raise ValueError("observed outcome unit does not match the frozen prediction target")
        if observed.target_scale != episode.target.target_scale:
            raise ValueError("observed outcome scale does not match the frozen prediction target")
        if observed.provenance.collection_method != episode.target.measurement_method:
            raise ValueError("outcome collection method does not match the predeclared target method")
        lower, upper = episode.target.valid_range
        if not lower <= observed.value <= upper:
            raise ValueError(f"observed outcome must be within the target range [{lower}, {upper}]")
        observed_at = self._aware_utc(observed.provenance.observed_at, "observed_at")
        now = self._now()
        if observed_at < episode.outcome_due_at:
            raise ValueError("outcome is premature; wait until outcome_due_at")
        if observed_at > now:
            raise ValueError("outcome observation timestamp cannot be in the future")
        if observed.provenance.quality <= 0:
            raise ValueError("outcome provenance quality must be greater than zero")

        updated = episode.model_copy(
            update={
                "status": EpisodeStatus.OUTCOME_RECORDED,
                "observed_outcome": observed,
                "outcome_quality": observed.provenance.quality,
            }
        )
        self.store.update_episode(
            updated,
            [
                self._event(
                    updated,
                    EpisodeEventType.OUTCOME_RECORDED,
                    now,
                    {
                        "source_type": observed.provenance.source_type.value,
                        "evidence_id": observed.provenance.evidence_id,
                        "observed_at": observed_at.isoformat(),
                    },
                )
            ],
            expected_episode=episode,
        )
        return updated

    def mark_outcome_missing(
        self,
        episode_id: str,
        user_id: str,
        *,
        reason: str,
    ) -> ProspectivePredictionEpisode:
        episode = self._get(episode_id, user_id)
        self._require_status(episode, EpisodeStatus.AWAITING_OUTCOME)
        missing_reason = self._required_text(reason, "reason")
        now = self._now()
        if now < episode.outcome_due_at:
            raise ValueError("outcome cannot be marked missing before outcome_due_at")
        updated = episode.model_copy(
            update={"status": EpisodeStatus.MISSING_OUTCOME, "missing_outcome_reason": missing_reason}
        )
        self.store.update_episode(
            updated,
            [self._event(updated, EpisodeEventType.OUTCOME_MISSING, now, {"reason": missing_reason})],
            expected_episode=episode,
        )
        return updated

    def exclude_episode(
        self,
        episode_id: str,
        user_id: str,
        *,
        reason: str,
    ) -> ProspectivePredictionEpisode:
        episode = self._get(episode_id, user_id)
        if episode.status in {EpisodeStatus.EXCLUDED, EpisodeStatus.MISSING_OUTCOME}:
            raise ValueError(f"cannot exclude an episode in {episode.status.value} status")
        exclusion_reason = self._required_text(reason, "reason")
        now = self._now()
        updated = episode.model_copy(
            update={"status": EpisodeStatus.EXCLUDED, "exclusion_reason": exclusion_reason}
        )
        self.store.update_episode(
            updated,
            [self._event(updated, EpisodeEventType.EPISODE_EXCLUDED, now, {"reason": exclusion_reason})],
            expected_episode=episode,
        )
        return updated

    def is_episode_evaluation_eligible(self, episode_id: str, user_id: str) -> EligibilityResult:
        episode = self._get(episode_id, user_id)
        reasons: list[str] = []
        outcome = episode.observed_outcome
        if episode.status != EpisodeStatus.OUTCOME_RECORDED:
            reasons.append(f"episode_status_{episode.status.value.lower()}")
        if episode.prediction_timestamp >= (outcome.provenance.observed_at if outcome else self._now()):
            reasons.append("prediction_not_frozen_before_observation")
        if episode.action_started_at is None or episode.action_completed_at is None:
            reasons.append("action_not_completed")
        elif episode.action_started_at <= episode.prediction_timestamp:
            reasons.append("action_started_before_prediction_freeze")
        if episode.performed_action != episode.action:
            reasons.append("performed_action_mismatch")
        if outcome is None:
            reasons.append("observed_outcome_missing")
        else:
            if outcome.target_name != episode.target.target_name or outcome.target_dimension != episode.target.target_dimension:
                reasons.append("target_mismatch")
            if outcome.target_unit != episode.target.target_unit:
                reasons.append("target_unit_mismatch")
            if outcome.target_scale != episode.target.target_scale:
                reasons.append("target_scale_mismatch")
            if outcome.provenance.observed_at < episode.outcome_due_at:
                reasons.append("outcome_before_valid_horizon")
            if outcome.provenance.quality <= 0:
                reasons.append("outcome_provenance_quality_unacceptable")
            if outcome.provenance.source_type not in {
                OutcomeSource.USER_REPORTED,
                OutcomeSource.SYSTEM_OBSERVED,
                OutcomeSource.ASSESSMENT,
                OutcomeSource.EXTERNAL_MEASUREMENT,
                OutcomeSource.VERIFIED_EVENT,
            }:
                reasons.append("outcome_source_unverifiable")
        if episode.exclusion_reason:
            reasons.append("episode_excluded")
        if episode.missing_outcome_reason:
            reasons.append("outcome_marked_missing")
        return EligibilityResult(eligible=not reasons, reasons=tuple(dict.fromkeys(reasons)))

    def get_episode(self, episode_id: str, user_id: str) -> ProspectivePredictionEpisode:
        return self._get(episode_id, user_id)

    def get_episode_for_enrollment(
        self,
        *,
        participant_id: str,
        pilot_id: str,
        enrollment_id: str,
    ) -> ProspectivePredictionEpisode:
        matches = [
            episode
            for episode in self.store.list_episodes(self._required_text(participant_id, "participant_id"))
            if episode.pilot_id == pilot_id and episode.enrollment_id == enrollment_id
        ]
        if len(matches) != 1:
            raise KeyError("prospective episode not found for this enrollment")
        return matches[0]

    def list_episodes(self, user_id: str) -> list[ProspectivePredictionEpisode]:
        return self.store.list_episodes(self._required_text(user_id, "user_id"))

    def list_events(self, episode_id: str, user_id: str) -> list[EpisodeAuditEvent]:
        self._get(episode_id, user_id)
        return self.store.list_events(episode_id, user_id)

    @staticmethod
    def _validate_target_predictions(predictions: PredictionBundle, target: PredictionTarget) -> None:
        for label, prediction in (
            ("base", predictions.base_prediction),
            ("MG", predictions.mg_prediction),
        ):
            future = prediction.get("predicted_future_state")
            if not isinstance(future, dict) or target.target_name not in future:
                raise ValueError(f"{label} prediction does not contain the frozen target skill")
            value = future[target.target_name]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{label} prediction target must be a finite number")
            lower, upper = target.valid_range
            if not lower <= value <= upper:
                raise ValueError(f"{label} prediction target is outside the declared valid range")

    def _get(self, episode_id: str, user_id: str) -> ProspectivePredictionEpisode:
        episode = self.store.get_episode(episode_id, self._required_text(user_id, "user_id"))
        if episode is None:
            raise KeyError("prospective episode not found for this user")
        return episode

    @staticmethod
    def _require_status(episode: ProspectivePredictionEpisode, expected: EpisodeStatus) -> None:
        if episode.status != expected:
            raise ValueError(f"episode must be in {expected.value} status, not {episode.status.value}")

    def _event(
        self,
        episode: ProspectivePredictionEpisode,
        event_type: EpisodeEventType,
        timestamp: datetime,
        metadata: dict[str, Any] | None = None,
    ) -> EpisodeAuditEvent:
        return EpisodeAuditEvent(
            episode_id=episode.episode_id,
            timestamp=timestamp,
            event_type=event_type,
            metadata=metadata or {},
        )

    def _now(self) -> datetime:
        return self._aware_utc(self.clock(), "clock")

    @staticmethod
    def _aware_utc(value: datetime, name: str) -> datetime:
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{name} must be a timezone-aware datetime")
        return value.astimezone(timezone.utc)

    @staticmethod
    def _required_text(value: str, name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
        return value.strip()

    @classmethod
    def _reject_outcome_context(cls, context: dict[str, Any], forbidden_keys: set[str]) -> None:
        def visit(value: Any) -> None:
            if isinstance(value, dict):
                for key, nested in value.items():
                    if isinstance(key, str) and key.strip().lower() in forbidden_keys:
                        raise ValueError(f"context must not contain outcome data field {key!r}")
                    visit(nested)
            elif isinstance(value, list):
                for nested in value:
                    visit(nested)

        visit(context)
