from __future__ import annotations

import sqlite3

from src.domain.main_character_memory import CharacterMemory, EventRecord, LLMTurnLog, Relationship, SemanticFact


def row_to_event(connection: sqlite3.Connection, row: sqlite3.Row, from_json) -> EventRecord:
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
        raw_payload=from_json(row["raw_payload"], {}),
        importance=float(row["importance"]),
    )


def row_to_memory(connection: sqlite3.Connection, row: sqlite3.Row, from_json) -> CharacterMemory:
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
        event_ids=from_json(row["event_ids_json"], []),
        embedding=from_json(row["embedding_json"], []),
        last_recalled_at=row["last_recalled_at"],
        recall_count=int(row["recall_count"]),
    )


def row_to_fact(connection: sqlite3.Connection, row: sqlite3.Row, from_json) -> SemanticFact:
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
        source_memory_ids=from_json(row["source_memory_ids_json"], []),
        embedding=from_json(row["embedding_json"], []),
    )


def row_to_relationship(row: sqlite3.Row, from_json) -> Relationship:
    return Relationship(
        player_id=int(row["player_id"]),
        character_instance_id=str(row["character_instance_id"]),
        target_character_instance_id=str(row["target_character_instance_id"]),
        affinity=float(row["affinity"]),
        trust=float(row["trust"]),
        fear=float(row["fear"]),
        respect=float(row["respect"]),
        evidence_memory_ids=from_json(row["evidence_memory_ids_json"], []),
        updated_at=str(row["updated_at"]),
    )


def row_to_turn_log(row: sqlite3.Row, from_json) -> LLMTurnLog:
    return LLMTurnLog(
        player_id=int(row["player_id"]),
        turn_id=int(row["turn_id"]),
        character_instance_id=str(row["character_instance_id"]),
        created_at=str(row["created_at"]),
        model=str(row["model"]),
        scene_frame=from_json(row["scene_frame_json"], {}),
        prompt_packet=from_json(row["prompt_packet_json"], {}),
        output_payload=from_json(row["output_payload_json"], {}),
        persisted_summary=str(row["persisted_summary"]),
    )
