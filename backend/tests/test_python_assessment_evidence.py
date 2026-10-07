from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.models.prospective_prediction_episode import (
    EpisodeStatus,
    PracticeActionEvidence,
    PredictionBundle,
    PredictionTarget,
)
from backend.models.python_assessment_evidence import AssessmentPhase, AssessmentSession
from backend.models.python_skill_assessment import AssessmentResult
from backend.services.prospective_episode_service import ProspectiveEpisodeService
from backend.services.prospective_episode_store import ProspectiveEpisodeStore
from backend.services.python_assessment_evidence_service import (
    AssessmentEvidenceService,
    evaluate_pilot_collection_readiness,
)
from backend.services.python_practice_module_service import PythonPracticeModuleService
from backend.services.python_skill_assessment_service import PythonSkillAssessmentService

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "research" / "17.16B" / "action" / "python_practice_core_v1.json"


class FixedClock:
    def __init__(self):
        self.value = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)

    def __call__(self):
        return self.value


class PredictionProvider:
    def predict_pair(self, pre_action_state, action, context):
        state = dict(pre_action_state)
        return PredictionBundle(
            base_prediction={"predicted_future_state": state},
            mg_prediction={"predicted_future_state": state},
            base_model_version="test-base",
            mg_model_version="test-mg",
            mg_coefficients_version="test-coefficients",
            mg_configuration_sha256="a" * 64,
        )


@pytest.fixture
def evidence_setup(tmp_path):
    clock = FixedClock()
    episode_service = ProspectiveEpisodeService(
        ProspectiveEpisodeStore(tmp_path / "episodes.sqlite3"),
        PredictionProvider(),
        clock,
    )
    evidence_service = AssessmentEvidenceService(
        episode_service,
        tmp_path / "assessment-evidence.sqlite3",
        clock=clock,
    )
    enrollment = evidence_service.create_enrollment(participant_id="participant-1")
    return evidence_service, enrollment, clock


def _target() -> PredictionTarget:
    return PredictionTarget(
        target_name="python",
        target_dimension="skill",
        target_unit="points",
        target_scale="0-100",
        measurement_method="standardized_assessment_v1",
        horizon_seconds=7 * 24 * 60 * 60,
    )


def _use_deterministic_test_score(monkeypatch):
    def score_form(form, responses, *, execution_mode):
        assert execution_mode == "SECURE_CONTAINER"
        raw_score = sum(item.maximum_points for item in form.items)
        return AssessmentResult(
            assessment_id=f"test-{form.form_id}",
            participant_id="unknown-participant",
            episode_id="unknown-episode",
            pilot_id="17_16B_python_skill_pilot_v1",
            form_id=form.form_id,
            form_version=form.form_version,
            raw_score=raw_score,
            aura_python_skill=float(raw_score),
            completed=True,
            instrument_hash=form.assessment_hash,
        )

    monkeypatch.setattr(PythonSkillAssessmentService, "score_form", score_form)


def _create_baseline(evidence, enrollment, clock, monkeypatch, *, submitted_at=None):
    _use_deterministic_test_score(monkeypatch)
    started_at = enrollment.enrolled_at + timedelta(minutes=1)
    submitted = submitted_at or started_at + timedelta(minutes=1)
    clock.value = max(clock.value, submitted)
    return evidence.create_session(
        enrollment_id=enrollment.enrollment_id,
        participant_id=enrollment.participant_id,
        phase=AssessmentPhase.BASELINE,
        form_id=enrollment.baseline_form_id,
        started_at=started_at,
        submitted_at=submitted,
        responses={"test": "valid deterministic test response"},
        recorded_by="test-assessor",
    )


def _create_episode(evidence, enrollment, baseline, clock):
    # Advance clock to ensure baseline submitted_at < freeze_candidate
    clock.value = baseline.submitted_at + timedelta(seconds=1)
    return evidence.create_prospective_episode_from_baseline(
        enrollment_id=enrollment.enrollment_id,
        baseline_assessment_session_id=baseline.assessment_session_id,
        pre_action_state={"python": int(baseline.aura_python_skill)},
        action="complete-python-practice",
        context={},
        target=_target(),
    )


def _complete_action(evidence, episode, clock):
    clock.value = episode.prediction_timestamp + timedelta(seconds=1)
    started = evidence.episode_service.mark_action_started(episode.episode_id, episode.user_id)
    clock.value += timedelta(minutes=5)
    completed = evidence.episode_service.mark_action_completed(
        episode.episode_id,
        episode.user_id,
        performed_action=episode.action,
    )
    module = PythonPracticeModuleService.load_module(MODULE_PATH)
    action_evidence = PracticeActionEvidence(
        participant_id=episode.user_id,
        module_id=module.module_id,
        module_version=module.module_version,
        module_hash=module.module_hash,
        completion_status="complete",
        evidence_id=f"test-action-{episode.episode_id}",
        started_at=started.action_started_at,
        completed_at=completed.action_completed_at - timedelta(microseconds=1),
    )
    episode = evidence.episode_service.record_action_completion_evidence(
        episode.episode_id,
        episode.user_id,
        action_evidence,
    )
    return episode, action_evidence


def test_enrollment_and_baseline_precede_prediction_freeze(evidence_setup, monkeypatch):
    evidence, enrollment, clock = evidence_setup
    assert enrollment.status.value == "ENROLLED"

    baseline = _create_baseline(evidence, enrollment, clock, monkeypatch)
    episode = _create_episode(evidence, enrollment, baseline, clock)
    linked_baseline = evidence.get_session(baseline.assessment_session_id)

    assert linked_baseline == baseline
    assert linked_baseline.episode_id is None
    assert episode.enrollment_id == enrollment.enrollment_id
    assert episode.baseline_assessment_session_id == baseline.assessment_session_id
    assert enrollment.enrolled_at < baseline.started_at < baseline.submitted_at < episode.prediction_timestamp
    assert any(
        event.event_type.value == "BASELINE_LINKED"
        for event in evidence.episode_service.list_events(episode.episode_id, episode.user_id)
    )
    with evidence._connection() as connection:
        row = connection.execute(
            """SELECT baseline_assessment_session_id, episode_id
               FROM assessment_episode_links WHERE enrollment_id = ?""",
            (enrollment.enrollment_id,),
        ).fetchone()
    assert row == (baseline.assessment_session_id, episode.episode_id)


def test_prediction_freeze_without_valid_finalized_baseline_fails(evidence_setup):
    evidence, enrollment, _ = evidence_setup
    with pytest.raises(KeyError, match="assessment session"):
        evidence.create_prospective_episode_from_baseline(
            enrollment_id=enrollment.enrollment_id,
            baseline_assessment_session_id="missing-baseline",
            pre_action_state={"python": 50},
            action="complete-python-practice",
            context={},
            target=_target(),
        )


def test_baseline_session_is_not_available_before_enrollment(evidence_setup):
    evidence, enrollment, clock = evidence_setup
    started = clock.value + timedelta(minutes=1)
    submitted = started + timedelta(minutes=1)
    clock.value = submitted
    with pytest.raises(ValueError, match="does not belong to the participant"):
        evidence.create_session(
            enrollment_id=enrollment.enrollment_id,
            participant_id="other-participant",
            phase=AssessmentPhase.BASELINE,
            form_id=enrollment.baseline_form_id,
            started_at=started,
            submitted_at=submitted,
            responses={},
            recorded_by="test-assessor",
        )


def test_baseline_wrong_assigned_form_is_rejected(evidence_setup):
    evidence, enrollment, clock = evidence_setup
    started = clock.value + timedelta(minutes=1)
    submitted = started + timedelta(minutes=1)
    clock.value = submitted
    with pytest.raises(ValueError, match="does not match assigned form"):
        evidence.create_session(
            enrollment_id=enrollment.enrollment_id,
            participant_id=enrollment.participant_id,
            phase=AssessmentPhase.BASELINE,
            form_id=enrollment.followup_form_id,
            started_at=started,
            submitted_at=submitted,
            responses={},
            recorded_by="test-assessor",
        )


def test_baseline_must_precede_proposed_freeze_strictly(evidence_setup, monkeypatch):
    _use_deterministic_test_score(monkeypatch)
    evidence, enrollment, clock = evidence_setup
    started_at = enrollment.enrolled_at + timedelta(minutes=1)
    submitted_at = started_at + timedelta(minutes=1)
    clock.value = submitted_at
    baseline = evidence.create_session(
        enrollment_id=enrollment.enrollment_id,
        participant_id=enrollment.participant_id,
        phase=AssessmentPhase.BASELINE,
        form_id=enrollment.baseline_form_id,
        started_at=started_at,
        submitted_at=submitted_at,
        responses={"test": "valid deterministic test response"},
        recorded_by="test-assessor",
    )

    with pytest.raises(ValueError, match="precede proposed prediction freeze"):
        evidence.create_prospective_episode_from_baseline(
            enrollment_id=enrollment.enrollment_id,
            baseline_assessment_session_id=baseline.assessment_session_id,
            pre_action_state={"python": int(baseline.aura_python_skill)},
            action="complete-python-practice",
            context={},
            target=_target(),
        )


def test_pilot_episode_api_requires_baseline_binding(evidence_setup):
    evidence, enrollment, _ = evidence_setup
    with pytest.raises(ValueError, match="requires a finalized baseline"):
        evidence.episode_service.create_prospective_episode(
            user_id=enrollment.participant_id,
            pre_action_state={"python": 50},
            action="complete-python-practice",
            context={},
            target=_target(),
            pilot_id=enrollment.pilot_id,
        )


def test_action_cannot_start_before_prediction_freeze(evidence_setup, monkeypatch):
    evidence, enrollment, clock = evidence_setup
    baseline = _create_baseline(evidence, enrollment, clock, monkeypatch)
    episode = _create_episode(evidence, enrollment, baseline, clock)

    with pytest.raises(ValueError, match="start after prediction freeze"):
        evidence.episode_service.mark_action_started(episode.episode_id, episode.user_id)


def test_followup_requires_completed_action_and_same_participant(evidence_setup, monkeypatch):
    _use_deterministic_test_score(monkeypatch)
    evidence, enrollment, clock = evidence_setup
    baseline = _create_baseline(evidence, enrollment, clock, monkeypatch)
    episode = _create_episode(evidence, enrollment, baseline, clock)
    followup_at = episode.prediction_timestamp + timedelta(days=7)

    followup_submitted = followup_at + timedelta(minutes=1)
    clock.value = followup_submitted

    with pytest.raises(ValueError, match="enrollment does not belong to the participant"):
        evidence.create_session(
            enrollment_id=enrollment.enrollment_id,
            participant_id="other-participant",
            phase=AssessmentPhase.FOLLOWUP,
            form_id=enrollment.followup_form_id,
            started_at=followup_at,
            submitted_at=followup_submitted,
            responses={"test": "valid"},
            recorded_by="test-assessor",
        )
    with pytest.raises(ValueError, match="persisted practice-module completion evidence"):
        evidence.create_session(
            enrollment_id=enrollment.enrollment_id,
            participant_id=enrollment.participant_id,
            phase=AssessmentPhase.FOLLOWUP,
            form_id=enrollment.followup_form_id,
            started_at=followup_at,
            submitted_at=followup_submitted,
            responses={"test": "valid"},
            recorded_by="test-assessor",
        )


def test_followup_must_be_within_t_plus_7_to_t_plus_10(evidence_setup, monkeypatch):
    evidence, enrollment, clock = evidence_setup
    baseline = _create_baseline(evidence, enrollment, clock, monkeypatch)
    episode = _create_episode(evidence, enrollment, baseline, clock)
    episode, action_evidence = _complete_action(evidence, episode, clock)
    _use_deterministic_test_score(monkeypatch)
    completion = episode.action_completed_at
    assert completion is not None

    for started_at, submitted_at in (
        (completion + timedelta(days=7) - timedelta(seconds=1), completion + timedelta(days=7)),
        (completion + timedelta(days=10, seconds=1), completion + timedelta(days=10, seconds=2)),
    ):
        clock.value = submitted_at
        with pytest.raises(ValueError, match="T\\+7 through T\\+10"):
            evidence.create_session(
                enrollment_id=enrollment.enrollment_id,
                participant_id=enrollment.participant_id,
                phase=AssessmentPhase.FOLLOWUP,
                form_id=enrollment.followup_form_id,
                started_at=started_at,
                submitted_at=submitted_at,
                responses={"test": "valid"},
                recorded_by="test-assessor",
                action_evidence=action_evidence,
            )


def test_valid_lifecycle_records_only_followup_as_observed_outcome(evidence_setup, monkeypatch):
    evidence, enrollment, clock = evidence_setup
    baseline = _create_baseline(evidence, enrollment, clock, monkeypatch)
    episode = _create_episode(evidence, enrollment, baseline, clock)
    episode, action_evidence = _complete_action(evidence, episode, clock)
    completed_at = episode.action_completed_at
    assert completed_at is not None

    followup_started = completed_at + timedelta(days=7)
    followup_submitted = followup_started + timedelta(minutes=2)
    clock.value = followup_submitted
    followup = evidence.create_session(
        enrollment_id=enrollment.enrollment_id,
        participant_id=enrollment.participant_id,
        phase=AssessmentPhase.FOLLOWUP,
        form_id=enrollment.followup_form_id,
        started_at=followup_started,
        submitted_at=followup_submitted,
        responses={"test": "valid"},
        recorded_by="test-assessor",
        action_evidence=action_evidence,
    )
    recorded = evidence.finalize_followup_as_outcome(
        followup.assessment_session_id,
        action_evidence=action_evidence,
    )
    assert recorded.status is EpisodeStatus.OUTCOME_RECORDED
    assert recorded.observed_outcome is not None
    assert recorded.observed_outcome.provenance.source_type.value == "ASSESSMENT"
    assert recorded.observed_outcome.value == followup.aura_python_skill
    assert recorded.observed_outcome.value != baseline.raw_score or baseline.raw_score == followup.raw_score
    assert (
        enrollment.enrolled_at
        < baseline.started_at
        < baseline.submitted_at
        < episode.prediction_timestamp
        < episode.action_started_at
        <= episode.action_completed_at
        < followup.submitted_at
    )
    assert followup.submitted_at >= completed_at + timedelta(days=7)
    assert followup.submitted_at <= completed_at + timedelta(days=10)


def test_assessment_sessions_and_episode_links_are_append_only(evidence_setup):
    evidence, enrollment, _ = evidence_setup
    with evidence._connection() as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE pilot_enrollments SET participant_id = 'changed' WHERE enrollment_id = ?",
                (enrollment.enrollment_id,),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "DELETE FROM pilot_enrollments WHERE enrollment_id = ?",
                (enrollment.enrollment_id,),
            )


def test_assessment_session_model_enforces_score_identity_and_baseline_unlinked():
    timestamp = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="aura_python_skill"):
        AssessmentSession(
            assessment_session_id="session-1",
            pilot_id="pilot",
            enrollment_id="enrollment-1",
            episode_id=None,
            participant_id="participant",
            assignment_group="AB",
            phase=AssessmentPhase.BASELINE,
            form_id="python_skill_form_a_v1",
            form_version="v1",
            form_hash="a" * 64,
            started_at=timestamp - timedelta(minutes=1),
            submitted_at=timestamp,
            evidence_id="pilot:participant:enrollment-1:session-1",
            responses={},
            raw_score=5,
            aura_python_skill=6,
            scoring_version="v1",
            instrument_hash="a" * 64,
            protocol_version="protocol-v1",
            protocol_hash="c" * 64,
            provenance={
                "source_type": "ASSESSMENT",
                "collection_method": "assessment",
                "recorded_by": "assessor",
                "assessment_session_id": "session-1",
                "instrument_version": "v1",
                "observed_at": timestamp,
            },
        )


def test_collection_readiness_stays_blocked_without_secure_backend_or_owner_approval(monkeypatch):
    monkeypatch.delenv("AURA_SECURE_EXECUTION_IMAGE", raising=False)
    result = evaluate_pilot_collection_readiness(evidence_service=None)
    assert result.ready is False
    assert result.protocol_hash_valid is True
    assert result.artifact_bindings_valid is True
    assert result.measurement_artifacts_valid is True
    assert result.action_module_valid is True
    assert result.owner_approval is False
    assert result.evidence_validation_service_available is False
    assert result.secure_execution_backend_available is False
    assert result.security_execution_gate == "BLOCKED_ENVIRONMENT_DEPENDENCY"
