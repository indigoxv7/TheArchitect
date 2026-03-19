from __future__ import annotations

import sqlite3


SCHEMA_VERSION = 1


def ensure_schema(connection: sqlite3.Connection, schema_version: int = SCHEMA_VERSION):
    connection.execute("CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    row = connection.execute("SELECT value FROM schema_meta WHERE key = 'schema_version'").fetchone()
    if row is None:
        create_schema(connection)
        connection.execute(
            "INSERT INTO schema_meta (key, value) VALUES ('schema_version', ?)",
            (str(schema_version),),
        )
        return

    version = int(row["value"])
    if version != schema_version:
        raise RuntimeError(
            f"Unsupported player memory schema version {version}; expected {schema_version}."
        )


def create_schema(connection: sqlite3.Connection):
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
