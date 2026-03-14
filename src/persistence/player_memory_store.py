from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from typing import Iterable

from src.domain.main_character_memory import CharacterMemory, EventRecord, LLMTurnLog, Relationship, SemanticFact


class PlayerMemoryStore:
    SCHEMA_VERSION = 1

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
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            row = connection.execute(
                "SELECT value FROM schema_meta WHERE key = 'schema_version'"
            ).fetchone()
            if row is None:
                self._create_schema(connection)
                connection.execute(
                    "INSERT INTO schema_meta (key, value) VALUES ('schema_version', ?)",
                    (str(self.SCHEMA_VERSION),),
                )
            else:
                version = int(row["value"])
                if version != self.SCHEMA_VERSION:
                    raise RuntimeError(
                        f"Unsupported player memory schema version {version}; expected {self.SCHEMA_VERSION}."
                    )

    def _create_schema(self, connection: sqlite3.Connection):
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                player_id INTEGER NOT NULL,
                event_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                event_type TEXT NOT NULL,
                summary TEXT NOT NULL,
                location TEXT NOT NULL,
                stakes TEXT NOT NULL,
                sensory_details TEXT NOT NULL,
                latest_utterance TEXT NOT NULL,
                prompt TEXT NOT NULL,
                raw_payload TEXT NOT NULL,
                importance REAL NOT NULL,
                PRIMARY KEY (player_id, event_id)
            );
            CREATE TABLE IF NOT EXISTS event_participants (
                player_id INTEGER NOT NULL,
                event_id INTEGER NOT NULL,
                character_instance_id TEXT NOT NULL,
                PRIMARY KEY (player_id, event_id, character_instance_id)
            );
            CREATE TABLE IF NOT EXISTS event_tags (
                player_id INTEGER NOT NULL,
                event_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY (player_id, event_id, tag)
            );
            CREATE TABLE IF NOT EXISTS memories (
                player_id INTEGER NOT NULL,
                memory_id INTEGER NOT NULL,
                character_instance_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                summary TEXT NOT NULL,
                importance REAL NOT NULL,
                event_ids_json TEXT NOT NULL,
                embedding_json TEXT NOT NULL,
                last_recalled_at TEXT,
                recall_count INTEGER NOT NULL,
                PRIMARY KEY (player_id, memory_id)
            );
            CREATE TABLE IF NOT EXISTS memory_tags (
                player_id INTEGER NOT NULL,
                memory_id INTEGER NOT NULL,
                character_instance_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY (player_id, memory_id, tag)
            );
            CREATE TABLE IF NOT EXISTS facts (
                player_id INTEGER NOT NULL,
                fact_id INTEGER NOT NULL,
                character_instance_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                fact_text TEXT NOT NULL,
                confidence REAL NOT NULL,
                source_memory_ids_json TEXT NOT NULL,
                embedding_json TEXT NOT NULL,
                PRIMARY KEY (player_id, fact_id)
            );
            CREATE TABLE IF NOT EXISTS fact_tags (
                player_id INTEGER NOT NULL,
                fact_id INTEGER NOT NULL,
                character_instance_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY (player_id, fact_id, tag)
            );
            CREATE TABLE IF NOT EXISTS relationships (
                player_id INTEGER NOT NULL,
                character_instance_id TEXT NOT NULL,
                target_character_instance_id TEXT NOT NULL,
                affinity REAL NOT NULL,
                trust REAL NOT NULL,
                fear REAL NOT NULL,
                respect REAL NOT NULL,
                evidence_memory_ids_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (player_id, character_instance_id, target_character_instance_id)
            );
            CREATE TABLE IF NOT EXISTS llm_turn_logs (
                player_id INTEGER NOT NULL,
                turn_id INTEGER NOT NULL,
                character_instance_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                model TEXT NOT NULL,
                scene_frame_json TEXT NOT NULL,
                prompt_packet_json TEXT NOT NULL,
                output_payload_json TEXT NOT NULL,
                persisted_summary TEXT NOT NULL,
                PRIMARY KEY (player_id, turn_id)
            );
            CREATE INDEX IF NOT EXISTS idx_event_participants_character ON event_participants(player_id, character_instance_id, event_id);
            CREATE INDEX IF NOT EXISTS idx_memory_character ON memories(player_id, character_instance_id, memory_id);
            CREATE INDEX IF NOT EXISTS idx_memory_tag ON memory_tags(player_id, character_instance_id, tag, memory_id);
            CREATE INDEX IF NOT EXISTS idx_fact_character ON facts(player_id, character_instance_id, fact_id);
            CREATE INDEX IF NOT EXISTS idx_fact_tag ON fact_tags(player_id, character_instance_id, tag, fact_id);
            CREATE INDEX IF NOT EXISTS idx_relationship_character ON relationships(player_id, character_instance_id, target_character_instance_id);
            CREATE INDEX IF NOT EXISTS idx_turn_character ON llm_turn_logs(player_id, character_instance_id, turn_id);
            """
        )

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

    def list_events_for_character(self, player_id: int, character_instance_id: str, limit: int = 50) -> list[EventRecord]:
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
                    (int(memory.player_id), int(memory_id), str(memory.character_instance_id), str(tag).strip().lower()),
                )
        memory.memory_id = int(memory_id)
        return memory

    def list_memories_for_character(self, player_id: int, character_instance_id: str, limit: int | None = None) -> list[CharacterMemory]:
        limit = self._clamp_limit(limit)
        sql = (
            "SELECT * FROM memories WHERE player_id = ? AND character_instance_id = ? "
            "ORDER BY memory_id DESC"
        )
        params: list = [int(player_id), str(character_instance_id)]
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(sql, tuple(params)).fetchall()
            return [self._row_to_memory(connection, row) for row in rows]

    def list_memories_by_tags(self, player_id: int, character_instance_id: str, tags: Iterable[str], limit: int = 50) -> list[CharacterMemory]:
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

    def list_facts_for_character(self, player_id: int, character_instance_id: str, limit: int | None = None) -> list[SemanticFact]:
        limit = self._clamp_limit(limit)
        sql = "SELECT * FROM facts WHERE player_id = ? AND character_instance_id = ? ORDER BY fact_id DESC"
        params: list = [int(player_id), str(character_instance_id)]
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(sql, tuple(params)).fetchall()
            return [self._row_to_fact(connection, row) for row in rows]

    def list_facts_by_tags(self, player_id: int, character_instance_id: str, tags: Iterable[str], limit: int = 50) -> list[SemanticFact]:
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

    def get_relationship(self, player_id: int, character_instance_id: str, target_character_instance_id: str) -> Relationship | None:
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

    def list_turn_logs_for_character(self, player_id: int, character_instance_id: str, limit: int = 20) -> list[LLMTurnLog]:
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
        participant_rows = connection.execute(
            "SELECT character_instance_id FROM event_participants WHERE player_id = ? AND event_id = ? ORDER BY character_instance_id",
            (int(row["player_id"]), int(row["event_id"])),
        ).fetchall()
        tag_rows = connection.execute(
            "SELECT tag FROM event_tags WHERE player_id = ? AND event_id = ? ORDER BY tag",
            (int(row["player_id"]), int(row["event_id"])),
        ).fetchall()
        return EventRecord(
            player_id=int(row["player_id"]),
            event_id=int(row["event_id"]),
            created_at=str(row["created_at"]),
            event_type=str(row["event_type"]),
            summary=str(row["summary"]),
            participants=[str(item["character_instance_id"]) for item in participant_rows],
            tags=[str(item["tag"]) for item in tag_rows],
            location=str(row["location"]),
            stakes=str(row["stakes"]),
            sensory_details=str(row["sensory_details"]),
            latest_utterance=str(row["latest_utterance"]),
            prompt=str(row["prompt"]),
            raw_payload=self._from_json(row["raw_payload"], {}),
            importance=float(row["importance"]),
        )

    def _row_to_memory(self, connection: sqlite3.Connection, row: sqlite3.Row) -> CharacterMemory:
        tag_rows = connection.execute(
            "SELECT tag FROM memory_tags WHERE player_id = ? AND memory_id = ? ORDER BY tag",
            (int(row["player_id"]), int(row["memory_id"])),
        ).fetchall()
        return CharacterMemory(
            player_id=int(row["player_id"]),
            memory_id=int(row["memory_id"]),
            character_instance_id=str(row["character_instance_id"]),
            created_at=str(row["created_at"]),
            summary=str(row["summary"]),
            importance=float(row["importance"]),
            tags=[str(item["tag"]) for item in tag_rows],
            event_ids=self._from_json(row["event_ids_json"], []),
            embedding=self._from_json(row["embedding_json"], []),
            last_recalled_at=row["last_recalled_at"],
            recall_count=int(row["recall_count"]),
        )

    def _row_to_fact(self, connection: sqlite3.Connection, row: sqlite3.Row) -> SemanticFact:
        tag_rows = connection.execute(
            "SELECT tag FROM fact_tags WHERE player_id = ? AND fact_id = ? ORDER BY tag",
            (int(row["player_id"]), int(row["fact_id"])),
        ).fetchall()
        return SemanticFact(
            player_id=int(row["player_id"]),
            fact_id=int(row["fact_id"]),
            character_instance_id=str(row["character_instance_id"]),
            created_at=str(row["created_at"]),
            fact_text=str(row["fact_text"]),
            confidence=float(row["confidence"]),
            tags=[str(item["tag"]) for item in tag_rows],
            source_memory_ids=self._from_json(row["source_memory_ids_json"], []),
            embedding=self._from_json(row["embedding_json"], []),
        )

    def _row_to_relationship(self, row: sqlite3.Row) -> Relationship:
        return Relationship(
            player_id=int(row["player_id"]),
            character_instance_id=str(row["character_instance_id"]),
            target_character_instance_id=str(row["target_character_instance_id"]),
            affinity=float(row["affinity"]),
            trust=float(row["trust"]),
            fear=float(row["fear"]),
            respect=float(row["respect"]),
            evidence_memory_ids=self._from_json(row["evidence_memory_ids_json"], []),
            updated_at=str(row["updated_at"]),
        )

    def _row_to_turn_log(self, row: sqlite3.Row) -> LLMTurnLog:
        return LLMTurnLog(
            player_id=int(row["player_id"]),
            turn_id=int(row["turn_id"]),
            character_instance_id=str(row["character_instance_id"]),
            created_at=str(row["created_at"]),
            model=str(row["model"]),
            scene_frame=self._from_json(row["scene_frame_json"], {}),
            prompt_packet=self._from_json(row["prompt_packet_json"], {}),
            output_payload=self._from_json(row["output_payload_json"], {}),
            persisted_summary=str(row["persisted_summary"]),
        )
