from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from typing import Iterable

from src.domain.main_character_memory import CharacterMemory, EventRecord, LLMTurnLog, Relationship, SemanticFact
from src.persistence.player_memory.rows import (
    row_to_event,
    row_to_fact,
    row_to_memory,
    row_to_relationship,
    row_to_turn_log,
)
from src.persistence.player_memory.schema import SCHEMA_VERSION, ensure_schema


class PlayerMemoryStore:
    SCHEMA_VERSION = SCHEMA_VERSION

    def __init__(self, db_path: str):
        self.db_path = db_path

    def ensure_directory(self):
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    @contextmanager
    def connect(self):
        self.ensure_directory()
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self):
        with self.connect() as connection:
            ensure_schema(connection, self.SCHEMA_VERSION)

    @staticmethod
    def _to_json(value) -> str:
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _from_json(value: str, default):
        if not value:
            return default
        try:
            return json.loads(value)
        except Exception:
            return default

    @staticmethod
    def _clamp_limit(limit: int | None) -> int | None:
        if limit is None:
            return None
        return max(1, int(limit))

    def _next_id(self, connection: sqlite3.Connection, table: str, id_column: str, player_id: int) -> int:
        row = connection.execute(
            f"SELECT COALESCE(MAX({id_column}), 0) AS max_id FROM {table} WHERE player_id = ?",
            (int(player_id),),
        ).fetchone()
        return int(row["max_id"]) + 1

    def insert_event(self, record: EventRecord) -> EventRecord:
        with self.connect() as connection:
            event_id = record.event_id or self._next_id(connection, "events", "event_id", record.player_id)
            connection.execute(
                """
                INSERT INTO events (
                    player_id, event_id, created_at, event_type, summary, location, stakes,
                    sensory_details, latest_utterance, prompt, raw_payload, importance
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(record.player_id),
                    int(event_id),
                    record.created_at,
                    record.event_type,
                    record.summary,
                    record.location,
                    record.stakes,
                    record.sensory_details,
                    record.latest_utterance,
                    record.prompt,
                    self._to_json(record.raw_payload),
                    float(record.importance),
                ),
            )
            for participant in record.participants:
                connection.execute(
                    "INSERT OR IGNORE INTO event_participants (player_id, event_id, character_instance_id) VALUES (?, ?, ?)",
                    (int(record.player_id), int(event_id), str(participant)),
                )
            for tag in record.tags:
                connection.execute(
                    "INSERT OR IGNORE INTO event_tags (player_id, event_id, tag) VALUES (?, ?, ?)",
                    (int(record.player_id), int(event_id), str(tag).strip().lower()),
                )
        record.event_id = int(event_id)
        return record

    def list_events_for_character(
        self, player_id: int, character_instance_id: str, limit: int = 50
    ) -> list[EventRecord]:
        limit = self._clamp_limit(limit) or 50
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT e.* FROM events e
                INNER JOIN event_participants p
                    ON p.player_id = e.player_id AND p.event_id = e.event_id
                WHERE e.player_id = ? AND p.character_instance_id = ?
                ORDER BY e.event_id DESC
                LIMIT ?
                """,
                (int(player_id), str(character_instance_id), limit),
            ).fetchall()
            return [self._row_to_event(connection, row) for row in rows]

    def insert_memory(self, memory: CharacterMemory) -> CharacterMemory:
        with self.connect() as connection:
            memory_id = memory.memory_id or self._next_id(connection, "memories", "memory_id", memory.player_id)
            connection.execute(
                """
                INSERT INTO memories (
                    player_id, memory_id, character_instance_id, created_at, summary, importance,
                    event_ids_json, embedding_json, last_recalled_at, recall_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(memory.player_id),
                    int(memory_id),
                    str(memory.character_instance_id),
                    memory.created_at,
                    memory.summary,
                    float(memory.importance),
                    self._to_json(memory.event_ids),
                    self._to_json(memory.embedding),
                    memory.last_recalled_at,
                    int(memory.recall_count),
                ),
            )
            for tag in memory.tags:
                connection.execute(
                    "INSERT OR IGNORE INTO memory_tags (player_id, memory_id, character_instance_id, tag) VALUES (?, ?, ?, ?)",
                    (
                        int(memory.player_id),
                        int(memory_id),
                        str(memory.character_instance_id),
                        str(tag).strip().lower(),
                    ),
                )
        memory.memory_id = int(memory_id)
        return memory

    def list_memories_for_character(
        self, player_id: int, character_instance_id: str, limit: int | None = None
    ) -> list[CharacterMemory]:
        limit = self._clamp_limit(limit)
        sql = "SELECT * FROM memories WHERE player_id = ? AND character_instance_id = ? ORDER BY memory_id DESC"
        params: list = [int(player_id), str(character_instance_id)]
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(sql, tuple(params)).fetchall()
            return [self._row_to_memory(connection, row) for row in rows]

    def list_memories_by_tags(
        self, player_id: int, character_instance_id: str, tags: Iterable[str], limit: int = 50
    ) -> list[CharacterMemory]:
        normalized_tags = [str(tag).strip().lower() for tag in tags if str(tag).strip()]
        if not normalized_tags:
            return []
        placeholders = ", ".join(["?"] * len(normalized_tags))
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT DISTINCT m.* FROM memories m
                INNER JOIN memory_tags t
                    ON t.player_id = m.player_id AND t.memory_id = m.memory_id
                WHERE m.player_id = ? AND m.character_instance_id = ? AND t.tag IN ({placeholders})
                ORDER BY m.memory_id DESC
                LIMIT ?
                """,
                (int(player_id), str(character_instance_id), *normalized_tags, int(limit)),
            ).fetchall()
            return [self._row_to_memory(connection, row) for row in rows]

    def touch_memories(self, player_id: int, memory_ids: Iterable[int], recalled_at: str):
        memory_ids = [int(memory_id) for memory_id in memory_ids]
        if not memory_ids:
            return
        placeholders = ", ".join(["?"] * len(memory_ids))
        with self.connect() as connection:
            connection.execute(
                f"""
                UPDATE memories
                SET last_recalled_at = ?, recall_count = recall_count + 1
                WHERE player_id = ? AND memory_id IN ({placeholders})
                """,
                (recalled_at, int(player_id), *memory_ids),
            )

    def count_memories_for_character(self, player_id: int, character_instance_id: str) -> int:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count_value FROM memories WHERE player_id = ? AND character_instance_id = ?",
                (int(player_id), str(character_instance_id)),
            ).fetchone()
            return int(row["count_value"])

    def insert_fact(self, fact: SemanticFact) -> SemanticFact:
        with self.connect() as connection:
            fact_id = fact.fact_id or self._next_id(connection, "facts", "fact_id", fact.player_id)
            connection.execute(
                """
                INSERT INTO facts (
                    player_id, fact_id, character_instance_id, created_at, fact_text,
                    confidence, source_memory_ids_json, embedding_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(fact.player_id),
                    int(fact_id),
                    str(fact.character_instance_id),
                    fact.created_at,
                    fact.fact_text,
                    float(fact.confidence),
                    self._to_json(fact.source_memory_ids),
                    self._to_json(fact.embedding),
                ),
            )
            for tag in fact.tags:
                connection.execute(
                    "INSERT OR IGNORE INTO fact_tags (player_id, fact_id, character_instance_id, tag) VALUES (?, ?, ?, ?)",
                    (int(fact.player_id), int(fact_id), str(fact.character_instance_id), str(tag).strip().lower()),
                )
        fact.fact_id = int(fact_id)
        return fact

    def list_facts_for_character(
        self, player_id: int, character_instance_id: str, limit: int | None = None
    ) -> list[SemanticFact]:
        limit = self._clamp_limit(limit)
        sql = "SELECT * FROM facts WHERE player_id = ? AND character_instance_id = ? ORDER BY fact_id DESC"
        params: list = [int(player_id), str(character_instance_id)]
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(sql, tuple(params)).fetchall()
            return [self._row_to_fact(connection, row) for row in rows]

    def list_facts_by_tags(
        self, player_id: int, character_instance_id: str, tags: Iterable[str], limit: int = 50
    ) -> list[SemanticFact]:
        normalized_tags = [str(tag).strip().lower() for tag in tags if str(tag).strip()]
        if not normalized_tags:
            return []
        placeholders = ", ".join(["?"] * len(normalized_tags))
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT DISTINCT f.* FROM facts f
                INNER JOIN fact_tags t
                    ON t.player_id = f.player_id AND t.fact_id = f.fact_id
                WHERE f.player_id = ? AND f.character_instance_id = ? AND t.tag IN ({placeholders})
                ORDER BY f.fact_id DESC
                LIMIT ?
                """,
                (int(player_id), str(character_instance_id), *normalized_tags, int(limit)),
            ).fetchall()
            return [self._row_to_fact(connection, row) for row in rows]

    def get_relationship(
        self, player_id: int, character_instance_id: str, target_character_instance_id: str
    ) -> Relationship | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM relationships
                WHERE player_id = ? AND character_instance_id = ? AND target_character_instance_id = ?
                """,
                (int(player_id), str(character_instance_id), str(target_character_instance_id)),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_relationship(row)

    def list_relationships_for_character(self, player_id: int, character_instance_id: str) -> list[Relationship]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM relationships WHERE player_id = ? AND character_instance_id = ? ORDER BY target_character_instance_id",
                (int(player_id), str(character_instance_id)),
            ).fetchall()
            return [self._row_to_relationship(row) for row in rows]

    def upsert_relationship(self, relationship: Relationship):
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO relationships (
                    player_id, character_instance_id, target_character_instance_id,
                    affinity, trust, fear, respect, evidence_memory_ids_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(player_id, character_instance_id, target_character_instance_id)
                DO UPDATE SET
                    affinity = excluded.affinity,
                    trust = excluded.trust,
                    fear = excluded.fear,
                    respect = excluded.respect,
                    evidence_memory_ids_json = excluded.evidence_memory_ids_json,
                    updated_at = excluded.updated_at
                """,
                (
                    int(relationship.player_id),
                    str(relationship.character_instance_id),
                    str(relationship.target_character_instance_id),
                    float(relationship.affinity),
                    float(relationship.trust),
                    float(relationship.fear),
                    float(relationship.respect),
                    self._to_json(relationship.evidence_memory_ids),
                    relationship.updated_at,
                ),
            )

    def insert_turn_log(self, log: LLMTurnLog) -> LLMTurnLog:
        with self.connect() as connection:
            turn_id = log.turn_id or self._next_id(connection, "llm_turn_logs", "turn_id", log.player_id)
            connection.execute(
                """
                INSERT INTO llm_turn_logs (
                    player_id, turn_id, character_instance_id, created_at, model,
                    scene_frame_json, prompt_packet_json, output_payload_json, persisted_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(log.player_id),
                    int(turn_id),
                    str(log.character_instance_id),
                    log.created_at,
                    log.model,
                    self._to_json(log.scene_frame),
                    self._to_json(log.prompt_packet),
                    self._to_json(log.output_payload),
                    log.persisted_summary,
                ),
            )
        log.turn_id = int(turn_id)
        return log

    def list_turn_logs_for_character(
        self, player_id: int, character_instance_id: str, limit: int = 20
    ) -> list[LLMTurnLog]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM llm_turn_logs
                WHERE player_id = ? AND character_instance_id = ?
                ORDER BY turn_id DESC
                LIMIT ?
                """,
                (int(player_id), str(character_instance_id), int(limit)),
            ).fetchall()
            return [self._row_to_turn_log(row) for row in rows]

    def _row_to_event(self, connection: sqlite3.Connection, row: sqlite3.Row) -> EventRecord:
        return row_to_event(connection, row, self._from_json)

    def _row_to_memory(self, connection: sqlite3.Connection, row: sqlite3.Row) -> CharacterMemory:
        return row_to_memory(connection, row, self._from_json)

    def _row_to_fact(self, connection: sqlite3.Connection, row: sqlite3.Row) -> SemanticFact:
        return row_to_fact(connection, row, self._from_json)

    def _row_to_relationship(self, row: sqlite3.Row) -> Relationship:
        return row_to_relationship(row, self._from_json)

    def _row_to_turn_log(self, row: sqlite3.Row) -> LLMTurnLog:
        return row_to_turn_log(row, self._from_json)
