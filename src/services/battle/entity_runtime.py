from __future__ import annotations

import math

from src.config.tuning import character_stat_factor
from src.domain.main_character import MainCharacter
from src.domain.character_util import NormalizeUnitDisplayName
from src.domain.combat.enums import BattleTeam
from src.domain.combat.state import BattleState
from src.domain.combat_timing import (
    ExertionLevel,
    initialize_runtime_fields,
    next_window_start,
    speed_factor_from_attributes,
    start_time_gap_seconds,
    stamina_limit_from_physical_stamina,
    stamina_regen_per_second_from_physical_stamina,
)
from src.domain.combat.units import EnemyStackState


class BattleEntityRuntimeMixin:
    def _active_allies(self, battle: BattleState) -> list:
        return [unit for unit in battle.ally_units if unit.alive]

    def _active_non_player_allies(self, battle: BattleState) -> list:
        return [unit for unit in battle.ally_units if unit.alive and not bool(getattr(unit, "is_player_owned", False))]

    def _active_enemies(self, battle: BattleState) -> list:
        return [unit for unit in battle.enemy_units if unit.alive] + [
            stack for stack in battle.enemy_stacks if stack.alive
        ]

    @staticmethod
    def _entity_name(entity) -> str:
        raw_name = str(getattr(entity, "name", "Entity") or "Entity")
        return NormalizeUnitDisplayName(raw_name) or raw_name

    @staticmethod
    def _entity_health(entity) -> float:
        return float(getattr(entity, "health", getattr(entity, "total_health", 0.0)) or 0.0)

    @staticmethod
    def _entity_max_health(entity) -> float:
        return float(getattr(entity, "max_health", 100.0) or 100.0)

    @staticmethod
    def _entity_lane_width(entity) -> int:
        return max(1, int(getattr(entity, "lane_width", 1) or 1))

    @staticmethod
    def _entity_count(entity) -> int:
        if isinstance(entity, EnemyStackState):
            return max(0, int(getattr(entity, "current_count", 0) or 0))
        return 1 if float(getattr(entity, "health", 0.0) or 0.0) > 0.0 else 0

    def _entity_attack_count(self, entity) -> int:
        if isinstance(entity, EnemyStackState):
            return max(1, min(4, math.ceil(entity.current_count / 2)))
        return 1

    @staticmethod
    def _entity_timeline_id(entity) -> str:
        return str(
            getattr(entity, "unit_id", getattr(entity, "stack_id", getattr(entity, "name", "entity"))) or "entity"
        )

    def _entity_speed(self, entity) -> float:
        return max(
            character_stat_factor("minimum_speed_factor", 0.1),
            speed_factor_from_attributes(
                getattr(entity, "physical_power", character_stat_factor("primary_stat_baseline", 5.0)),
                getattr(entity, "magic_power", character_stat_factor("primary_stat_baseline", 5.0)),
            ),
        )

    def _ensure_entity_runtime(self, entity, current_time: float = 0.0):
        physical_stamina = float(getattr(entity, "physical_stamina", 5.0) or 5.0)
        stamina_limit = float(stamina_limit_from_physical_stamina(physical_stamina))
        stamina_regen = float(stamina_regen_per_second_from_physical_stamina(physical_stamina))
        stamina_current = getattr(entity, "stamina_current", stamina_limit)
        stamina_last_update_time = getattr(entity, "stamina_last_update_time", current_time)
        next_action_time = getattr(entity, "next_action_time", 0.0)
        entity.speed = self._entity_speed(entity)
        initialize_runtime_fields(
            entity,
            stamina_limit=stamina_limit,
            stamina_regen_per_second=stamina_regen,
            stamina_current=stamina_current,
            stamina_last_update_time=stamina_last_update_time,
            next_action_time=next_action_time,
        )

    def _all_entities(self, battle: BattleState) -> list:
        return list(battle.ally_units) + list(battle.enemy_units) + list(battle.enemy_stacks)

    def _active_entities(self, battle: BattleState) -> list:
        return [entity for entity in self._all_entities(battle) if self._entity_health(entity) > 0.0]

    def _seed_initial_action_times(self, battle: BattleState):
        active_entities = self._active_entities(battle)
        if not active_entities:
            return
        for entity in active_entities:
            self._ensure_entity_runtime(entity, battle.battle_time_seconds)
        order = list(active_entities)
        self._rng.shuffle(order)
        gap = start_time_gap_seconds(len(order))
        window_start = next_window_start(battle.battle_time_seconds)
        for index, entity in enumerate(order):
            entity.next_action_time = window_start + (index * gap)
            entity.stamina_last_update_time = battle.battle_time_seconds
            entity.exertion_level = ExertionLevel.FRESH.name

    def _seed_new_entities_action_times(self, battle: BattleState, entities: list):
        arrivals = [entity for entity in entities if self._entity_health(entity) > 0.0]
        if not arrivals:
            return
        gap = start_time_gap_seconds(len(arrivals))
        window_start = next_window_start(battle.battle_time_seconds)
        for index, entity in enumerate(arrivals):
            self._ensure_entity_runtime(entity, battle.battle_time_seconds)
            entity.next_action_time = window_start + (index * gap)
            entity.stamina_last_update_time = battle.battle_time_seconds

    def _select_next_actor(self, battle: BattleState):
        active_entities = self._active_entities(battle)
        if not active_entities:
            return None
        for entity in active_entities:
            self._ensure_entity_runtime(entity, battle.battle_time_seconds)
        return min(
            active_entities,
            key=lambda entity: (
                float(getattr(entity, "next_action_time", 0.0) or 0.0),
                getattr(getattr(entity, "team", BattleTeam.ALLY), "name", "ALLY"),
                self._entity_timeline_id(entity),
            ),
        )

    def _player_source_character(self, player_id: int, character_instance_id: str):
        player = self.player_service.get_player_sync(player_id)
        if player is None:
            return None
        for character in getattr(player, "characters", []) or []:
            if str(getattr(character, "playerInstanceId", "") or "") == str(character_instance_id):
                return character
        return None

    def _tracked_main_character(self, battle: BattleState, entity) -> MainCharacter | None:
        if not bool(getattr(battle, "record_external_effects", True)):
            return None
        if getattr(entity, "team", BattleTeam.ALLY) != BattleTeam.ALLY:
            return None
        character_instance_id = str(getattr(entity, "character_instance_id", "") or "")
        if not character_instance_id:
            return None
        source = self._player_source_character(battle.player_id, character_instance_id)
        return source if isinstance(source, MainCharacter) else None

    def _template_character(self, template_character_id: str, race_id: str):
        if template_character_id:
            character = self.character_service.get_character(template_character_id)
            if character is not None:
                return character
        race = self.context.all_races.get(race_id)
        if race is not None:
            return getattr(race, "averageSpecimine", None)
        return None
