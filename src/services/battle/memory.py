from __future__ import annotations

from src.domain.main_character import MainCharacter
from src.domain.combat.state import BattleState


class BattleMemoryMixin:
    def _append_memory_event(self, battle: BattleState, summary: str):
        if self.memory_service is None:
            return
        participant_ids = []
        for unit in battle.ally_units:
            character_id = str(getattr(unit, "character_instance_id", "") or "")
            if not character_id:
                continue
            source = self._player_source_character(battle.player_id, character_id)
            if isinstance(source, MainCharacter):
                participant_ids.append(character_id)
        if not participant_ids:
            return
        context_tags = [
            str(tag or "").strip().lower()
            for tag in getattr(getattr(battle, "encounter", None), "context_tags", []) or []
            if str(tag or "").strip()
        ]
        self.memory_service.append_manual_event(
            player_id=battle.player_id,
            participant_ids=participant_ids,
            summary=str(summary or "").strip(),
            event_type="combat_event",
            tags=["combat", battle.encounter.encounter_type.name.lower(), battle.encounter.terrain.lower(), *context_tags],
            location=battle.encounter.terrain,
            stakes=battle.encounter.objective_text,
        )
