from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from backend.compatibility.mg_config import MGCompatibilityConfig
from backend.models.prospective_prediction_episode import (
    EpisodeStatus,
    ObservedOutcome,
    OutcomeProvenance,
    OutcomeSource,
    PredictionBundle,
    PredictionTarget,
)
from backend.services.prospective_episode_service import (
    ProspectiveEpisodeService,
    SimulationEnginePredictionProvider,
)
from backend.services.prospective_episode_store import ProspectiveEpisodeStore
from backend.services.simulation_engine import SimulationEngine
from backend.services.transition_engine import TransitionEngine


class MutableClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.value

    def advance(self, seconds: int) -> None:
        self.value += timedelta(seconds=seconds)


class TestPredictionProvider:
    def predict_pair(self, pre_action_state, action, context) -> PredictionBundle:
        assert action
        assert isinstance(context, dict)
        future = dict(pre_action_state)
        future["python"] = 52
        prediction = {"current_state": dict(pre_action_state), "predicted_future_state": future}
        mg_future = dict(future)
        mg_future["python"] = 54
        return PredictionBundle(
            base_prediction=prediction,
            mg_prediction={"current_state": dict(pre_action_state), "predicted_future_state": mg_future},
            base_model_version="test-base-v1",
            mg_model_version="test-mg-v1",
            mg_coefficients_version="frozen-test-coefficients-v1",
            mg_configuration_sha256="a" * 64,
        )


def test_simulation_adapter_captures_actual_base_and_mg_pair():
    engine = SimulationEngine(
        transition_engine=TransitionEngine(experiences=[]),
        mg_config=MGCompatibilityConfig(),
    )
    provider = SimulationEnginePredictionProvider(
        engine,
        base_model_version="transition-v1",
        mg_model_version="mg-layer-v1",
        mg_coefficients_version="coefficients-17.13B",
    )

    pair = provider.predict_pair({"python": 50}, "Complete Python Project", {})

    expected = engine.simulate_action({"python": 50}, "Complete Python Project")
    assert pair.base_prediction["predicted_future_state"] == expected["predicted_future_state"]
    assert pair.mg_prediction["predicted_future_state"] == expected["predicted_future_state"]
    assert len(pair.mg_configuration_sha256) == 64
    assert all(character in "0123456789abcdef" for character in pair.mg_configuration_sha256)


@pytest.fixture
def setup_service(tmp_path):
    clock = MutableClock()
    store = ProspectiveEpisodeStore(tmp_path / "prospective.sqlite3")
    service = ProspectiveEpisodeService(store, TestPredictionProvider(), clock)
    target = PredictionTarget(
        target_name="python",
        target_dimension="skill",
        target_unit="points",
        target_scale="0-100",
        measurement_method="standardized_assessment_v1",
        horizon_seconds=10,
        valid_range=(0, 100),
    )
    return service, store, clock, target


def create_episode(service, target, user_id="user-1"):
    return service.create_prospective_episode(
        user_id=user_id,
        pre_action_state={"python": 50},
        action="Complete Python Project",
        context={"category": "career_skill_development"},
        target=target,
    )


def complete_action(service, clock, episode):
    clock.advance(1)
    service.mark_action_started(episode.episode_id, episode.user_id)
    clock.advance(1)
    return service.mark_action_completed(
        episode.episode_id,
        episode.user_id,
        performed_action=episode.action,
    )


def make_outcome_due(service, clock, episode):
    completed = complete_action(service, clock, episode)
    clock.value = completed.outcome_due_at
    return service.mark_outcome_due(episode.episode_id, episode.user_id)


def observed_outcome(target, observed_at, *, value=53, source=OutcomeSource.ASSESSMENT):
    return ObservedOutcome(
        target_name=target.target_name,
        target_dimension=target.target_dimension,
        target_unit=target.target_unit,
        target_scale=target.target_scale,
        value=value,
        provenance=OutcomeProvenance(
            source_type=source,
            collection_method=target.measurement_method,
            recorded_by="assessor-7",
            evidence_id="assessment-2026-10-episode-1",
            observed_at=observed_at,
            quality=0.9,
            notes="Synthetic fixture for service behavior tests only.",
        ),
    )


def test_creation_freezes_paired_predictions_without_outcome(setup_service):
    service, store, _, target = setup_service
    episode = create_episode(service, target)

    assert episode.status == EpisodeStatus.PREDICTION_FROZEN
    assert episode.observed_outcome is None
    assert episode.predictions.base_prediction["predicted_future_state"]["python"] == 52
    assert episode.predictions.mg_prediction["predicted_future_state"]["python"] == 54
    assert episode.outcome_due_at == episode.prediction_timestamp + timedelta(seconds=10)
    assert [event.event_type.value for event in store.list_events(episode.episode_id, "user-1")] == [
        "EPISODE_CREATED",
        "PREDICTION_FROZEN",
    ]


def test_creation_rejects_unknown_or_non_career_target(setup_service):
    service, _, _, target = setup_service
    with pytest.raises(ValueError, match="existing career skill"):
        create_episode(
            service,
            target.model_copy(update={"target_name": "health"}),
        )
    with pytest.raises(ValueError):
        PredictionTarget(
            target_name="python",
            target_dimension="health",
            target_unit="points",
            target_scale="0-100",
            measurement_method="assessment",
            horizon_seconds=1,
        )
    with pytest.raises(ValueError, match="supported 0-100 scale"):
        PredictionTarget(
            target_name="python",
            target_dimension="skill",
            target_unit="points",
            target_scale="1-5",
            measurement_method="assessment",
            horizon_seconds=1,
        )
    with pytest.raises(ValueError, match="within \\[0, 100\\]"):
        PredictionTarget(
            target_name="python",
            target_dimension="skill",
            target_unit="points",
            target_scale="0-100",
            measurement_method="assessment",
            horizon_seconds=1,
            valid_range=(0, 101),
        )


def test_creation_does_not_accept_observed_outcome(setup_service):
    service, _, _, target = setup_service
    with pytest.raises(TypeError):
        service.create_prospective_episode(
            user_id="user-1",
            pre_action_state={"python": 50},
            action="Complete Python Project",
            context={},
            target=target,
            observed_outcome={"value": 55},
        )


def test_creation_rejects_outcome_fields_hidden_in_context(setup_service):
    service, _, _, target = setup_service
    with pytest.raises(ValueError, match="must not contain outcome data"):
        service.create_prospective_episode(
            user_id="user-1",
            pre_action_state={"python": 50},
            action="Complete Python Project",
            context={"telemetry": [{"actual_state": {"python": 55}}]},
            target=target,
        )


def test_action_linkage_and_valid_outcome_are_persisted(setup_service):
    service, store, clock, target = setup_service
    episode = create_episode(service, target)
    completed = complete_action(service, clock, episode)
    assert completed.status == EpisodeStatus.ACTION_COMPLETED
    with pytest.raises(ValueError, match="not due yet"):
        service.mark_outcome_due(episode.episode_id, episode.user_id)
    with pytest.raises(ValueError, match="must be in AWAITING_OUTCOME"):
        service.record_observed_outcome(
            episode.episode_id,
            episode.user_id,
            observed_outcome(target, completed.outcome_due_at),
        )
    clock.value = completed.outcome_due_at
    awaiting = service.mark_outcome_due(episode.episode_id, episode.user_id)
    assert awaiting.status == EpisodeStatus.AWAITING_OUTCOME
    assert awaiting.outcome_due_at == awaiting.action_completed_at + timedelta(seconds=10)
    result = service.record_observed_outcome(
        episode.episode_id,
        episode.user_id,
        observed_outcome(target, clock()),
    )
    assert result.status == EpisodeStatus.OUTCOME_RECORDED
    assert result.outcome_quality == 0.9
    assert result.observed_outcome.provenance.source_type == OutcomeSource.ASSESSMENT
    assert service.is_episode_evaluation_eligible(episode.episode_id, "user-1").eligible
    assert [event.event_type.value for event in store.list_events(episode.episode_id, "user-1")][-2:] == [
        "OUTCOME_DUE",
        "OUTCOME_RECORDED",
    ]


def test_action_cannot_start_at_same_instant_as_prediction_freeze(setup_service):
    service, _, _, target = setup_service
    episode = create_episode(service, target)
    with pytest.raises(ValueError, match="start after prediction freeze"):
        service.mark_action_started(episode.episode_id, episode.user_id)


def test_duplicate_lifecycle_transitions_are_rejected_without_duplicate_events(setup_service):
    service, store, clock, target = setup_service
    episode = create_episode(service, target)
    clock.advance(1)
    started = service.mark_action_started(episode.episode_id, episode.user_id)
    with pytest.raises(ValueError, match="must be in PREDICTION_FROZEN"):
        service.mark_action_started(episode.episode_id, episode.user_id)
    clock.advance(1)
    completed = service.mark_action_completed(
        episode.episode_id,
        episode.user_id,
        performed_action=episode.action,
    )
    with pytest.raises(ValueError, match="must be in ACTION_STARTED"):
        service.mark_action_completed(
            episode.episode_id,
            episode.user_id,
            performed_action=episode.action,
        )
    assert started.status == EpisodeStatus.ACTION_STARTED
    assert completed.status == EpisodeStatus.ACTION_COMPLETED
    assert [event.event_type.value for event in store.list_events(episode.episode_id, episode.user_id)] == [
        "EPISODE_CREATED",
        "PREDICTION_FROZEN",
        "ACTION_STARTED",
        "ACTION_COMPLETED",
    ]


@pytest.mark.parametrize(
    "source",
    ["prediction", "simulation", "digital_twin", "synthetic", "SYNTHETIC", "legacy_prediction"],
)
def test_forbidden_outcome_sources_are_rejected(setup_service, source):
    service, _, clock, target = setup_service
    episode = create_episode(service, target)
    awaiting = make_outcome_due(service, clock, episode)
    with pytest.raises(ValueError, match="provenance/schema"):
        service.record_observed_outcome(
            episode.episode_id,
            episode.user_id,
            {
                **observed_outcome(target, clock()).model_dump(mode="json"),
                "provenance": {
                    **observed_outcome(target, clock()).provenance.model_dump(mode="json"),
                    "source_type": source,
                },
            },
        )
    assert service.get_episode(episode.episode_id, episode.user_id).status == EpisodeStatus.AWAITING_OUTCOME
    assert awaiting.status == EpisodeStatus.AWAITING_OUTCOME


def test_prediction_payload_cannot_be_submitted_as_observed_outcome(setup_service):
    service, _, clock, target = setup_service
    episode = create_episode(service, target)
    make_outcome_due(service, clock, episode)
    prediction_payload = {
        "base_prediction": episode.predictions.base_prediction,
        "mg_prediction": episode.predictions.mg_prediction,
    }
    with pytest.raises(ValueError, match="provenance/schema"):
        service.record_observed_outcome(episode.episode_id, episode.user_id, prediction_payload)


def test_target_and_measurement_method_must_match(setup_service):
    service, _, clock, target = setup_service
    episode = create_episode(service, target)
    make_outcome_due(service, clock, episode)
    mismatched = observed_outcome(target, clock()).model_copy(update={"target_name": "leadership"})
    with pytest.raises(ValueError, match="target does not match"):
        service.record_observed_outcome(episode.episode_id, episode.user_id, mismatched)
    wrong_method = observed_outcome(target, clock()).model_copy(
        update={
            "provenance": observed_outcome(target, clock()).provenance.model_copy(
                update={"collection_method": "unregistered_method"}
            )
        }
    )
    with pytest.raises(ValueError, match="collection method"):
        service.record_observed_outcome(episode.episode_id, episode.user_id, wrong_method)
    wrong_scale = observed_outcome(target, clock()).model_copy(update={"target_scale": "1-5"})
    with pytest.raises(ValueError, match="scale does not match"):
        service.record_observed_outcome(episode.episode_id, episode.user_id, wrong_scale)


def test_outcome_equal_to_frozen_prediction_is_allowed_with_valid_provenance(setup_service):
    service, _, clock, target = setup_service
    episode = create_episode(service, target)
    make_outcome_due(service, clock, episode)
    base_prediction = episode.predictions.base_prediction["predicted_future_state"]["python"]

    result = service.record_observed_outcome(
        episode.episode_id,
        episode.user_id,
        observed_outcome(target, clock(), value=base_prediction),
    )

    assert result.observed_outcome.value == base_prediction
    assert service.is_episode_evaluation_eligible(episode.episode_id, episode.user_id).eligible


def test_out_of_range_outcome_and_duplicate_recording_are_rejected(setup_service):
    service, _, clock, target = setup_service
    episode = create_episode(service, target)
    make_outcome_due(service, clock, episode)
    out_of_range = observed_outcome(target, clock(), value=101)
    with pytest.raises(ValueError, match="target range"):
        service.record_observed_outcome(episode.episode_id, episode.user_id, out_of_range)
    valid = service.record_observed_outcome(
        episode.episode_id,
        episode.user_id,
        observed_outcome(target, clock()),
    )
    assert valid.status == EpisodeStatus.OUTCOME_RECORDED
    with pytest.raises(ValueError, match="must be in AWAITING_OUTCOME"):
        service.record_observed_outcome(
            episode.episode_id,
            episode.user_id,
            observed_outcome(target, clock()),
        )


def test_action_mismatch_is_excluded_and_never_eligible(setup_service):
    service, store, clock, target = setup_service
    episode = create_episode(service, target)
    clock.advance(1)
    service.mark_action_started(episode.episode_id, episode.user_id)
    clock.advance(1)
    completed = service.mark_action_completed(
        episode.episode_id,
        episode.user_id,
        performed_action="Different action actually performed",
    )
    assert completed.status == EpisodeStatus.EXCLUDED
    assert completed.exclusion_reason == "performed_action_did_not_match_frozen_action"
    assert not service.is_episode_evaluation_eligible(episode.episode_id, episode.user_id).eligible
    assert any(event.event_type.value == "EPISODE_EXCLUDED" for event in store.list_events(episode.episode_id, "user-1"))


def test_unperformed_action_can_be_excluded(setup_service):
    service, _, _, target = setup_service
    episode = create_episode(service, target)
    excluded = service.exclude_episode(episode.episode_id, episode.user_id, reason="participant declined")
    assert excluded.status == EpisodeStatus.EXCLUDED
    assert excluded.exclusion_reason == "participant declined"
    assert "action_not_completed" in service.is_episode_evaluation_eligible(
        episode.episode_id, episode.user_id
    ).reasons


def test_missing_outcome_requires_due_time_and_is_not_eligible(setup_service):
    service, _, clock, target = setup_service
    episode = create_episode(service, target)
    completed = complete_action(service, clock, episode)
    with pytest.raises(ValueError, match="not due yet"):
        service.mark_outcome_due(episode.episode_id, episode.user_id)
    clock.value = completed.outcome_due_at
    awaiting = service.mark_outcome_due(episode.episode_id, episode.user_id)
    missing = service.mark_outcome_missing(episode.episode_id, episode.user_id, reason="no response")
    assert missing.status == EpisodeStatus.MISSING_OUTCOME
    assert "observed_outcome_missing" in service.is_episode_evaluation_eligible(
        episode.episode_id, episode.user_id
    ).reasons
    assert awaiting.status == EpisodeStatus.AWAITING_OUTCOME


def test_database_prevents_frozen_payload_and_audit_event_mutations(setup_service):
    service, store, _, target = setup_service
    episode = create_episode(service, target)
    episode.predictions.base_prediction["predicted_future_state"]["python"] = 99
    with pytest.raises(ValueError, match="frozen"):
        store.update_episode(episode, [], expected_episode=episode)

    with sqlite3.connect(store.database_path) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("UPDATE prospective_episode_events SET metadata_json = '{}' WHERE event_id = 1")
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM prospective_episode_events WHERE event_id = 1")
        with pytest.raises(sqlite3.IntegrityError, match="frozen prediction payload"):
            connection.execute(
                "UPDATE prospective_episodes SET frozen_payload = '{}' WHERE episode_id = ?",
                (episode.episode_id,),
            )
        tampered_episode = episode.model_dump(mode="json")
        tampered_episode["predictions"]["base_prediction"]["predicted_future_state"]["python"] = 99
        with pytest.raises(sqlite3.IntegrityError, match="modified frozen fields"):
            connection.execute(
                "UPDATE prospective_episodes SET episode_json = ? WHERE episode_id = ?",
                (
                    json.dumps(tampered_episode, sort_keys=True, separators=(",", ":")),
                    episode.episode_id,
                ),
            )


def test_stale_lifecycle_write_cannot_append_audit_event(setup_service):
    service, store, clock, target = setup_service
    episode = create_episode(service, target)
    stale_snapshot = service.get_episode(episode.episode_id, episode.user_id)
    clock.advance(1)
    service.mark_action_started(episode.episode_id, episode.user_id)
    stale_update = stale_snapshot.model_copy(update={"status": EpisodeStatus.EXCLUDED})
    with pytest.raises(ValueError, match="changed concurrently"):
        store.update_episode(stale_update, [], expected_episode=stale_snapshot)
    assert len(service.list_events(episode.episode_id, episode.user_id)) == 3


def test_serialization_and_user_isolation(setup_service):
    service, _, _, target = setup_service
    first = create_episode(service, target, "user-1")
    second = create_episode(service, target, "user-2")
    assert service.get_episode(first.episode_id, "user-1") == first
    assert service.list_episodes("user-1") == [first]
    with pytest.raises(KeyError, match="not found"):
        service.get_episode(first.episode_id, "user-2")
    assert second.user_id == "user-2"


def test_future_and_naive_observation_timestamps_are_rejected(setup_service):
    service, _, clock, target = setup_service
    episode = create_episode(service, target)
    awaiting = make_outcome_due(service, clock, episode)
    due = awaiting.outcome_due_at
    with pytest.raises(ValueError, match="timezone"):
        OutcomeProvenance(
            source_type=OutcomeSource.ASSESSMENT,
            collection_method=target.measurement_method,
            recorded_by="assessor",
            evidence_id="evidence-1",
            observed_at=due.replace(tzinfo=None),
            quality=0.8,
        )
    with pytest.raises(ValueError, match="future"):
        service.record_observed_outcome(
            episode.episode_id,
            episode.user_id,
            observed_outcome(target, due + timedelta(seconds=20)),
        )
