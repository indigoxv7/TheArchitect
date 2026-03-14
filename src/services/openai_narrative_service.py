from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, Field


class RelationshipDeltaModel(BaseModel):
    target_character_instance_id: str = ""
    affinity_delta: float = 0.0
    trust_delta: float = 0.0
    fear_delta: float = 0.0
    respect_delta: float = 0.0
    reason: str = ""


class TurnResponseModel(BaseModel):
    spoken_text: str
    action_summary: str
    scene_tags: list[str] = Field(default_factory=list)
    self_emotion: str = ""
    relationship_deltas: list[RelationshipDeltaModel] = Field(default_factory=list)


class MemoryDistillationModel(BaseModel):
    summary: str
    importance: float = 0.5
    tags: list[str] = Field(default_factory=list)
    fact_candidates: list[str] = Field(default_factory=list)
    relationship_deltas: list[RelationshipDeltaModel] = Field(default_factory=list)


class ReflectionModel(BaseModel):
    insights: list[str] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class OpenAINarrativeService:
    def __init__(
        self,
        api_key: str | None = None,
        turn_model: str | None = None,
        memory_model: str | None = None,
        embedding_model: str | None = None,
    ):
        self._api_key_override = api_key
        self.turn_model = turn_model or os.getenv("OPENAI_TURN_MODEL") or "gpt-5.2"
        self.memory_model = memory_model or os.getenv("OPENAI_MEMORY_MODEL") or "gpt-5-mini"
        self.embedding_model = embedding_model or os.getenv("OPENAI_EMBEDDING_MODEL") or "text-embedding-3-small"
        self._client: OpenAI | None = None

    @staticmethod
    def resolve_api_key(explicit_api_key: str | None = None) -> str | None:
        if explicit_api_key:
            return explicit_api_key
        return os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_AI_API_KEY")

    def is_configured(self) -> bool:
        return bool(self.resolve_api_key(self._api_key_override))

    def _get_client(self) -> OpenAI:
        if self._client is None:
            api_key = self.resolve_api_key(self._api_key_override)
            if not api_key:
                raise RuntimeError("OpenAI API key not configured. Set OPENAI_API_KEY or OPEN_AI_API_KEY.")
            self._client = OpenAI(api_key=api_key)
        return self._client

    @staticmethod
    def _normalize_tags(tags: list[str]) -> list[str]:
        result = []
        seen = set()
        for tag in tags:
            normalized = str(tag or "").strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            result.append(normalized)
        return result

    def embed_text(self, text: str) -> list[float]:
        client = self._get_client()
        response = client.embeddings.create(
            model=self.embedding_model,
            input=str(text or ""),
        )
        if not response.data:
            return []
        return list(response.data[0].embedding)

    def generate_turn(self, prompt_packet: dict[str, Any]) -> TurnResponseModel:
        client = self._get_client()
        response = client.responses.parse(
            model=self.turn_model,
            reasoning={"effort": "medium"},
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are roleplaying exactly one character in a fantasy game. "
                        "Only use the supplied prompt packet. Never invent forbidden knowledge. "
                        "Return concise in-character speech and a short action summary."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(prompt_packet, ensure_ascii=False),
                },
            ],
            text_format=TurnResponseModel,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError("OpenAI turn response did not produce structured output.")
        parsed.scene_tags = self._normalize_tags(parsed.scene_tags)
        return parsed

    def distill_memory(self, character_packet: dict[str, Any], event_packet: dict[str, Any]) -> MemoryDistillationModel:
        client = self._get_client()
        response = client.responses.parse(
            model=self.memory_model,
            reasoning={"effort": "low"},
            input=[
                {
                    "role": "system",
                    "content": (
                        "Summarize one event from a single character's point of view. "
                        "Produce a short memory summary, importance 0.0-1.0, compact tags, "
                        "candidate durable facts, and optional relationship deltas."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "character": character_packet,
                            "event": event_packet,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            text_format=MemoryDistillationModel,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError("OpenAI memory distillation did not produce structured output.")
        parsed.importance = max(0.0, min(1.0, float(parsed.importance)))
        parsed.tags = self._normalize_tags(parsed.tags)
        return parsed

    def reflect(self, character_packet: dict[str, Any], memories: list[dict[str, Any]]) -> ReflectionModel:
        client = self._get_client()
        response = client.responses.parse(
            model=self.memory_model,
            reasoning={"effort": "low"},
            input=[
                {
                    "role": "system",
                    "content": (
                        "Synthesize higher-level insights and stable facts from a set of memories. "
                        "Return only durable conclusions that the character would plausibly believe."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "character": character_packet,
                            "memories": memories,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            text_format=ReflectionModel,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError("OpenAI reflection did not produce structured output.")
        parsed.tags = self._normalize_tags(parsed.tags)
        return parsed
