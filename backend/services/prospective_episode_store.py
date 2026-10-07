from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Sequence

from backend.models.prospective_prediction_episode import (
    EpisodeAuditEvent,
    ProspectivePredictionEpisode,
)

DEFAULT_PROSPECTIVE_DB = (
    Path(__file__).resolve().parents[1] / "data" / "prospective_outcomes" / "prospective_outcomes.sqlite3"
)


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))


def _episode_json(episode: ProspectivePredictionEpisode) -> str:
    return _json(episode.model_dump(mode="json"))


def _frozen_payload(episode: ProspectivePredictionEpisode) -> str:
    episode_data = episode.model_dump(mode="json")
    return _json(
        {
            field: episode_data[field]
            for field in (
                "episode_id",
                "user_id",
                "created_at",
                "prediction_timestamp",
                "pre_action_state",
                "action",
                "context",
                "predictions",
                "target",
                "pilot_id",
                "enrollment_id",
                "baseline_assessment_session_id",
            )
        }
    )


class ProspectiveEpisodeStore:
    """SQLite persistence kept separate from AURA's training and synthetic data files."""

    def __init__(self, database_path: Path | str = DEFAULT_PROSPECTIVE_DB) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        connection = sqlite3.connect(self.database_path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS prospective_episodes (
                    episode_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    frozen_payload TEXT NOT NULL,
                    episode_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS prospective_episode_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    episode_id TEXT NOT NULL REFERENCES prospective_episodes(episode_id),
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_prospective_episodes_user
                    ON prospective_episodes(user_id, episode_id);
                CREATE INDEX IF NOT EXISTS idx_prospective_events_episode
                    ON prospective_episode_events(episode_id, event_id);

                CREATE TRIGGER IF NOT EXISTS prevent_frozen_payload_update
                BEFORE UPDATE OF frozen_payload ON prospective_episodes
                WHEN OLD.frozen_payload != NEW.frozen_payload
                BEGIN
                    SELECT RAISE(ABORT, 'frozen prediction payload is immutable');
                END;

                CREATE TRIGGER IF NOT EXISTS prevent_episode_json_frozen_field_update
                BEFORE UPDATE OF episode_json ON prospective_episodes
                WHEN
                    json_extract(NEW.episode_json, '$.episode_id') IS NOT json_extract(OLD.frozen_payload, '$.episode_id')
                    OR json_extract(NEW.episode_json, '$.user_id') IS NOT json_extract(OLD.frozen_payload, '$.user_id')
                    OR json_extract(NEW.episode_json, '$.created_at') IS NOT json_extract(OLD.frozen_payload, '$.created_at')
                    OR json_extract(NEW.episode_json, '$.prediction_timestamp') IS NOT json_extract(OLD.frozen_payload, '$.prediction_timestamp')
                    OR json(json_extract(NEW.episode_json, '$.pre_action_state')) IS NOT json(json_extract(OLD.frozen_payload, '$.pre_action_state'))
                    OR json_extract(NEW.episode_json, '$.action') IS NOT json_extract(OLD.frozen_payload, '$.action')
                    OR json(json_extract(NEW.episode_json, '$.context')) IS NOT json(json_extract(OLD.frozen_payload, '$.context'))
                    OR json(json_extract(NEW.episode_json, '$.predictions')) IS NOT json(json_extract(OLD.frozen_payload, '$.predictions'))
                    OR json(json_extract(NEW.episode_json, '$.target')) IS NOT json(json_extract(OLD.frozen_payload, '$.target'))
                    OR json_extract(NEW.episode_json, '$.enrollment_id') IS NOT json_extract(OLD.frozen_payload, '$.enrollment_id')
                    OR json_extract(NEW.episode_json, '$.baseline_assessment_session_id') IS NOT json_extract(OLD.frozen_payload, '$.baseline_assessment_session_id')
                BEGIN
                    SELECT RAISE(ABORT, 'episode JSON contains modified frozen fields');
                END;

                CREATE TRIGGER IF NOT EXISTS prevent_action_evidence_update
                BEFORE UPDATE OF episode_json ON prospective_episodes
                WHEN
                    json_extract(OLD.episode_json, '$.action_evidence') IS NOT NULL
                    AND json(json_extract(NEW.episode_json, '$.action_evidence'))
                        IS NOT json(json_extract(OLD.episode_json, '$.action_evidence'))
                BEGIN
                    SELECT RAISE(ABORT, 'action completion evidence is immutable');
                END;

                CREATE TRIGGER IF NOT EXISTS prevent_audit_event_update
                BEFORE UPDATE ON prospective_episode_events
                BEGIN
                    SELECT RAISE(ABORT, 'prospective audit events are append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS prevent_audit_event_delete
                BEFORE DELETE ON prospective_episode_events
                BEGIN
                    SELECT RAISE(ABORT, 'prospective audit events are append-only');
                END;
                """
            )

    @staticmethod
    def _insert_events(connection: sqlite3.Connection, events: Sequence[EpisodeAuditEvent]) -> None:
        connection.executemany(
            """
            INSERT INTO prospective_episode_events
                (episode_id, timestamp, event_type, metadata_json)
            VALUES (?, ?, ?, ?)
            """,
            [
                (
                    event.episode_id,
                    event.timestamp.isoformat(),
                    event.event_type.value,
                    _json(event.metadata),
                )
                for event in events
            ],
        )

    def create_episode(
        self,
        episode: ProspectivePredictionEpisode,
        events: Sequence[EpisodeAuditEvent],
    ) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO prospective_episodes
                    (episode_id, user_id, frozen_payload, episode_json)
                VALUES (?, ?, ?, ?)
                """,
                (episode.episode_id, episode.user_id, _frozen_payload(episode), _episode_json(episode)),
            )
            self._insert_events(connection, events)

    def update_episode(
        self,
        episode: ProspectivePredictionEpisode,
        events: Sequence[EpisodeAuditEvent],
        *,
        expected_episode: ProspectivePredictionEpisode,
    ) -> None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT frozen_payload FROM prospective_episodes WHERE episode_id = ? AND user_id = ?",
                (episode.episode_id, episode.user_id),
            ).fetchone()
            if row is None:
                raise KeyError("prospective episode not found for this user")
            if row["frozen_payload"] != _frozen_payload(episode):
                raise ValueError("prediction timestamp, state, action, context, target, and predictions are frozen")
            result = connection.execute(
                """
                UPDATE prospective_episodes
                SET episode_json = ?
                WHERE episode_id = ? AND user_id = ? AND episode_json = ?
                """,
                (
                    _episode_json(episode),
                    episode.episode_id,
                    episode.user_id,
                    _episode_json(expected_episode),
                ),
            )
            if result.rowcount != 1:
                raise ValueError("prospective episode changed concurrently; reload before updating")
            self._insert_events(connection, events)

    def append_event(self, event: EpisodeAuditEvent) -> None:
        with self._connection() as connection:
            if not connection.execute(
                "SELECT 1 FROM prospective_episodes WHERE episode_id = ?",
                (event.episode_id,),
            ).fetchone():
                raise KeyError("prospective episode not found")
            self._insert_events(connection, [event])

    def get_episode(self, episode_id: str, user_id: str) -> ProspectivePredictionEpisode | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT episode_json FROM prospective_episodes WHERE episode_id = ? AND user_id = ?",
                (episode_id, user_id),
            ).fetchone()
        if row is None:
            return None
        return ProspectivePredictionEpisode.model_validate_json(row["episode_json"])

    def list_episodes(self, user_id: str) -> list[ProspectivePredictionEpisode]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT episode_json FROM prospective_episodes WHERE user_id = ? ORDER BY rowid",
                (user_id,),
            ).fetchall()
        return [ProspectivePredictionEpisode.model_validate_json(row["episode_json"]) for row in rows]

    def list_events(self, episode_id: str, user_id: str) -> list[EpisodeAuditEvent]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT prospective_episode_events.event_id,
                       prospective_episode_events.episode_id,
                       prospective_episode_events.timestamp,
                       prospective_episode_events.event_type,
                       prospective_episode_events.metadata_json
                FROM prospective_episode_events
                INNER JOIN prospective_episodes USING (episode_id)
                WHERE prospective_episode_events.episode_id = ? AND prospective_episodes.user_id = ?
                ORDER BY prospective_episode_events.event_id
                """,
                (episode_id, user_id),
            ).fetchall()
        return [
            EpisodeAuditEvent(
                event_id=row["event_id"],
                episode_id=row["episode_id"],
                timestamp=row["timestamp"],
                event_type=row["event_type"],
                metadata=json.loads(row["metadata_json"]),
            )
            for row in rows
        ]
