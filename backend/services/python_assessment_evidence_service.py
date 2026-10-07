from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Generator
from uuid import uuid4

from pydantic import ValidationError

from backend.models.prospective_prediction_episode import (
    EpisodeEventType,
    EpisodeStatus,
    ObservedOutcome,
    OutcomeProvenance,
    OutcomeSource,
    PracticeActionEvidence,
)
from backend.models.python_assessment_evidence import (
    AssessmentPhase,
    AssessmentProvenance,
    AssessmentSession,
    EnrollmentStatus,
    PilotReadinessResult,
    ProspectivePilotEnrollment,
)
from backend.models.python_skill_assessment import AssessmentAssignment
from backend.services.prospective_episode_service import ProspectiveEpisodeService
from backend.services.python_code_executor import (
    DockerContainerExecutor,
    SecureExecutionUnavailable,
    get_secure_execution_backend,
)
from backend.services.python_practice_module_service import PythonPracticeModuleService
from backend.services.python_skill_assessment_service import PythonSkillAssessmentService

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT / "17_16B_PILOT_PROTOCOL_CONFIG.json"
FORM_FILES = {
    "python_skill_form_a_v1": ROOT / "research" / "17.16B" / "instruments" / "python_skill_form_a_v1.json",
    "python_skill_form_b_v1": ROOT / "research" / "17.16B" / "instruments" / "python_skill_form_b_v1.json",
}
MODULE_FILE = ROOT / "research" / "17.16B" / "action" / "python_practice_core_v1.json"
SCORING_VERSION = "python_skill_scoring_v1"


class AssessmentEvidenceService:
    """Validates and stores append-only assessment evidence linked to prospective episodes."""

    def __init__(
        self,
        episode_service: ProspectiveEpisodeService,
        evidence_database_path: str | Path,
        *,
        config_path: str | Path = DEFAULT_CONFIG_PATH,
        clock=lambda: datetime.now(timezone.utc),
    ) -> None:
        self.episode_service = episode_service
        self.evidence_database_path = Path(evidence_database_path)
        self.config_path = Path(config_path)
        self.clock = clock
        self._lock = threading.RLock()
        self.evidence_database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS pilot_enrollments (
                    enrollment_id TEXT PRIMARY KEY,
                    pilot_id TEXT NOT NULL,
                    participant_id TEXT NOT NULL,
                    enrollment_json TEXT NOT NULL,
                    UNIQUE (pilot_id, participant_id, enrollment_id)
                );
                CREATE TABLE IF NOT EXISTS assessment_sessions (
                    assessment_session_id TEXT PRIMARY KEY,
                    evidence_id TEXT NOT NULL UNIQUE,
                    enrollment_id TEXT NOT NULL REFERENCES pilot_enrollments(enrollment_id),
                    episode_id TEXT,
                    phase TEXT NOT NULL CHECK (phase IN ('BASELINE', 'FOLLOWUP')),
                    session_json TEXT NOT NULL,
                    CHECK (
                        (phase = 'BASELINE' AND episode_id IS NULL)
                        OR (phase = 'FOLLOWUP' AND episode_id IS NOT NULL)
                    ),
                    UNIQUE (enrollment_id, phase),
                    UNIQUE (episode_id, phase)
                );
                CREATE TABLE IF NOT EXISTS assessment_episode_links (
                    enrollment_id TEXT PRIMARY KEY REFERENCES pilot_enrollments(enrollment_id),
                    baseline_assessment_session_id TEXT NOT NULL UNIQUE
                        REFERENCES assessment_sessions(assessment_session_id),
                    episode_id TEXT NOT NULL UNIQUE,
                    linked_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS finalized_assessment_outcomes (
                    episode_id TEXT PRIMARY KEY,
                    assessment_session_id TEXT NOT NULL UNIQUE
                        REFERENCES assessment_sessions(assessment_session_id)
                );
                CREATE TRIGGER IF NOT EXISTS prevent_assessment_session_update
                BEFORE UPDATE ON assessment_sessions
                BEGIN
                    SELECT RAISE(ABORT, 'finalized assessment sessions are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS prevent_assessment_session_delete
                BEFORE DELETE ON assessment_sessions
                BEGIN
                    SELECT RAISE(ABORT, 'finalized assessment sessions are append-only');
                END;
                CREATE TRIGGER IF NOT EXISTS prevent_finalized_outcome_update
                BEFORE UPDATE ON finalized_assessment_outcomes
                BEGIN
                    SELECT RAISE(ABORT, 'finalized assessment outcomes are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS prevent_finalized_outcome_delete
                BEFORE DELETE ON finalized_assessment_outcomes
                BEGIN
                    SELECT RAISE(ABORT, 'finalized assessment outcomes are append-only');
                END;
                CREATE TRIGGER IF NOT EXISTS prevent_pilot_enrollment_update
                BEFORE UPDATE ON pilot_enrollments
                BEGIN
                    SELECT RAISE(ABORT, 'pilot enrollments are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS prevent_pilot_enrollment_delete
                BEFORE DELETE ON pilot_enrollments
                BEGIN
                    SELECT RAISE(ABORT, 'pilot enrollments are append-only');
                END;
                CREATE TRIGGER IF NOT EXISTS prevent_assessment_episode_link_update
                BEFORE UPDATE ON assessment_episode_links
                BEGIN
                    SELECT RAISE(ABORT, 'assessment episode links are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS prevent_assessment_episode_link_delete
                BEFORE DELETE ON assessment_episode_links
                BEGIN
                    SELECT RAISE(ABORT, 'assessment episode links are append-only');
                END;
                """
            )

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        connection = sqlite3.connect(self.evidence_database_path, timeout=10)
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def health_check(self) -> bool:
        try:
            with self._connection() as connection:
                session_tables = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN (?, ?, ?, ?)",
                    (
                        "pilot_enrollments",
                        "assessment_sessions",
                        "assessment_episode_links",
                        "finalized_assessment_outcomes",
                    ),
                ).fetchall()
                triggers = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'trigger' AND name IN (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        "prevent_assessment_session_update",
                        "prevent_assessment_session_delete",
                        "prevent_finalized_outcome_update",
                        "prevent_finalized_outcome_delete",
                        "prevent_pilot_enrollment_update",
                        "prevent_pilot_enrollment_delete",
                        "prevent_assessment_episode_link_update",
                        "prevent_assessment_episode_link_delete",
                    ),
                ).fetchall()
            return len(session_tables) == 4 and len(triggers) == 8
        except sqlite3.Error:
            return False

    def assign_participant(self, participant_id: str) -> AssessmentAssignment:
        return PythonSkillAssessmentService.assign_forms(participant_id)

    @staticmethod
    def _session_identifier(pilot_id: str, enrollment_id: str, phase: AssessmentPhase) -> str:
        value = f"python-assessment-session-v1:{pilot_id}:{enrollment_id}:{phase.value}"
        return f"assessment_{hashlib.sha256(value.encode('utf-8')).hexdigest()}"

    def create_enrollment(
        self,
        *,
        participant_id: str,
        target_name: str = "python",
        target_unit: str = "points",
    ) -> ProspectivePilotEnrollment:
        participant_id = self._required_text(participant_id, "participant_id")
        target_name = self._required_text(target_name, "target_name")
        target_unit = self._required_text(target_unit, "target_unit")
        config = self._read_config()
        assignment = self.assign_participant(participant_id)
        enrolled_at = self.clock()
        self._require_aware(enrolled_at, "enrolled_at")
        enrollment = ProspectivePilotEnrollment(
            enrollment_id=f"enrollment_{uuid4().hex}",
            pilot_id=config["pilot_id"],
            participant_id=participant_id,
            target_name=target_name,
            target_unit=target_unit,
            assignment_group=assignment.assignment_group,
            baseline_form_id=assignment.baseline_form,
            followup_form_id=assignment.followup_form,
            enrolled_at=enrolled_at,
            protocol_version=config["protocol_version"],
            protocol_hash=config["protocol_hash"],
            status=EnrollmentStatus.ENROLLED,
        )
        with self._lock, self._connection() as connection:
            connection.execute(
                """INSERT INTO pilot_enrollments
                   (enrollment_id, pilot_id, participant_id, enrollment_json)
                   VALUES (?, ?, ?, ?)""",
                (
                    enrollment.enrollment_id,
                    enrollment.pilot_id,
                    enrollment.participant_id,
                    enrollment.model_dump_json(),
                ),
            )
        return enrollment

    def get_enrollment(self, enrollment_id: str) -> ProspectivePilotEnrollment:
        with self._lock, self._connection() as connection:
            row = connection.execute(
                "SELECT enrollment_json FROM pilot_enrollments WHERE enrollment_id = ?",
                (enrollment_id,),
            ).fetchone()
        if row is None:
            raise KeyError("pilot enrollment not found")
        return ProspectivePilotEnrollment.model_validate_json(row[0])

    def create_session(
        self,
        *,
        enrollment_id: str,
        participant_id: str,
        phase: AssessmentPhase,
        form_id: str,
        started_at: datetime,
        submitted_at: datetime,
        responses: dict[str, Any],
        recorded_by: str,
        action_evidence: PracticeActionEvidence | dict[str, Any] | None = None,
        notes: str | None = None,
    ) -> AssessmentSession:
        if not isinstance(phase, AssessmentPhase):
            raise ValueError("phase must be BASELINE or FOLLOWUP")
        self._require_aware(started_at, "started_at")
        self._require_aware(submitted_at, "submitted_at")
        if started_at >= submitted_at:
            raise ValueError("started_at must be earlier than submitted_at")
        if submitted_at > self.clock():
            raise ValueError("submitted_at cannot be in the future")
        participant_id = self._required_text(participant_id, "participant_id")
        recorded_by = self._required_text(recorded_by, "recorded_by")

        config = self._read_config()
        assignment = self.assign_participant(participant_id)
        enrollment = self.get_enrollment(enrollment_id)
        if enrollment.participant_id != participant_id:
            raise ValueError("enrollment does not belong to the participant")
        if enrollment.pilot_id != config["pilot_id"]:
            raise ValueError("enrollment does not belong to the configured pilot")
        if enrollment.protocol_version != config["protocol_version"] or enrollment.protocol_hash != config["protocol_hash"]:
            raise ValueError("enrollment protocol binding does not match the active protocol")
        if (
            enrollment.assignment_group != assignment.assignment_group
            or enrollment.baseline_form_id != assignment.baseline_form
            or enrollment.followup_form_id != assignment.followup_form
        ):
            raise ValueError("enrollment assignment does not match deterministic participant assignment")
        if started_at <= enrollment.enrolled_at:
            raise ValueError("assessment must start after enrollment")
        PythonSkillAssessmentService.validate_assigned_form(assignment, phase.value.lower(), form_id)
        if not isinstance(responses, dict):
            raise TypeError("responses must be a mapping")

        form = self._load_bound_form(form_id, config)
        binding_name = "form_a" if form_id.endswith("_a_v1") else "form_b"
        if form.form_version != config["artifact_bindings"][binding_name][f"{binding_name}_version"]:
            raise ValueError("form version does not match protocol binding")

        episode = None
        if phase is AssessmentPhase.BASELINE:
            if action_evidence is not None:
                raise ValueError("baseline assessment cannot include action evidence")
        else:
            episode = self.episode_service.get_episode_for_enrollment(
                participant_id=participant_id,
                pilot_id=config["pilot_id"],
                enrollment_id=enrollment_id,
            )
            self._validate_followup(
                episode,
                enrollment_id,
                started_at,
                submitted_at,
                action_evidence,
                config,
            )

        result = PythonSkillAssessmentService.score_form(
            form,
            responses,
            execution_mode="SECURE_CONTAINER",
        )
        if not result.completed or result.invalid_items:
            raise ValueError("assessment is incomplete or contains invalid required responses")
        if result.raw_score != result.aura_python_skill:
            raise ValueError("score transformation verification failed")

        session_id = self._session_identifier(config["pilot_id"], enrollment_id, phase)
        identity = enrollment_id if phase is AssessmentPhase.BASELINE else episode.episode_id
        evidence_id = f"{config['pilot_id']}:{participant_id}:{identity}:{session_id}"
        measurement_method = "PYTHON_SKILL_FORM" if phase is AssessmentPhase.BASELINE else episode.target.measurement_method
        provenance = AssessmentProvenance(
            source_type="ASSESSMENT",
            collection_method=measurement_method,
            recorded_by=recorded_by,
            assessment_session_id=session_id,
            instrument_version=form.form_version,
            observed_at=submitted_at,
            notes=notes,
        )
        try:
            session = AssessmentSession(
                assessment_session_id=session_id,
                pilot_id=config["pilot_id"],
                enrollment_id=enrollment_id,
                episode_id=None if episode is None else episode.episode_id,
                participant_id=participant_id,
                assignment_group=assignment.assignment_group,
                phase=phase,
                form_id=form.form_id,
                form_version=form.form_version,
                form_hash=form.assessment_hash,
                started_at=started_at,
                submitted_at=submitted_at,
                evidence_id=evidence_id,
                responses=json.loads(json.dumps(responses)),
                raw_score=result.raw_score,
                aura_python_skill=result.aura_python_skill,
                scoring_version=SCORING_VERSION,
                instrument_hash=form.assessment_hash,
                protocol_version=config["protocol_version"],
                protocol_hash=config["protocol_hash"],
                provenance=provenance,
            )
        except ValidationError as error:
            raise ValueError(f"assessment evidence failed validation: {error}") from error

        with self._lock, self._connection() as connection:
            if phase is AssessmentPhase.FOLLOWUP and not connection.execute(
                """SELECT 1 FROM assessment_episode_links
                   WHERE enrollment_id = ? AND episode_id = ?""",
                (enrollment_id, episode.episode_id),
            ).fetchone():
                raise ValueError("follow-up requires an episode linked to this enrollment")
            try:
                connection.execute(
                    """INSERT INTO assessment_sessions
                       (assessment_session_id, evidence_id, enrollment_id, episode_id, phase, session_json)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        session_id,
                        evidence_id,
                        enrollment_id,
                        None if episode is None else episode.episode_id,
                        phase.value,
                        session.model_dump_json(),
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise ValueError("duplicate evidence ID or assessment phase for episode") from error
        return AssessmentSession.model_validate_json(session.model_dump_json())

    def create_prospective_episode_from_baseline(
        self,
        *,
        enrollment_id: str,
        baseline_assessment_session_id: str,
        pre_action_state: dict[str, int],
        action: str,
        context: dict[str, Any],
        target: Any,
    ) -> Any:
        enrollment = self.get_enrollment(enrollment_id)
        baseline = self.get_session(baseline_assessment_session_id)
        if baseline.phase is not AssessmentPhase.BASELINE or baseline.validation_status != "VALID_FINALIZED":
            raise ValueError("prediction freeze requires a finalized valid baseline assessment")
        if baseline.enrollment_id != enrollment_id or baseline.participant_id != enrollment.participant_id:
            raise ValueError("baseline assessment does not match enrollment participant")
        if baseline.pilot_id != enrollment.pilot_id:
            raise ValueError("baseline assessment does not match enrollment pilot")
        if (
            baseline.protocol_version != enrollment.protocol_version
            or baseline.protocol_hash != enrollment.protocol_hash
        ):
            raise ValueError("baseline protocol binding does not match enrollment")
        if baseline.form_id != enrollment.baseline_form_id:
            raise ValueError("baseline form does not match enrollment assignment")
        config = self._read_config()
        if (
            enrollment.protocol_version != config["protocol_version"]
            or enrollment.protocol_hash != config["protocol_hash"]
        ):
            raise ValueError("enrollment protocol binding does not match active protocol")
        if target.target_name != enrollment.target_name or target.target_unit != enrollment.target_unit:
            raise ValueError("prediction target does not match enrollment target")
        freeze_candidate = self.clock()
        self._require_aware(freeze_candidate, "prediction_frozen_at")
        if baseline.submitted_at >= freeze_candidate:
            raise ValueError("baseline assessment must precede proposed prediction freeze")
        with self._lock, self._connection() as connection:
            if connection.execute(
                "SELECT 1 FROM assessment_episode_links WHERE enrollment_id = ?",
                (enrollment_id,),
            ).fetchone():
                raise ValueError("enrollment already has a frozen prediction episode")
        episode = self.episode_service.create_prospective_episode(
            user_id=enrollment.participant_id,
            pre_action_state=pre_action_state,
            action=action,
            context=context,
            target=target,
            pilot_id=enrollment.pilot_id,
            enrollment_id=enrollment.enrollment_id,
            baseline_assessment_session_id=baseline.assessment_session_id,
            baseline_submitted_at=baseline.submitted_at,
        )
        linked_at = self.clock()
        self._require_aware(linked_at, "linked_at")
        with self._lock, self._connection() as connection:
            try:
                connection.execute(
                    """INSERT INTO assessment_episode_links
                       (enrollment_id, baseline_assessment_session_id, episode_id, linked_at)
                       VALUES (?, ?, ?, ?)""",
                    (
                        enrollment_id,
                        baseline.assessment_session_id,
                        episode.episode_id,
                        linked_at.isoformat(),
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise ValueError("baseline or enrollment is already linked to a prediction episode") from error
        self.episode_service.store.append_event(
            self.episode_service._event(
                episode,
                EpisodeEventType.BASELINE_LINKED,
                linked_at,
                {
                    "enrollment_id": enrollment_id,
                    "baseline_assessment_session_id": baseline.assessment_session_id,
                },
            )
        )
        return episode

    def get_session(self, assessment_session_id: str) -> AssessmentSession:
        with self._lock, self._connection() as connection:
            row = connection.execute(
                "SELECT session_json FROM assessment_sessions WHERE assessment_session_id = ?",
                (assessment_session_id,),
            ).fetchone()
        if row is None:
            raise KeyError("assessment session not found")
        serialized = row[0]
        return AssessmentSession.model_validate_json(serialized)

    def finalize_followup_as_outcome(
        self,
        assessment_session_id: str,
        *,
        action_evidence: PracticeActionEvidence | dict[str, Any],
    ) -> Any:
        session = self.get_session(assessment_session_id)
        if session.phase is not AssessmentPhase.FOLLOWUP or session.validation_status != "VALID_FINALIZED":
            raise ValueError("only a valid finalized follow-up can become an observed outcome")
        if session.episode_id is None:
            raise ValueError("follow-up assessment must reference its prediction episode")
        with self._lock, self._connection() as connection:
            link = connection.execute(
                """SELECT 1 FROM assessment_episode_links
                   WHERE enrollment_id = ? AND episode_id = ?
                     AND baseline_assessment_session_id = (
                         SELECT assessment_session_id FROM assessment_sessions
                         WHERE enrollment_id = ? AND phase = 'BASELINE'
                     )""",
                (session.enrollment_id, session.episode_id, session.enrollment_id),
            ).fetchone()
            if link is None:
                raise ValueError("follow-up assessment is not linked to its finalized baseline episode")
        with self._lock, self._connection() as connection:
            if connection.execute(
                "SELECT 1 FROM finalized_assessment_outcomes WHERE episode_id = ?",
                (session.episode_id,),
            ).fetchone():
                raise ValueError("follow-up outcome has already been finalized")
        episode = self.episode_service.get_episode(session.episode_id, session.participant_id)
        config = self._read_config()
        self._validate_action_evidence(episode, action_evidence, config)
        if episode.action_completed_at is None:
            raise ValueError("action completion is required before follow-up outcome")
        lower = episode.action_completed_at + timedelta(days=config["observation_horizon"]["primary_horizon_days"])
        upper = episode.action_completed_at + timedelta(days=config["observation_horizon"]["allowed_timing_window_days"]["end"])
        if not lower <= session.started_at <= session.submitted_at <= upper:
            raise ValueError("follow-up timestamp is outside the T+7 through T+10 day window")
        if episode.status is EpisodeStatus.ACTION_COMPLETED:
            self.episode_service.mark_outcome_due(episode.episode_id, episode.user_id)
        observed = ObservedOutcome(
            target_name=episode.target.target_name,
            target_dimension=episode.target.target_dimension,
            target_unit=episode.target.target_unit,
            target_scale=episode.target.target_scale,
            value=session.aura_python_skill,
            provenance=OutcomeProvenance(
                source_type=OutcomeSource.ASSESSMENT,
                collection_method=episode.target.measurement_method,
                recorded_by=session.provenance.recorded_by,
                evidence_id=session.evidence_id,
                observed_at=session.submitted_at,
                quality=1.0,
                notes=(
                    f"assessment_session_id={session.assessment_session_id};"
                    f"instrument_version={session.form_version};instrument_hash={session.instrument_hash}"
                ),
            ),
        )
        updated = self.episode_service.record_observed_outcome(
            episode.episode_id,
            episode.user_id,
            observed,
        )
        with self._lock, self._connection() as connection:
            try:
                connection.execute(
                    """INSERT INTO finalized_assessment_outcomes
                       (episode_id, assessment_session_id) VALUES (?, ?)""",
                    (session.episode_id, session.assessment_session_id),
                )
            except sqlite3.IntegrityError as error:
                raise ValueError("follow-up outcome has already been finalized") from error
        return updated

    def _validate_followup(
        self,
        episode: Any,
        enrollment_id: str,
        started_at: datetime,
        submitted_at: datetime,
        action_evidence: PracticeActionEvidence | dict[str, Any] | None,
        config: dict[str, Any],
    ) -> None:
        with self._lock, self._connection() as connection:
            if not connection.execute(
                """SELECT 1 FROM assessment_sessions
                   WHERE enrollment_id = ? AND phase = 'BASELINE'""",
                (enrollment_id,),
            ).fetchone():
                raise ValueError("follow-up requires a finalized baseline for the same enrollment")
            if not connection.execute(
                """SELECT 1 FROM assessment_episode_links
                   WHERE enrollment_id = ? AND episode_id = ?""",
                (enrollment_id, episode.episode_id),
            ).fetchone():
                raise ValueError("follow-up episode is not linked to this enrollment")
        self._validate_action_evidence(episode, action_evidence, config)
        if episode.action_completed_at is None:
            raise ValueError("action must be completed before follow-up assessment")
        lower = episode.action_completed_at + timedelta(days=config["observation_horizon"]["primary_horizon_days"])
        upper = episode.action_completed_at + timedelta(days=config["observation_horizon"]["allowed_timing_window_days"]["end"])
        if not lower <= started_at <= submitted_at <= upper:
            raise ValueError("follow-up timestamp is outside the T+7 through T+10 day window")

    @staticmethod
    def _validate_action_evidence(
        episode: Any,
        evidence: PracticeActionEvidence | dict[str, Any] | None,
        config: dict[str, Any],
    ) -> None:
        persisted = episode.action_evidence
        if persisted is None:
            raise ValueError("episode has no persisted practice-module completion evidence")
        if evidence is not None:
            supplied = evidence if isinstance(evidence, PracticeActionEvidence) else PracticeActionEvidence.model_validate(evidence)
            if supplied != persisted:
                raise ValueError("supplied practice-module evidence does not match episode-recorded evidence")
        validated = persisted
        expected = config["artifact_bindings"]["module"]
        if (
            validated.module_id != expected["module_id"]
            or validated.module_version != expected["module_version"]
            or validated.module_hash != expected["module_hash"]
            or validated.completion_status != "complete"
            or validated.participant_id != episode.user_id
        ):
            raise ValueError("practice-module evidence does not match the bound completed module")
        module = PythonPracticeModuleService.load_module(MODULE_FILE)
        if module.module_hash != expected["module_hash"]:
            raise ValueError("practice-module artifact hash mismatch")
        if episode.action_completed_at is None or validated.completed_at > episode.action_completed_at:
            raise ValueError("practice-module completion must precede episode action completion")

    def _load_bound_form(self, form_id: str, config: dict[str, Any]) -> Any:
        path = FORM_FILES.get(form_id)
        if path is None:
            raise ValueError("unknown assessment form")
        form = PythonSkillAssessmentService.load_form(path)
        binding_name = "form_a" if form_id.endswith("_a_v1") else "form_b"
        binding = config["artifact_bindings"][binding_name]
        expected_hash = binding[f"{binding_name}_hash"]
        if form.form_id != binding[f"{binding_name}_id"] or form.assessment_hash != expected_hash:
            raise ValueError("assessment form hash or ID does not match protocol binding")
        return form

    def _read_config(self) -> dict[str, Any]:
        config = json.loads(self.config_path.read_text(encoding="utf-8"))
        payload = {key: value for key, value in config.items() if key != "protocol_hash"}
        calculated = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        if config.get("protocol_hash") != calculated:
            raise ValueError("protocol hash mismatch")
        return config

    @staticmethod
    def _require_aware(value: datetime, name: str) -> None:
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{name} must be a timezone-aware datetime")

    @staticmethod
    def _required_text(value: str, name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be non-empty")
        return value.strip()


def evaluate_pilot_collection_readiness(
    *,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    evidence_service: AssessmentEvidenceService | None,
) -> PilotReadinessResult:
    path = Path(config_path)
    config = json.loads(path.read_text(encoding="utf-8"))
    payload = {key: value for key, value in config.items() if key != "protocol_hash"}
    protocol_hash_valid = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest() == config.get("protocol_hash")
    artifact_bindings_valid = False
    measurement_valid = False
    action_valid = False
    blockers: list[str] = []
    try:
        evidence_service_available = isinstance(evidence_service, AssessmentEvidenceService)
        for (
            artifact_path,
            hash_field,
            binding,
            artifact_id_field,
            artifact_version_field,
            binding_id_field,
            binding_version_field,
            binding_hash_field,
        ) in [
            (
                ROOT / "research" / "17.16B" / "instruments" / "python_skill_blueprint_v1.json",
                "assessment_hash",
                config["artifact_bindings"]["blueprint"],
                "blueprint_id",
                "blueprint_version",
                "blueprint_id",
                "blueprint_version",
                "blueprint_hash",
            ),
            (
                FORM_FILES["python_skill_form_a_v1"],
                "assessment_hash",
                config["artifact_bindings"]["form_a"],
                "form_id",
                "form_version",
                "form_a_id",
                "form_a_version",
                "form_a_hash",
            ),
            (
                FORM_FILES["python_skill_form_b_v1"],
                "assessment_hash",
                config["artifact_bindings"]["form_b"],
                "form_id",
                "form_version",
                "form_b_id",
                "form_b_version",
                "form_b_hash",
            ),
            (
                MODULE_FILE,
                "module_hash",
                config["artifact_bindings"]["module"],
                "module_id",
                "module_version",
                "module_id",
                "module_version",
                "module_hash",
            ),
        ]:
            artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
            computed = hashlib.sha256(
                json.dumps(
                    {key: value for key, value in artifact.items() if key != hash_field},
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode("utf-8")
            ).hexdigest()
            if (
                artifact.get(hash_field) != computed
                or artifact.get(artifact_id_field) != binding[binding_id_field]
                or artifact.get(artifact_version_field) != binding[binding_version_field]
            ):
                raise ValueError(f"artifact binding invalid: {artifact_path.name}")
            if binding[binding_hash_field] != computed:
                raise ValueError(f"artifact digest binding invalid: {artifact_path.name}")
        blueprint = json.loads(
            (ROOT / "research" / "17.16B" / "instruments" / "python_skill_blueprint_v1.json").read_text(encoding="utf-8")
        )
        if (
            blueprint["form_a_id"] != config["artifact_bindings"]["form_a"]["form_a_id"]
            or blueprint["form_b_id"] != config["artifact_bindings"]["form_b"]["form_b_id"]
        ):
            raise ValueError("blueprint form references do not match the bound forms")
        artifact_bindings_valid = protocol_hash_valid
        expected_domain_points = {
            "variables_and_types": 20,
            "control_flow": 20,
            "functions": 20,
            "collections": 20,
            "debugging_reasoning": 10,
            "problem_solving": 10,
        }
        for form_id, form_path in FORM_FILES.items():
            form = PythonSkillAssessmentService.load_form(form_path)
            domain_points: dict[str, int] = {}
            for item in form.items:
                domain_points[item.domain] = domain_points.get(item.domain, 0) + item.maximum_points
            if (
                form.form_id != form_id
                or any(item.maximum_points != 10 for item in form.items)
                or len(form.items) != 10
                or domain_points != expected_domain_points
            ):
                raise ValueError(f"assessment form invalid: {form_id}")
        measurement_valid = True
        module = PythonPracticeModuleService.load_module(MODULE_FILE)
        domain_by_exercise = {exercise.exercise_id: exercise.domain for exercise in module.exercises}
        action_valid = (
            module.module_hash == config["artifact_bindings"]["module"]["module_hash"]
            and set(module.exercise_ids) == set(domain_by_exercise)
            and set(module.competency_domains) == set(domain_by_exercise.values())
            and set(module.required_exercises)
            == {exercise.exercise_id for exercise in module.exercises if exercise.required}
            and set(module.optional_exercises)
            == {exercise.exercise_id for exercise in module.exercises if not exercise.required}
        )
    except (KeyError, ValueError, OSError, json.JSONDecodeError) as error:
        blockers.append(str(error))
    secure_available = False
    secure_healthy = False
    try:
        secure_backend = get_secure_execution_backend()
        secure_available = isinstance(secure_backend, DockerContainerExecutor)
        secure_healthy = secure_backend.health_check()
    except (SecureExecutionUnavailable, ValueError) as error:
        blockers.append(str(error))
    if not protocol_hash_valid:
        blockers.append("protocol hash is invalid")
    if not artifact_bindings_valid:
        blockers.append("artifact bindings are invalid")
    if not measurement_valid:
        blockers.append("measurement artifacts are invalid")
    if not action_valid:
        blockers.append("action module is invalid")
    evidence_service_available = evidence_service_available and evidence_service is not None and evidence_service.health_check()
    if not evidence_service_available:
        blockers.append("assessment evidence validation service is unavailable")
    owner_approval = config.get("pilot_owner_approval") is True
    if not owner_approval:
        blockers.append("explicit pilot-owner approval is pending")
    ready = all(
        (
            protocol_hash_valid,
            artifact_bindings_valid,
            measurement_valid,
            action_valid,
            secure_available,
            secure_healthy,
            evidence_service_available,
            owner_approval,
        )
    )
    if secure_available and secure_healthy:
        security_gate = "PASS"
    elif secure_available:
        security_gate = "FAIL"
    else:
        security_gate = "BLOCKED_ENVIRONMENT_DEPENDENCY"
    return PilotReadinessResult(
        ready=ready,
        protocol_hash_valid=protocol_hash_valid,
        artifact_bindings_valid=artifact_bindings_valid,
        measurement_artifacts_valid=measurement_valid,
        action_module_valid=action_valid,
        secure_execution_backend_available=secure_available,
        secure_execution_backend_health_check=secure_healthy,
        secure_backend_type="docker_container" if secure_available else "unavailable",
        security_execution_gate=security_gate,
        evidence_validation_service_available=evidence_service_available,
        owner_approval=owner_approval,
        blockers=tuple(blockers),
    )
