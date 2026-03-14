from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class EventRecord:
    player_id: int
    event_id: int
    created_at: str
    event_type: str
    summary: str
    participants: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    location: str = ""
    stakes: str = ""
    sensory_details: str = ""
    latest_utterance: str = ""
    prompt: str = ""
    raw_payload: dict[str, Any] = field(default_factory=dict)
    importance: float = 0.0


@dataclass
class CharacterMemory:
    player_id: int
    memory_id: int
    character_instance_id: str
    created_at: str
    summary: str
    importance: float
    tags: list[str] = field(default_factory=list)
    event_ids: list[int] = field(default_factory=list)
    embedding: list[float] = field(default_factory=list)
    last_recalled_at: str | None = None
    recall_count: int = 0


@dataclass
class SemanticFact:
    player_id: int
    fact_id: int
    character_instance_id: str
    created_at: str
    fact_text: str
    confidence: float = 0.5
    tags: list[str] = field(default_factory=list)
    source_memory_ids: list[int] = field(default_factory=list)
    embedding: list[float] = field(default_factory=list)


@dataclass
class Relationship:
    player_id: int
    character_instance_id: str
    target_character_instance_id: str
    affinity: float = 0.0
    trust: float = 0.0
    fear: float = 0.0
    respect: float = 0.0
    evidence_memory_ids: list[int] = field(default_factory=list)
    updated_at: str = field(default_factory=utc_now_iso)


@dataclass
class LLMTurnLog:
    player_id: int
    turn_id: int
    character_instance_id: str
    created_at: str
    model: str
    scene_frame: dict[str, Any]
    prompt_packet: dict[str, Any]
    output_payload: dict[str, Any]
    persisted_summary: str = ""
