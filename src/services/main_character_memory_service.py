from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from src.domain.main_character import MainCharacter
from src.domain.main_character_memory import CharacterMemory, EventRecord, LLMTurnLog, Relationship, SemanticFact, utc_now_iso
from src.persistence.player_memory import PlayerMemoryStore
from src.services.openai_narrative_service import MemoryDistillationModel, OpenAINarrativeService, TurnResponseModel


class MainCharacterMemoryService:
    HIGH_SIGNAL_KEYWORDS = {
        "promise",
        "promised",
        "betray",
        "betrayed",
        "attack",
        "attacked",
        "injured",
        "wounded",
        "killed",
        "found",
        "gained",
        "lost",
        "secret",
        "fear",
        "alliance",
        "quest",
        "goal",
        "discover",
        "discovered",
        "mission",
    }

    def __init__(
        self,
        memory_store: PlayerMemoryStore,
        player_service,
        openai_service: OpenAINarrativeService,
    ):
        self.store = memory_store
        self.player_service = player_service
        self.openai_service = openai_service

    def initialize(self):
        self.store.initialize()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _iso_to_datetime(value: str | None) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return datetime.now(timezone.utc)

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, float(value)))

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

    @staticmethod
    def _cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
        if not vector_a or not vector_b or len(vector_a) != len(vector_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vector_a, vector_b))
        norm_a = math.sqrt(sum(a * a for a in vector_a))
        norm_b = math.sqrt(sum(b * b for b in vector_b))
        if norm_a <= 0 or norm_b <= 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _recency_score(self, created_at: str, half_life_days: float = 14.0) -> float:
        age_seconds = max(0.0, (self._now() - self._iso_to_datetime(created_at)).total_seconds())
        half_life_seconds = max(1.0, half_life_days * 86400.0)
        return 0.5 ** (age_seconds / half_life_seconds)

    def _player_and_character(self, player_id: int, character_instance_id: str):
        player = self.player_service.get_player_sync(int(player_id))
        if player is None:
            raise ValueError(f"Player {player_id} does not exist.")

        for character in getattr(player, "characters", []) or []:
            if str(getattr(character, "playerInstanceId", "") or "") == str(character_instance_id):
                return player, character

        raise ValueError(f"Character instance '{character_instance_id}' was not found for player {player_id}.")

    def list_player_main_characters(self, player_id: int) -> list[MainCharacter]:
        player = self.player_service.get_player_sync(int(player_id))
        if player is None:
            return []
        return [
            character
            for character in (getattr(player, "characters", []) or [])
            if isinstance(character, MainCharacter)
        ]

    def _coerce_scene_frame(self, scene_frame: dict[str, Any]) -> dict[str, Any]:
        frame = dict(scene_frame or {})
        participant_ids = frame.get("participant_ids") or []
        if not isinstance(participant_ids, list):
            participant_ids = []
        return {
            "location": str(frame.get("location", "") or "").strip(),
            "stakes": str(frame.get("stakes", "") or "").strip(),
            "sensory_details": str(frame.get("sensory_details", "") or "").strip(),
            "latest_utterance": str(frame.get("latest_utterance", "") or "").strip(),
            "prompt": str(frame.get("prompt", "") or "").strip(),
            "participant_ids": [str(item or "").strip() for item in participant_ids if str(item or "").strip()],
        }

    def _gear_highlights(self, character) -> list[str]:
        gear = getattr(character, "gear", None)
        if gear is None:
            return []
        highlights = []
        for item in gear.GetAllEquipped():
            if item is None:
                continue
            highlights.append(str(getattr(item, "name", "") or "Unknown Item"))
        return highlights[:8]

    def _relationship_snapshot(self, player_id: int, character_instance_id: str, visible_ids: list[str]) -> list[dict[str, Any]]:
        relationships = self.store.list_relationships_for_character(player_id, character_instance_id)
        result = []
        visible_lookup = set(visible_ids)
        for relationship in relationships:
            if visible_lookup and relationship.target_character_instance_id not in visible_lookup:
                continue
            result.append(
                {
                    "target_character_instance_id": relationship.target_character_instance_id,
                    "affinity": relationship.affinity,
                    "trust": relationship.trust,
                    "fear": relationship.fear,
                    "respect": relationship.respect,
                    "evidence_memory_ids": list(relationship.evidence_memory_ids),
                }
            )
        return result

    def _character_packet(self, character) -> dict[str, Any]:
        character_info = getattr(character, "characterInfo", None)
        llm_profile = getattr(character, "llmControlProfile", None)
        return {
            "name": str(getattr(character, "name", "") or ""),
            "playerInstanceId": str(getattr(character, "playerInstanceId", "") or ""),
            "description": str(getattr(character, "description", "") or ""),
            "race": str(getattr(character, "race", "Human1") or "Human1"),
            "raceTier": str(getattr(character, "raceTier", "Tier I") or "Tier I"),
            "level": int(getattr(character, "level", 0) or 0),
            "health": int(getattr(character, "health", 100) or 100),
            "healthState": getattr(getattr(character, "healthState", None), "name", str(getattr(character, "healthState", "HEALTHY"))),
            "activeAchievementTitle": str(getattr(character, "activeAchievementTitle", "") or ""),
            "achievements": [str(getattr(item, "name", "") or "") for item in (getattr(character, "achievements", []) or [])],
            "gearHighlights": self._gear_highlights(character),
            "characterInfo": character_info.to_dict() if hasattr(character_info, "to_dict") else {},
            "llmControlProfile": llm_profile.to_dict() if hasattr(llm_profile, "to_dict") else {},
        }

    def _derive_scene_tags(self, scene_frame: dict[str, Any], character) -> list[str]:
        tokens = []
        for key in ("location", "stakes", "sensory_details", "latest_utterance", "prompt"):
            tokens.append(str(scene_frame.get(key, "") or "").lower())
        character_info = getattr(character, "characterInfo", None)
        if character_info is not None:
            tokens.extend(
                [
                    str(getattr(character_info, "occupation", "") or "").lower(),
                    str(getattr(character_info, "goal", "") or "").lower(),
                    str(getattr(character_info, "background", "") or "").lower(),
                ]
            )
        combined = " ".join(tokens)
        tags = set()
        for word in self.HIGH_SIGNAL_KEYWORDS:
            if word in combined:
                tags.add(word)
        location = str(scene_frame.get("location", "") or "").strip().lower()
        if location:
            tags.add(location)
        return sorted(tags)

    def _memory_score(self, memory: CharacterMemory, query_embedding: list[float], visible_ids: list[str], relationship_ids: set[str]) -> float:
        similarity = self._cosine_similarity(query_embedding, memory.embedding)
        recency = self._recency_score(memory.created_at)
        importance = self._clamp(memory.importance, 0.0, 1.0)
        relationship_boost = 0.1 if any(tag in relationship_ids for tag in memory.tags) else 0.0
        participant_boost = 0.1 if any(visible_id.lower() in memory.summary.lower() for visible_id in visible_ids) else 0.0
        return (0.45 * similarity) + (0.25 * recency) + (0.20 * importance) + relationship_boost + participant_boost

    def _fact_score(self, fact: SemanticFact, query_embedding: list[float]) -> float:
        similarity = self._cosine_similarity(query_embedding, fact.embedding)
        confidence = self._clamp(fact.confidence, 0.0, 1.0)
        recency = self._recency_score(fact.created_at, half_life_days=45.0)
        return (0.55 * similarity) + (0.30 * confidence) + (0.15 * recency)

    def build_prompt_packet(self, player_id: int, character_instance_id: str, scene_frame: dict[str, Any]) -> dict[str, Any]:
        _player, character = self._player_and_character(player_id, character_instance_id)
        if not isinstance(character, MainCharacter):
            raise ValueError("Only MainCharacters participate in the memory system in v1.")

        scene = self._coerce_scene_frame(scene_frame)
        visible_ids = list(dict.fromkeys([character_instance_id] + scene["participant_ids"]))
        scene_tags = self._derive_scene_tags(scene, character)
        query_text = "\n".join(
            [
                scene.get("location", ""),
                scene.get("stakes", ""),
                scene.get("sensory_details", ""),
                scene.get("latest_utterance", ""),
                scene.get("prompt", ""),
                " ".join(scene_tags),
            ]
        ).strip()
        query_embedding = self.openai_service.embed_text(query_text or character.name)

        recent_memories = self.store.list_memories_for_character(player_id, character_instance_id, limit=75)
        tag_memories = self.store.list_memories_by_tags(player_id, character_instance_id, scene_tags, limit=40)
        memory_pool = {memory.memory_id: memory for memory in recent_memories}
        for memory in tag_memories:
            memory_pool[memory.memory_id] = memory
        relationship_ids = set(visible_ids)
        ranked_memories = sorted(
            memory_pool.values(),
            key=lambda memory: self._memory_score(memory, query_embedding, visible_ids, relationship_ids),
            reverse=True,
        )[:12]

        recent_facts = self.store.list_facts_for_character(player_id, character_instance_id, limit=75)
        tag_facts = self.store.list_facts_by_tags(player_id, character_instance_id, scene_tags, limit=40)
        fact_pool = {fact.fact_id: fact for fact in recent_facts}
        for fact in tag_facts:
            fact_pool[fact.fact_id] = fact
        ranked_facts = sorted(
            fact_pool.values(),
            key=lambda fact: self._fact_score(fact, query_embedding),
            reverse=True,
        )[:8]

        if ranked_memories:
            self.store.touch_memories(player_id, [memory.memory_id for memory in ranked_memories], utc_now_iso())

        return {
            "player_id": int(player_id),
            "character_sheet": self._character_packet(character),
            "scene_frame": scene,
            "relationship_snapshot": self._relationship_snapshot(player_id, character_instance_id, visible_ids),
            "recalled_memories": [
                {
                    "memory_id": memory.memory_id,
                    "summary": memory.summary,
                    "importance": memory.importance,
                    "tags": list(memory.tags),
                }
                for memory in ranked_memories
            ],
            "semantic_facts": [
                {
                    "fact_id": fact.fact_id,
                    "fact_text": fact.fact_text,
                    "confidence": fact.confidence,
                    "tags": list(fact.tags),
                }
                for fact in ranked_facts
            ],
            "do_not_know_constraints": [
                "Only use knowledge in this prompt packet and this character sheet.",
                str(getattr(getattr(character, "llmControlProfile", None), "knowledgeBoundaryNotes", "") or "").strip(),
            ],
        }

    def _event_importance(self, scene_tags: list[str], turn_result: TurnResponseModel) -> float:
        score = 0.25 + (0.1 * len(scene_tags))
        combined = f"{turn_result.spoken_text} {turn_result.action_summary}".lower()
        for keyword in self.HIGH_SIGNAL_KEYWORDS:
            if keyword in combined:
                score += 0.08
        if turn_result.relationship_deltas:
            score += 0.15
        return self._clamp(score, 0.1, 1.0)

    def _should_distill_memory(self, event: EventRecord, existing_memory_count: int) -> bool:
        if existing_memory_count == 0:
            return True
        if float(event.importance) >= 0.6:
            return True
        combined = f"{event.summary} {event.prompt} {event.latest_utterance}".lower()
        return any(keyword in combined for keyword in self.HIGH_SIGNAL_KEYWORDS)

    @staticmethod
    def _quantize_delta(raw_delta: float, importance: float) -> float:
        magnitude = abs(float(raw_delta))
        if magnitude < 0.1:
            return 0.0
        if magnitude < 0.35:
            base = 0.05
        elif magnitude < 0.7:
            base = 0.1
        else:
            base = 0.2
        scaled = base * max(0.5, min(1.5, float(importance) + 0.5))
        return scaled if raw_delta > 0 else -scaled

    def _apply_relationship_deltas(
        self,
        player_id: int,
        source_character_id: str,
        memory_id: int,
        importance: float,
        deltas,
    ) -> int:
        updated = 0
        for delta in deltas:
            target_id = str(delta.target_character_instance_id or "").strip()
            if not target_id or target_id == source_character_id:
                continue
            relationship = self.store.get_relationship(player_id, source_character_id, target_id)
            if relationship is None:
                relationship = Relationship(
                    player_id=player_id,
                    character_instance_id=source_character_id,
                    target_character_instance_id=target_id,
                )
            relationship.affinity = self._clamp(
                relationship.affinity + self._quantize_delta(delta.affinity_delta, importance), -1.0, 1.0
            )
            relationship.trust = self._clamp(
                relationship.trust + self._quantize_delta(delta.trust_delta, importance), -1.0, 1.0
            )
            relationship.fear = self._clamp(
                relationship.fear + self._quantize_delta(delta.fear_delta, importance), -1.0, 1.0
            )
            relationship.respect = self._clamp(
                relationship.respect + self._quantize_delta(delta.respect_delta, importance), -1.0, 1.0
            )
            evidence_ids = list(relationship.evidence_memory_ids)
            if int(memory_id) not in evidence_ids:
                evidence_ids.append(int(memory_id))
            relationship.evidence_memory_ids = evidence_ids[-20:]
            relationship.updated_at = utc_now_iso()
            self.store.upsert_relationship(relationship)
            updated += 1
        return updated

    def _insert_fact_candidates(self, player_id: int, character_instance_id: str, memory_id: int, distillation: MemoryDistillationModel) -> int:
        existing_fact_texts = {
            str(fact.fact_text or "").strip().lower()
            for fact in self.store.list_facts_for_character(player_id, character_instance_id, limit=200)
        }
        inserted = 0
        for candidate in distillation.fact_candidates:
            fact_text = str(candidate or "").strip()
            if not fact_text or fact_text.lower() in existing_fact_texts:
                continue
            fact = SemanticFact(
                player_id=int(player_id),
                fact_id=0,
                character_instance_id=str(character_instance_id),
                created_at=utc_now_iso(),
                fact_text=fact_text,
                confidence=max(0.4, min(1.0, distillation.importance)),
                tags=list(distillation.tags),
                source_memory_ids=[int(memory_id)],
                embedding=self.openai_service.embed_text(fact_text),
            )
            self.store.insert_fact(fact)
            inserted += 1
            existing_fact_texts.add(fact_text.lower())
        return inserted

    def _maybe_reflect(self, player_id: int, character_instance_id: str, character_packet: dict[str, Any], latest_importance: float) -> int:
        memory_count = self.store.count_memories_for_character(player_id, character_instance_id)
        should_reflect = latest_importance >= 0.85 or (memory_count > 0 and memory_count % 10 == 0)
        if not should_reflect:
            return 0

        recent_memories = self.store.list_memories_for_character(player_id, character_instance_id, limit=12)
        if not recent_memories:
            return 0

        reflection = self.openai_service.reflect(
            character_packet=character_packet,
            memories=[
                {
                    "summary": memory.summary,
                    "importance": memory.importance,
                    "tags": list(memory.tags),
                }
                for memory in recent_memories
            ],
        )

        existing_fact_texts = {
            str(fact.fact_text or "").strip().lower()
            for fact in self.store.list_facts_for_character(player_id, character_instance_id, limit=250)
        }
        inserted = 0
        for fact_text in list(reflection.insights) + list(reflection.facts):
            normalized = str(fact_text or "").strip()
            if not normalized or normalized.lower() in existing_fact_texts:
                continue
            fact = SemanticFact(
                player_id=int(player_id),
                fact_id=0,
                character_instance_id=str(character_instance_id),
                created_at=utc_now_iso(),
                fact_text=normalized,
                confidence=0.8,
                tags=list(reflection.tags),
                source_memory_ids=[memory.memory_id for memory in recent_memories[:4]],
                embedding=self.openai_service.embed_text(normalized),
            )
            self.store.insert_fact(fact)
            inserted += 1
            existing_fact_texts.add(normalized.lower())
        return inserted

    def generate_turn(self, player_id: int, character_instance_id: str, scene_frame: dict[str, Any]) -> dict[str, Any]:
        if not self.openai_service.is_configured():
            raise RuntimeError("OpenAI is not configured. Set OPENAI_API_KEY or OPEN_AI_API_KEY in .env.")

        player, character = self._player_and_character(player_id, character_instance_id)
        if not isinstance(character, MainCharacter):
            raise ValueError("Only MainCharacters participate in the memory system in v1.")

        prompt_packet = self.build_prompt_packet(player_id, character_instance_id, scene_frame)
        turn_result = self.openai_service.generate_turn(prompt_packet)
        scene = prompt_packet["scene_frame"]
        participant_ids = list(dict.fromkeys([character_instance_id] + list(scene.get("participant_ids", []))))
        scene_tags = self._normalize_tags(list(turn_result.scene_tags) + self._derive_scene_tags(scene, character))
        importance = self._event_importance(scene_tags, turn_result)

        event = EventRecord(
            player_id=int(player_id),
            event_id=0,
            created_at=utc_now_iso(),
            event_type="character_turn",
            summary=f"{character.name}: {turn_result.action_summary}",
            participants=participant_ids,
            tags=scene_tags,
            location=scene.get("location", ""),
            stakes=scene.get("stakes", ""),
            sensory_details=scene.get("sensory_details", ""),
            latest_utterance=scene.get("latest_utterance", ""),
            prompt=scene.get("prompt", ""),
            raw_payload={
                "turn": turn_result.model_dump(),
                "character_name": character.name,
            },
            importance=importance,
        )
        event = self.store.insert_event(event)

        memory_ids = []
        fact_count = 0
        relationship_updates = 0
        distilled_for = []
        for participant_id in participant_ids:
            try:
                _participant_player, participant_character = self._player_and_character(player_id, participant_id)
            except ValueError:
                continue
            if not isinstance(participant_character, MainCharacter):
                continue
            existing_memory_count = self.store.count_memories_for_character(player_id, participant_id)
            if participant_id != character_instance_id and not self._should_distill_memory(event, existing_memory_count):
                continue

            character_packet = self._character_packet(participant_character)
            distillation = self.openai_service.distill_memory(
                character_packet=character_packet,
                event_packet={
                    "event": {
                        "summary": event.summary,
                        "tags": list(event.tags),
                        "location": event.location,
                        "stakes": event.stakes,
                        "latest_utterance": event.latest_utterance,
                        "prompt": event.prompt,
                        "turn_output": turn_result.model_dump(),
                    }
                },
            )
            memory = CharacterMemory(
                player_id=int(player_id),
                memory_id=0,
                character_instance_id=str(participant_id),
                created_at=utc_now_iso(),
                summary=distillation.summary,
                importance=float(distillation.importance),
                tags=self._normalize_tags(list(distillation.tags) + list(event.tags)),
                event_ids=[event.event_id],
                embedding=self.openai_service.embed_text(distillation.summary),
            )
            memory = self.store.insert_memory(memory)
            memory_ids.append(memory.memory_id)
            fact_count += self._insert_fact_candidates(player_id, participant_id, memory.memory_id, distillation)
            relationship_updates += self._apply_relationship_deltas(
                player_id,
                participant_id,
                memory.memory_id,
                float(distillation.importance),
                distillation.relationship_deltas,
            )
            fact_count += self._maybe_reflect(
                player_id,
                participant_id,
                character_packet,
                float(distillation.importance),
            )
            distilled_for.append(str(participant_id))

        persisted_summary = (
            f"Event {event.event_id} stored for player {player_id}. "
            f"Memories created: {len(memory_ids)}. Facts added: {fact_count}. "
            f"Relationships updated: {relationship_updates}."
        )
        turn_log = LLMTurnLog(
            player_id=int(player_id),
            turn_id=0,
            character_instance_id=str(character_instance_id),
            created_at=utc_now_iso(),
            model=self.openai_service.turn_model,
            scene_frame=scene,
            prompt_packet=prompt_packet,
            output_payload=turn_result.model_dump(),
            persisted_summary=persisted_summary,
        )
        turn_log = self.store.insert_turn_log(turn_log)

        return {
            "spoken_text": turn_result.spoken_text,
            "action_summary": turn_result.action_summary,
            "event_id": event.event_id,
            "turn_id": turn_log.turn_id,
            "memory_ids": memory_ids,
            "facts_added": fact_count,
            "relationships_updated": relationship_updates,
            "distilled_for": distilled_for,
            "prompt_packet": prompt_packet,
            "turn_output": turn_result.model_dump(),
            "persisted_summary": persisted_summary,
            "player_name": getattr(player, "playerName", str(player_id)),
            "character_name": character.name,
        }

    def append_manual_event(
        self,
        player_id: int,
        participant_ids: list[str],
        summary: str,
        event_type: str = "external_event",
        tags: list[str] | None = None,
        location: str = "",
        stakes: str = "",
    ) -> EventRecord:
        event = EventRecord(
            player_id=int(player_id),
            event_id=0,
            created_at=utc_now_iso(),
            event_type=str(event_type or "external_event"),
            summary=str(summary or "").strip(),
            participants=[str(item or "").strip() for item in participant_ids if str(item or "").strip()],
            tags=self._normalize_tags(tags or []),
            location=str(location or ""),
            stakes=str(stakes or ""),
            raw_payload={},
            importance=0.5,
        )
        return self.store.insert_event(event)

    def build_character_snapshot(self, player_id: int, character_instance_id: str) -> dict[str, Any]:
        _player, character = self._player_and_character(player_id, character_instance_id)
        return {
            "character": self._character_packet(character),
            "events": [event.__dict__ for event in self.store.list_events_for_character(player_id, character_instance_id, limit=25)],
            "memories": [memory.__dict__ for memory in self.store.list_memories_for_character(player_id, character_instance_id, limit=25)],
            "facts": [fact.__dict__ for fact in self.store.list_facts_for_character(player_id, character_instance_id, limit=25)],
            "relationships": [relationship.__dict__ for relationship in self.store.list_relationships_for_character(player_id, character_instance_id)],
            "turn_logs": [turn_log.__dict__ for turn_log in self.store.list_turn_logs_for_character(player_id, character_instance_id, limit=10)],
        }

