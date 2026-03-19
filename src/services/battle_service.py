
from __future__ import annotations

import copy
import math
import random
import re
from typing import Any

from src.config.tuning import battle_factor, battle_factor_int, character_stat_factor
from src.domain.Character import Character, HealthState
from src.domain.CharacterUtil import Attributes, EquipSlot, HitLocation, ItemType, PowerType
from src.domain.Items import Consumable, Gear, Item, Weapon
from src.domain.MainCharacter import MainCharacter
from src.domain.Mission import EliminationObjective, MissionObjective, MissionObjectiveStatus, MissionStatistics
from src.domain.Race import CreatureSize
from src.domain.Spells import Spell
from src.domain.combat_encounter import EncounterDefinition, EncounterEnemyEntry
from src.domain.combat_enums import (
    BattleOutcome,
    BattlePhase,
    BattleTeam,
    BattleTriggerType,
    CombatRole,
    CommanderStance,
    EncounterType,
    TargetPriority,
    TokenPolicy,
    lane_width_for_size,
)
from src.domain.combat_state import BattleExchangeSummary, BattleState, BattleTrigger, CommanderOrders
from src.domain.combat_timing import (
    ExertionLevel,
    accuracy_bonus_for_exertion,
    can_take_offensive_action,
    damage_multiplier_for_exertion,
    default_offensive_action_stamina_cost,
    defense_stat_penalty_for_exertion,
    exchange_duration_seconds,
    initialize_runtime_fields,
    next_window_start,
    schedule_next_action,
    speed_factor_from_attributes,
    spend_stamina,
    start_time_gap_seconds,
    stamina_damage_from_hit,
    stamina_limit_from_physical_stamina,
    stamina_regen_per_second_from_physical_stamina,
    sync_stamina,
)
from src.domain.combat_units import CombatUnitState, EnemyStackState
from src.services.battle_roster_builder import BattleRosterBuilder
from src.services.combat_loadout_service import select_active_character_weapon
from src.services.damage_calculator import DamageCalculator


class BattleService:
    HOURS_PER_EXCHANGE = 0.25
    STRATEGY_INJECTION_PATTERNS = (
        r"ignore\s+previous",
        r"system\s+prompt",
        r"developer\s+message",
        r"tool\s+call",
        r"jailbreak",
        r"assistant",
        r"chatgpt",
    )

    def __init__(
        self,
        context,
        player_service,
        item_service,
        spell_service,
        character_service,
        race_service,
        encounter_service,
        active_battle_store,
        damage_calculator: DamageCalculator | None = None,
        openai_service=None,
        memory_service=None,
    ):
        self.context = context
        self.player_service = player_service
        self.item_service = item_service
        self.spell_service = spell_service
        self.character_service = character_service
        self.race_service = race_service
        self.encounter_service = encounter_service
        self.store = active_battle_store
        self.damage_calculator = damage_calculator if damage_calculator is not None else DamageCalculator()
        self.openai_service = openai_service
        self.memory_service = memory_service
        self._rng = random.Random()
        self.roster_builder = BattleRosterBuilder(
            context=context,
            item_service=item_service,
            character_service=character_service,
            health_state_for_ratio=self._health_state_for_ratio,
        )

    def initialize(self):
        self.store.ensure_directory()
        if not hasattr(self.context, "active_battles"):
            self.context.active_battles = {}
        self.encounter_service.load_portal_templates()

    def get_active_battle(self, player_id: int) -> BattleState | None:
        player_id = int(player_id)
        cached = getattr(self.context, "active_battles", {}).get(player_id)
        if cached is not None:
            return cached
        payload = self.store.load_battle_file(player_id)
        if not isinstance(payload, dict):
            return None
        battle_payload = payload.get("battle_state", payload)
        try:
            battle = BattleState.from_dict(battle_payload)
        except Exception:
            return None
        if int(payload.get("format_version", 1) or 1) < 2:
            self._reset_battle_runtime_for_new_scheduler(battle)
        self.context.active_battles[player_id] = battle
        return battle

    def save_battle(self, battle: BattleState):
        self.store.save_battle_file(
            battle.player_id,
            {
                "format_version": 2,
                "battle_state": battle.to_dict(),
            },
        )
        self.context.active_battles[battle.player_id] = battle

    def clear_battle(self, player_id: int):
        player_id = int(player_id)
        self.store.delete_battle_file(player_id)
        getattr(self.context, "active_battles", {}).pop(player_id, None)

    def _reset_battle_runtime_for_new_scheduler(self, battle: BattleState):
        battle.battle_time_seconds = float(battle.exchange_count) * exchange_duration_seconds()
        for entity in self._all_entities(battle):
            self._ensure_entity_runtime(entity, battle.battle_time_seconds)
            entity.stamina_current = entity.stamina_limit
            entity.stamina_last_update_time = battle.battle_time_seconds
            entity.next_action_time = 0.0
            entity.exertion_level = ExertionLevel.FRESH.name
            entity.speed = speed_factor_from_attributes(
                getattr(entity, "physical_power", 5.0),
                getattr(entity, "magic_power", 5.0),
            )
        self._seed_initial_action_times(battle)

    def _default_objective_for_encounter(self, encounter: EncounterDefinition) -> MissionObjective:
        return EliminationObjective(requiredEliminationFraction=1.0)

    def start_or_resume_battle(self, player_id: int, encounter_type: EncounterType) -> tuple[BattleState, bool]:
        existing = self.get_active_battle(player_id)
        if existing is not None and existing.phase != BattlePhase.RESOLVED:
            return existing, True

        player = self.player_service.get_player_sync(player_id)
        if player is None:
            raise ValueError(f"Player {player_id} does not exist.")

        if encounter_type == EncounterType.SCAVENGING:
            encounter = self.encounter_service.create_scavenging_encounter(player)
            mission_menu_name = "scavengingMissionAction"
        else:
            encounter = self.encounter_service.create_portal_encounter(player)
            mission_menu_name = "portalMissionAction"

        battle = self._build_battle_from_encounter(
            player,
            encounter,
            mission_menu_name,
            mission_name=encounter.name,
            mission_objective=self._default_objective_for_encounter(encounter),
        )
        self.save_battle(battle)
        self._append_memory_event(battle, f"{battle.encounter.name} begins.")
        return battle, False

    def _build_battle_from_encounter(
        self,
        player,
        encounter: EncounterDefinition,
        mission_menu_name: str,
        mission_id: str = "",
        mission_name: str = "",
        mission_objective: MissionObjective | None = None,
        mission_statistics: MissionStatistics | None = None,
    ) -> BattleState:
        ally_units = self._build_ally_units(player)
        if not ally_units:
            raise ValueError("No characters are selected in the player's mission party.")

        enemy_units: list[CombatUnitState] = []
        enemy_stacks: list[EnemyStackState] = []
        for entry in encounter.enemy_entries:
            spawned_units, spawned_stacks = self._spawn_enemy_entry(entry)
            enemy_units.extend(spawned_units)
            enemy_stacks.extend(spawned_stacks)

        total_lines = max(4, int(encounter.total_lines))
        player_front = max(0, min(total_lines - 2, int(encounter.player_front_line)))
        enemy_front = max(player_front + 1, min(total_lines - 1, int(encounter.enemy_front_line)))

        objective = mission_objective if mission_objective is not None else self._default_objective_for_encounter(encounter)
        stats = mission_statistics if mission_statistics is not None else MissionStatistics()
        battle = BattleState(
            player_id=int(player.discordID),
            battle_id=f"{encounter.encounter_type.name.lower()}_{int(player.discordID)}",
            encounter=encounter,
            phase=BattlePhase.ORDERS,
            outcome=BattleOutcome.ONGOING,
            width=max(1, int(encounter.width)),
            total_lines=total_lines,
            player_front_line=player_front,
            enemy_front_line=enemy_front,
            default_player_front_line=total_lines // 2,
            default_enemy_front_line=(total_lines // 2) + 1,
            ally_units=ally_units,
            enemy_units=enemy_units,
            enemy_stacks=enemy_stacks,
            orders=CommanderOrders(),
            mission_menu_name=mission_menu_name,
            mission_id=str(mission_id or ""),
            mission_name=str(mission_name or encounter.name or "Mission"),
            mission_objective=objective,
            mission_statistics=stats,
            mission_objective_status=MissionObjectiveStatus.IN_PROGRESS,
        )
        self._solve_formations(battle)
        self._initialize_mission_statistics(battle)
        self._refresh_mission_state(battle, mission_complete=False)
        return battle

    def _party_members(self, player) -> list:
        return self.roster_builder.party_members(player)

    def _build_ally_units(self, player) -> list[CombatUnitState]:
        return self.roster_builder.build_ally_units(player)

    def _spawn_enemy_entry(self, entry: EncounterEnemyEntry) -> tuple[list[CombatUnitState], list[EnemyStackState]]:
        return self.roster_builder.spawn_enemy_entry(entry)

    def _resolve_item_id(self, item) -> str:
        return self.roster_builder.resolve_item_id(item)

    def _race_lookup(self, race_id: str):
        return self.roster_builder.race_lookup(race_id)

    def _resolve_size_for_character(self, character) -> CreatureSize:
        return self.roster_builder.resolve_size_for_character(character)

    def _extract_direct_damage_spells(self, character) -> list[str]:
        return self.roster_builder.extract_direct_damage_spells(character)

    def _infer_role(self, character) -> CombatRole:
        return self.roster_builder.infer_role(character)

    def _character_to_unit(
        self,
        character,
        team: BattleTeam,
        unit_id: str,
        character_instance_id: str = "",
        template_character_id: str = "",
        name_override: str = "",
        notable: bool = True,
        is_player_owned: bool = False,
        is_boss: bool = False,
        is_elite: bool = False,
    ) -> CombatUnitState:
        return self.roster_builder.character_to_unit(
            character=character,
            team=team,
            unit_id=unit_id,
            character_instance_id=character_instance_id,
            template_character_id=template_character_id,
            name_override=name_override,
            notable=notable,
            is_player_owned=is_player_owned,
            is_boss=is_boss,
            is_elite=is_elite,
        )

    def _character_to_stack(
        self,
        character,
        count: int,
        stack_id: str,
        template_character_id: str,
        race_id: str,
        name_override: str,
    ) -> EnemyStackState:
        return self.roster_builder.character_to_stack(
            character=character,
            count=count,
            stack_id=stack_id,
            template_character_id=template_character_id,
            race_id=race_id,
            name_override=name_override,
        )
    def _active_allies(self, battle: BattleState) -> list:
        return [unit for unit in battle.ally_units if unit.alive]

    def _active_non_player_allies(self, battle: BattleState) -> list:
        return [unit for unit in battle.ally_units if unit.alive and not bool(getattr(unit, "is_player_owned", False))]

    def _active_enemies(self, battle: BattleState) -> list:
        return [unit for unit in battle.enemy_units if unit.alive] + [stack for stack in battle.enemy_stacks if stack.alive]

    @staticmethod
    def _entity_name(entity) -> str:
        return str(getattr(entity, "name", "Entity") or "Entity")

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
        return str(getattr(entity, "unit_id", getattr(entity, "stack_id", getattr(entity, "name", "entity"))) or "entity")

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

    def _capture_starting_positions(self, battle: BattleState):
        for entity in list(battle.ally_units) + list(battle.enemy_units) + list(battle.enemy_stacks):
            entity.starting_line = int(getattr(entity, "line", 0) or 0)

    def _count_remaining_enemies(self, battle: BattleState) -> int:
        total = 0
        for entity in list(battle.enemy_units) + list(battle.enemy_stacks):
            total += self._entity_count(entity)
        return total

    def _count_non_player_allies_remaining(self, battle: BattleState) -> int:
        return sum(1 for entity in battle.ally_units if entity.alive and not bool(getattr(entity, "is_player_owned", False)))

    def _initialize_mission_statistics(self, battle: BattleState):
        battle.mission_statistics.totalStartingEnemies = sum(
            1 for entity in battle.enemy_units if entity.alive
        ) + sum(max(0, int(getattr(stack, "max_count", 0) or 0)) for stack in battle.enemy_stacks)
        battle.mission_statistics.totalStartingAllies = sum(
            1 for entity in battle.ally_units if not bool(getattr(entity, "is_player_owned", False))
        )
        battle.mission_statistics.enemiesRemaining = self._count_remaining_enemies(battle)
        battle.mission_statistics.alliesRemaining = self._count_non_player_allies_remaining(battle)
        battle.mission_statistics.timeInsideMissionHours = float(battle.exchange_count) * battle_factor("hours_per_exchange", self.HOURS_PER_EXCHANGE)
        self._capture_starting_positions(battle)

    def _refresh_dynamic_mission_statistics(self, battle: BattleState):
        stats = battle.mission_statistics
        stats.enemiesRemaining = self._count_remaining_enemies(battle)
        stats.alliesRemaining = self._count_non_player_allies_remaining(battle)
        stats.timeInsideMissionHours = float(battle.exchange_count) * battle_factor("hours_per_exchange", self.HOURS_PER_EXCHANGE)
        for entity in battle.ally_units:
            if bool(getattr(entity, "is_player_owned", False)):
                continue
            unit_id = str(getattr(entity, "unit_id", "") or "")
            if not unit_id:
                continue
            stats.unitAliveStates[unit_id] = bool(entity.alive)
            stats.unitDistancesMoved[unit_id] = max(
                stats.unitDistancesMoved.get(unit_id, 0.0),
                float(abs(int(getattr(entity, "line", 0) or 0) - int(getattr(entity, "starting_line", 0) or 0))),
            )
        if stats.startingImportantObjects > 0 and stats.importantObjectsRemaining <= 0:
            stats.importantObjectsRemaining = 0

    def _refresh_mission_state(self, battle: BattleState, mission_complete: bool):
        self._refresh_dynamic_mission_statistics(battle)
        status = battle.mission_objective.evaluate(battle.mission_statistics, mission_complete=mission_complete)
        battle.mission_objective_status = status
        if battle.phase != BattlePhase.RESOLVED:
            if status == MissionObjectiveStatus.SUCCESS:
                battle.phase = BattlePhase.RESOLVED
                battle.outcome = BattleOutcome.VICTORY
                battle.result_summary = f"Mission success: {battle.mission_objective.describe()}."
            elif status == MissionObjectiveStatus.FAILURE:
                battle.phase = BattlePhase.RESOLVED
                battle.outcome = BattleOutcome.DEFEAT
                battle.result_summary = f"Mission failed: {battle.mission_objective.describe()}."
        elif status == MissionObjectiveStatus.SUCCESS and battle.outcome != BattleOutcome.DEFEAT:
            battle.outcome = BattleOutcome.VICTORY
            battle.result_summary = battle.result_summary or f"Mission success: {battle.mission_objective.describe()}."
        elif mission_complete and status == MissionObjectiveStatus.FAILURE:
            if battle.outcome != BattleOutcome.RETREAT:
                battle.outcome = BattleOutcome.DEFEAT
            battle.result_summary = f"Mission failed: {battle.mission_objective.describe()}."

    def record_units_recruited(self, battle: BattleState, count: int):
        battle.mission_statistics.unitsRecruited += max(0, int(count or 0))
        self._refresh_mission_state(battle, mission_complete=False)
        self.save_battle(battle)

    def record_resources_gathered(self, battle: BattleState, amount: int):
        battle.mission_statistics.basicResourcesGathered += max(0, int(amount or 0))
        self._refresh_mission_state(battle, mission_complete=False)
        self.save_battle(battle)

    def record_package_delivery(self, battle: BattleState, item_id: str, allegiance_id: str, count: int = 1):
        delivered_count = max(0, int(count or 0))
        if delivered_count <= 0:
            return
        stats = battle.mission_statistics
        stats.packagesDelivered += delivered_count
        composite_key = f"{str(item_id or '').strip()}|{str(allegiance_id or '').strip()}"
        stats.deliveredPackageCounts[composite_key] = stats.deliveredPackageCounts.get(composite_key, 0) + delivered_count
        self._refresh_mission_state(battle, mission_complete=False)
        self.save_battle(battle)

    def set_important_object_counts(self, battle: BattleState, starting_count: int, remaining_count: int | None = None):
        stats = battle.mission_statistics
        stats.startingImportantObjects = max(0, int(starting_count or 0))
        stats.importantObjectsRemaining = max(0, int(remaining_count if remaining_count is not None else starting_count or 0))
        self._refresh_mission_state(battle, mission_complete=False)
        self.save_battle(battle)

    def record_ally_escape_progress(self, battle: BattleState, unit_id: str, distance: float, alive: bool = True):
        key = str(unit_id or '').strip()
        if not key:
            return
        battle.mission_statistics.unitDistancesMoved[key] = max(
            battle.mission_statistics.unitDistancesMoved.get(key, 0.0),
            max(0.0, float(distance or 0.0)),
        )
        battle.mission_statistics.unitAliveStates[key] = bool(alive)
        self._refresh_mission_state(battle, mission_complete=False)
        self.save_battle(battle)

    def _character_snapshot_for_entity(self, battle: BattleState, entity) -> Character:
        if getattr(entity, "team", BattleTeam.ALLY) == BattleTeam.ALLY and getattr(entity, "character_instance_id", ""):
            source = self._player_source_character(battle.player_id, getattr(entity, "character_instance_id", ""))
        else:
            source = self._template_character(
                getattr(entity, "template_character_id", ""),
                getattr(entity, "race_id", "Human1"),
            )
        if source is None:
            source = Character(name=self._entity_name(entity), attributes=Attributes())
        snapshot = copy.deepcopy(source)
        snapshot.health = int(max(0.0, self._entity_health(entity)))
        state_name = self._normalize_health_state_name(getattr(entity, "health_state", "HEALTHY"))
        snapshot.healthState = HealthState[state_name]
        if hasattr(snapshot, "CalculateBonus"):
            snapshot.CalculateBonus()
        return snapshot

    @staticmethod
    def _normalize_health_state_name(value: str) -> str:
        text = str(value or "HEALTHY").upper().strip()
        return text if text in HealthState.__members__ else "HEALTHY"

    def _default_unarmed_weapon(self) -> Weapon:
        return Weapon(
            name="Unarmed Strike",
            slot=EquipSlot.PRIMARY_WEAPON,
            tier=0,
            durability=100,
            itemType=ItemType.MELEE_WEAPON,
            damageType=[],
            damageMin=4.0,
            damageMax=6.0,
            armorMultiplier=0.7,
            ignoreArmorFraction=0.0,
            penetrationBase=2.0,
            staminaCost=default_offensive_action_stamina_cost(),
            itemId="UNARMED",
        )

    def _weapon_for_entity(self, entity) -> Weapon:
        primary = self.item_service.get_weapon_by_id(str(getattr(entity, "primary_weapon_item_id", "") or ""))
        if primary is not None:
            return primary
        offhand = self.item_service.get_weapon_by_id(str(getattr(entity, "offhand_item_id", "") or ""))
        if offhand is not None:
            return offhand
        return self._default_unarmed_weapon()

    def _spell_for_entity(self, entity) -> Spell | None:
        best_spell = None
        best_power = 0.0
        for name in getattr(entity, "spell_names", []) or []:
            spell = self.spell_service.get_spell(str(name))
            if spell is None:
                continue
            try:
                power = float(getattr(spell, "power", 0) or 0)
            except Exception:
                power = 0.0
            if power > best_power:
                best_power = power
                best_spell = spell
        return best_spell

    def _set_entity_health(self, entity, health: float):
        health = max(0.0, float(health))
        if isinstance(entity, EnemyStackState):
            entity.total_health = health
        else:
            entity.health = health
        entity.health_state = self._health_state_for_ratio(health, self._entity_max_health(entity)).name

    @staticmethod
    def _health_state_for_ratio(health: float, max_health: float) -> HealthState:
        if health <= 0:
            return HealthState.UNCONSCIOUS
        percent = (float(health) / max(1.0, float(max_health))) * 100.0
        if percent >= character_stat_factor("healthy_health_ratio_threshold", 0.76) * 100.0:
            return HealthState.HEALTHY
        if percent >= character_stat_factor("injured_health_ratio_threshold", 0.51) * 100.0:
            return HealthState.INJURED
        if percent >= character_stat_factor("heavily_injured_health_ratio_threshold", 0.26) * 100.0:
            return HealthState.HEAVILY_INJURED
        return HealthState.DYING

    def _apply_damage(self, entity, amount: float) -> float:
        before = self._entity_health(entity)
        after = max(0.0, before - max(0.0, float(amount)))
        self._set_entity_health(entity, after)
        return before - after

    def _apply_damage_with_result(self, entity, amount: float) -> dict[str, Any]:
        before_health = self._entity_health(entity)
        before_count = self._entity_count(entity)
        actual_damage = self._apply_damage(entity, amount)
        after_count = self._entity_count(entity)
        return {
            "damage": actual_damage,
            "defeated_units": max(0, before_count - after_count),
            "target_down": before_health > 0.0 and self._entity_health(entity) <= 0.0,
        }

    def _heal_entity(self, entity, amount: float) -> float:
        before = self._entity_health(entity)
        after = min(self._entity_max_health(entity), before + max(0.0, float(amount)))
        self._set_entity_health(entity, after)
        return after - before

    def _record_damage_taken(self, battle: BattleState, entity, amount: float):
        target = self._tracked_main_character(battle, entity)
        if target is None:
            return
        target.stats.record_damage_taken(amount)

    def _record_damage_done(self, battle: BattleState, entity, amount: float):
        attacker = self._tracked_main_character(battle, entity)
        if attacker is None:
            return
        attacker.stats.record_damage_done(amount)

    def _record_spell_cast(self, battle: BattleState, entity):
        attacker = self._tracked_main_character(battle, entity)
        if attacker is None:
            return
        attacker.stats.record_spell_cast()

    def _record_kill(self, battle: BattleState, attacker_entity, target_entity, count: int):
        attacker = self._tracked_main_character(battle, attacker_entity)
        if attacker is None:
            return
        is_boss = bool(getattr(target_entity, "is_boss", False))
        is_elite = bool(getattr(target_entity, "is_elite", False))
        attacker.stats.record_kill(self._entity_name(target_entity), count=count, is_boss=is_boss, is_elite=is_elite)
        if is_boss:
            battle.mission_statistics.bossesDefeated += count

    def _lane_distance(self, attacker, target) -> int:
        attacker_mid = getattr(attacker, "lane_start", 0) + (self._entity_lane_width(attacker) - 1) / 2.0
        target_mid = getattr(target, "lane_start", 0) + (self._entity_lane_width(target) - 1) / 2.0
        return int(abs(attacker_mid - target_mid))

    def _line_distance(self, attacker, target) -> int:
        return abs(int(getattr(attacker, "line", 0)) - int(getattr(target, "line", 0)))

    def _frontline_targets(self, battle: BattleState, team: BattleTeam) -> list:
        if team == BattleTeam.ALLY:
            return [entity for entity in self._active_enemies(battle) if int(getattr(entity, "line", 0)) == battle.enemy_front_line]
        return [entity for entity in self._active_allies(battle) if int(getattr(entity, "line", 0)) == battle.player_front_line]

    def _select_target(self, battle: BattleState, attacker, candidates: list, orders: CommanderOrders | None = None):
        if not candidates or attacker is None:
            return None
        priority = orders.target_priority if orders is not None else TargetPriority.FRONTLINE
        alive = [candidate for candidate in candidates if self._entity_health(candidate) > 0.0]
        if not alive:
            return None

        def common_key(candidate):
            role_rank = 2
            if getattr(candidate, "role", CombatRole.FRONTLINE) == CombatRole.FRONTLINE:
                role_rank = 0
            elif getattr(candidate, "role", CombatRole.FRONTLINE) == CombatRole.RANGED:
                role_rank = 1
            health_ratio = self._entity_health(candidate) / max(1.0, self._entity_max_health(candidate))
            return (role_rank, health_ratio, self._line_distance(attacker, candidate), self._lane_distance(attacker, candidate), self._entity_name(candidate))

        if priority == TargetPriority.WEAKEST:
            return min(alive, key=lambda candidate: (self._entity_health(candidate) / max(1.0, self._entity_max_health(candidate)), self._line_distance(attacker, candidate), self._lane_distance(attacker, candidate)))
        if priority == TargetPriority.STRONGEST:
            return max(alive, key=lambda candidate: (self._entity_health(candidate), -self._line_distance(attacker, candidate), -self._lane_distance(attacker, candidate)))
        if priority == TargetPriority.SUPPORT:
            return sorted(alive, key=lambda candidate: (getattr(candidate, "role", CombatRole.FRONTLINE) != CombatRole.SUPPORT, common_key(candidate)))[0]
        if priority == TargetPriority.RANGED:
            return sorted(alive, key=lambda candidate: (getattr(candidate, "role", CombatRole.FRONTLINE) != CombatRole.RANGED, common_key(candidate)))[0]
        close = [candidate for candidate in alive if self._line_distance(attacker, candidate) <= 1]
        return sorted(close or alive, key=common_key)[0]

    def _stance_attack_bonus(self, orders: CommanderOrders | None) -> float:
        if orders is None:
            return 0.0
        if orders.stance == CommanderStance.ADVANCE:
            return battle_factor("stance_advance_attack_bonus", 0.03)
        if orders.stance == CommanderStance.AGGRESSIVE:
            return battle_factor("stance_aggressive_attack_bonus", 0.05)
        if orders.stance == CommanderStance.DEFENSIVE:
            return battle_factor("stance_defensive_attack_bonus", -0.03)
        return 0.0

    def _ranged_penalties(self, battle: BattleState, attacker, target) -> tuple[float, float, float]:
        congestion_penalty = battle_factor("ranged_congestion_penalty", 0.05) if self._entity_lane_width(attacker) > 1 else 0.0
        line_distance = self._line_distance(attacker, target)
        range_penalty = max(0.0, battle_factor("ranged_range_penalty_per_line", 0.05) * max(0, line_distance - 1))
        firing_penalty = 0.0
        if getattr(attacker, "role", CombatRole.FRONTLINE) != CombatRole.FRONTLINE:
            frontline_enemy = self._frontline_targets(battle, getattr(attacker, "team", BattleTeam.ALLY))
            if any(self._lane_distance(attacker, enemy) == 0 for enemy in frontline_enemy):
                firing_penalty = battle_factor("ranged_firing_through_engagement_penalty", 0.1)
        return congestion_penalty, firing_penalty, range_penalty

    def _resolve_attack(
        self,
        battle: BattleState,
        attacker,
        target,
        orders: CommanderOrders | None,
        highlights: list[str],
        current_time: float | None = None,
    ) -> bool:
        if target is None or self._entity_health(target) <= 0.0 or self._entity_health(attacker) <= 0.0:
            return False
        current_time = battle.battle_time_seconds if current_time is None else float(current_time)
        self._ensure_entity_runtime(attacker, current_time)
        self._ensure_entity_runtime(target, current_time)
        sync_stamina(attacker, current_time)
        sync_stamina(target, current_time)
        if not can_take_offensive_action(getattr(attacker, "exertion_level", ExertionLevel.FRESH.name)):
            return False
        attacker_character = self._character_snapshot_for_entity(battle, attacker)
        defender_character = self._character_snapshot_for_entity(battle, target)
        attack_bonus = self._stance_attack_bonus(orders) + accuracy_bonus_for_exertion(getattr(attacker, "exertion_level", ExertionLevel.FRESH.name))
        if orders is not None:
            attack_bonus += float(orders.lane_discipline_modifier)
        congestion_penalty, firing_penalty, range_penalty = self._ranged_penalties(battle, attacker, target)

        weapon = select_active_character_weapon(attacker_character, race_lookup=self._race_lookup) or self._default_unarmed_weapon()
        spell = self._spell_for_entity(attacker)
        use_spell = False
        if spell is not None:
            try:
                use_spell = (
                    getattr(attacker, "role", CombatRole.FRONTLINE) != CombatRole.FRONTLINE
                    or float(getattr(spell, "power", 0) or 0) >= float(getattr(weapon, "damageMax", 0) or 0)
                )
            except Exception:
                use_spell = False

        if use_spell:
            self._record_spell_cast(battle, attacker)
            defender_magic_resistance = max(
                0.0,
                float(getattr(target, "magic_resistance", 5.0))
                - defense_stat_penalty_for_exertion(getattr(target, "exertion_level", ExertionLevel.FRESH.name)),
            )
            hit, hit_chance = self.damage_calculator.roll_hit(
                attacker_stat=float(getattr(attacker, "magic_power", 5.0)),
                defender_stat=defender_magic_resistance,
                congestion_penalty=congestion_penalty,
                firing_through_engagement_penalty=firing_penalty,
                range_penalty=range_penalty,
                bonus=attack_bonus,
            )
            breakdown = self.damage_calculator.calculate_magic_hit(
                attacker=attacker_character,
                defender=defender_character,
                spell_power=float(getattr(spell, "power", 0) or 0) * damage_multiplier_for_exertion(getattr(attacker, "exertion_level", ExertionLevel.FRESH.name)),
                hit_chance=hit_chance,
                did_hit=hit,
            )
            damage = breakdown.hpFinal if hit else 0.0
            if damage > 0:
                damage_result = self._apply_damage_with_result(target, damage)
                spend_stamina(target, stamina_damage_from_hit(damage_result["damage"]), current_time)
                self._record_damage_done(battle, attacker, damage_result["damage"])
                self._record_damage_taken(battle, target, damage_result["damage"])
                if damage_result["defeated_units"] > 0:
                    self._record_kill(battle, attacker, target, damage_result["defeated_units"])
                highlights.append(f"{self._entity_name(attacker)} blasts {self._entity_name(target)} for {damage_result['damage']:.1f} damage.")
            else:
                highlights.append(f"{self._entity_name(attacker)} misses {self._entity_name(target)} with {getattr(spell, 'name', 'a spell')}.")
            return True

        hit, _hit_chance = self.damage_calculator.roll_hit(
            attacker_stat=float(getattr(attacker, "physical_power", 5.0)),
            defender_stat=max(
                0.0,
                float(getattr(target, "physical_resistance", 5.0))
                - defense_stat_penalty_for_exertion(getattr(target, "exertion_level", ExertionLevel.FRESH.name)),
            ),
            congestion_penalty=congestion_penalty,
            firing_through_engagement_penalty=firing_penalty,
            range_penalty=range_penalty,
            bonus=attack_bonus,
        )
        if not hit:
            highlights.append(f"{self._entity_name(attacker)} misses {self._entity_name(target)}.")
            return True
        scaled_weapon = self._scaled_weapon_for_damage_multiplier(
            weapon,
            damage_multiplier_for_exertion(getattr(attacker, "exertion_level", ExertionLevel.FRESH.name)),
        )
        result = self.damage_calculator.calculate_physical_hit_to_location(
            attacker=attacker_character,
            defender=defender_character,
            weapon=scaled_weapon,
            location=HitLocation.BODY,
            applyArmorDamageToGear=False,
        )
        damage = max(0.0, result.hpFinal)
        if damage > 0:
            damage_result = self._apply_damage_with_result(target, damage)
            spend_stamina(target, stamina_damage_from_hit(damage_result["damage"]), current_time)
            self._record_damage_done(battle, attacker, damage_result["damage"])
            self._record_damage_taken(battle, target, damage_result["damage"])
            if damage_result["defeated_units"] > 0:
                self._record_kill(battle, attacker, target, damage_result["defeated_units"])
            highlights.append(f"{self._entity_name(attacker)} hits {self._entity_name(target)} for {damage_result['damage']:.1f} damage.")
        else:
            highlights.append(f"{self._entity_name(attacker)} fails to injure {self._entity_name(target)}.")
        return True

    @staticmethod
    def _scaled_weapon_for_damage_multiplier(weapon: Weapon, damage_multiplier: float) -> Weapon:
        if abs(float(damage_multiplier) - 1.0) < 0.0001:
            return weapon
        scaled_weapon = copy.deepcopy(weapon)
        scaled_weapon.damageMin = max(0.0, float(getattr(weapon, "damageMin", 0.0) or 0.0) * float(damage_multiplier))
        scaled_weapon.damageMax = max(scaled_weapon.damageMin, float(getattr(weapon, "damageMax", scaled_weapon.damageMin) or scaled_weapon.damageMin) * float(damage_multiplier))
        return scaled_weapon

    def _offensive_action_cost(self, battle: BattleState, attacker) -> float:
        attacker_character = self._character_snapshot_for_entity(battle, attacker)
        weapon = select_active_character_weapon(attacker_character, race_lookup=self._race_lookup) or self._default_unarmed_weapon()
        spell = self._spell_for_entity(attacker)
        if spell is not None:
            try:
                if (
                    getattr(attacker, "role", CombatRole.FRONTLINE) != CombatRole.FRONTLINE
                    or float(getattr(spell, "power", 0) or 0) >= float(getattr(weapon, "damageMax", 0) or 0)
                ):
                    return default_offensive_action_stamina_cost()
            except Exception:
                pass
        return max(0.0, float(getattr(weapon, "staminaCost", default_offensive_action_stamina_cost()) or default_offensive_action_stamina_cost()))

    def _timeline_needs_seeding(self, battle: BattleState) -> bool:
        active_entities = self._active_entities(battle)
        return bool(active_entities) and all(float(getattr(entity, "next_action_time", 0.0) or 0.0) == 0.0 for entity in active_entities)

    def _execute_actor_turn(self, battle: BattleState, attacker, highlights: list[str]):
        if self._entity_health(attacker) <= 0.0:
            return
        current_time = battle.battle_time_seconds
        self._ensure_entity_runtime(attacker, current_time)
        sync_stamina(attacker, current_time)
        if not can_take_offensive_action(getattr(attacker, "exertion_level", ExertionLevel.FRESH.name)):
            highlights.append(f"{self._entity_name(attacker)} is exhausted and cannot press the attack.")
            schedule_next_action(attacker, self._entity_speed(attacker), current_time)
            return

        defenders = self._active_enemies(battle) if getattr(attacker, "team", BattleTeam.ALLY) == BattleTeam.ALLY else self._active_allies(battle)
        orders = battle.orders if getattr(attacker, "team", BattleTeam.ALLY) == BattleTeam.ALLY else None
        live_defenders = [entity for entity in defenders if self._entity_health(entity) > 0.0]
        action_attempted = False
        attack_count = self._entity_attack_count(attacker)
        for _ in range(attack_count):
            if not live_defenders:
                break
            target = self._select_target(battle, attacker, live_defenders, orders)
            if target is None:
                break
            action_attempted = self._resolve_attack(
                battle,
                attacker,
                target,
                orders,
                highlights,
                current_time=current_time,
            ) or action_attempted
            live_defenders = [entity for entity in defenders if self._entity_health(entity) > 0.0]
        if action_attempted:
            spend_stamina(attacker, self._offensive_action_cost(battle, attacker), current_time)
        schedule_next_action(attacker, self._entity_speed(attacker), current_time)

    def _resolve_team_attacks(self, battle: BattleState, attackers: list, defenders: list, orders: CommanderOrders | None, highlights: list[str]):
        for attacker in attackers:
            if self._entity_health(attacker) <= 0.0:
                continue
            attack_count = self._entity_attack_count(attacker)
            live_defenders = [entity for entity in defenders if self._entity_health(entity) > 0.0]
            for _ in range(attack_count):
                if not live_defenders:
                    return
                target = self._select_target(battle, attacker, live_defenders, orders)
                if target is None:
                    break
                self._resolve_attack(battle, attacker, target, orders, highlights)
                live_defenders = [entity for entity in defenders if self._entity_health(entity) > 0.0]

    def _frontline_group(self, entities: list) -> list:
        return [entity for entity in entities if getattr(entity, "role", CombatRole.FRONTLINE) == CombatRole.FRONTLINE]

    def _ranged_group(self, entities: list) -> list:
        return [entity for entity in entities if getattr(entity, "role", CombatRole.FRONTLINE) != CombatRole.FRONTLINE]
    def _effective_width(self, battle: BattleState, team: BattleTeam) -> int:
        width = int(battle.width)
        if team == BattleTeam.ALLY and battle.orders.width_control_bonus > 0:
            width += min(1, int(battle.orders.width_control_bonus))
        return max(1, width)

    def _solve_formations(self, battle: BattleState):
        self._assign_team_positions(
            entities=self._active_allies(battle),
            team=BattleTeam.ALLY,
            front_line=battle.player_front_line,
            total_lines=battle.total_lines,
            width=self._effective_width(battle, BattleTeam.ALLY),
        )
        self._assign_team_positions(
            entities=self._active_enemies(battle),
            team=BattleTeam.ENEMY,
            front_line=battle.enemy_front_line,
            total_lines=battle.total_lines,
            width=self._effective_width(battle, BattleTeam.ENEMY),
        )

    def _assign_team_positions(self, entities: list, team: BattleTeam, front_line: int, total_lines: int, width: int):
        if not entities:
            return
        if team == BattleTeam.ALLY:
            accessible_lines = list(range(front_line, -1, -1))
            rear_line = max(0, front_line - 1)
        else:
            accessible_lines = list(range(front_line, total_lines))
            rear_line = min(total_lines - 1, front_line + 1)

        occupancy = {line: [False] * max(1, width) for line in accessible_lines}
        role_order = {
            CombatRole.FRONTLINE: 0,
            CombatRole.RANGED: 1,
            CombatRole.SUPPORT: 2,
        }
        sorted_entities = sorted(
            entities,
            key=lambda entity: (role_order.get(getattr(entity, "role", CombatRole.FRONTLINE), 0), -self._entity_lane_width(entity), self._entity_name(entity)),
        )

        for entity in sorted_entities:
            preferred_line = front_line if getattr(entity, "role", CombatRole.FRONTLINE) == CombatRole.FRONTLINE else rear_line
            line_candidates = [preferred_line] + [line for line in accessible_lines if line != preferred_line]
            placed = False
            entity_width = self._entity_lane_width(entity)
            for line in line_candidates:
                if line not in occupancy:
                    continue
                lane = self._find_open_lane(occupancy[line], entity_width)
                if lane is None:
                    continue
                self._occupy_lanes(occupancy[line], lane, entity_width)
                entity.line = line
                entity.lane_start = lane
                entity.lane_width = entity_width
                placed = True
                break
            if not placed:
                entity.line = accessible_lines[-1]
                entity.lane_start = 0
                entity.lane_width = entity_width

    @staticmethod
    def _find_open_lane(row: list[bool], lane_width: int) -> int | None:
        if lane_width >= len(row):
            return 0 if not any(row) else None
        for lane in range(0, len(row) - lane_width + 1):
            if not any(row[lane : lane + lane_width]):
                return lane
        return None

    @staticmethod
    def _occupy_lanes(row: list[bool], lane_start: int, lane_width: int):
        end = min(len(row), lane_start + lane_width)
        for index in range(lane_start, end):
            row[index] = True

    def _team_strength_on_front(self, entities: list, front_line: int) -> float:
        total = 0.0
        for entity in entities:
            if int(getattr(entity, "line", 0)) != int(front_line):
                continue
            total += self._entity_health(entity) * (1.0 + battle_factor("front_line_attack_count_weight", 0.10) * self._entity_attack_count(entity))
        return total

    def _broken_lane_count(self, battle: BattleState, team: BattleTeam) -> int:
        front_line = battle.player_front_line if team == BattleTeam.ALLY else battle.enemy_front_line
        width = self._effective_width(battle, team)
        occupied = [False] * max(1, width)
        entities = self._active_allies(battle) if team == BattleTeam.ALLY else self._active_enemies(battle)
        for entity in entities:
            if int(getattr(entity, "line", 0)) != int(front_line):
                continue
            start = max(0, int(getattr(entity, "lane_start", 0) or 0))
            end = min(len(occupied), start + self._entity_lane_width(entity))
            for lane in range(start, end):
                occupied[lane] = True
        return len([lane for lane in occupied if not lane])

    def _backline_intrusion(self, battle: BattleState, team: BattleTeam) -> int:
        if team == BattleTeam.ALLY:
            return 1 if any(int(getattr(enemy, "line", 0)) < int(battle.player_front_line) for enemy in self._active_enemies(battle)) else 0
        return 1 if any(int(getattr(ally, "line", 0)) > int(battle.enemy_front_line) for ally in self._active_allies(battle)) else 0

    def _advance_front(self, battle: BattleState, team: BattleTeam, highlights: list[str]):
        if team == BattleTeam.ALLY:
            battle.player_front_line += 1
            battle.enemy_front_line += 1
            highlights.append("The allied line advances.")
        else:
            battle.player_front_line -= 1
            battle.enemy_front_line -= 1
            highlights.append("The enemy line advances.")

    def _apply_recentering(self, battle: BattleState, player_progress: bool, enemy_progress: bool, highlights: list[str]):
        player_missing = max(0, int(battle.default_player_front_line) - int(battle.player_front_line))
        enemy_missing = max(0, int(battle.enemy_front_line) - int(battle.default_enemy_front_line))
        player_broken = self._broken_lane_count(battle, BattleTeam.ALLY)
        enemy_broken = self._broken_lane_count(battle, BattleTeam.ENEMY)
        player_intrusion = self._backline_intrusion(battle, BattleTeam.ALLY)
        enemy_intrusion = self._backline_intrusion(battle, BattleTeam.ENEMY)

        battle.player_recenter_pressure += player_missing + player_broken + player_intrusion
        battle.enemy_recenter_pressure += enemy_missing + enemy_broken + enemy_intrusion

        threshold_base = battle_factor_int("recentering_threshold_base", 3)
        player_threshold = max(1, threshold_base - player_missing - player_broken)
        enemy_threshold = max(1, threshold_base - enemy_missing - enemy_broken)

        if (player_missing > 0 or player_intrusion) and not enemy_progress and battle.player_recenter_pressure >= player_threshold:
            if battle.player_front_line < battle.default_player_front_line and battle.enemy_front_line < battle.total_lines:
                battle.player_front_line += 1
                battle.enemy_front_line += 1
                battle.player_recenter_pressure = 0.0
                highlights.append("The allied lines recover ground and re-center.")

        if (enemy_missing > 0 or enemy_intrusion) and not player_progress and battle.enemy_recenter_pressure >= enemy_threshold:
            if battle.enemy_front_line > battle.default_enemy_front_line and battle.player_front_line >= 0:
                battle.player_front_line -= 1
                battle.enemy_front_line -= 1
                battle.enemy_recenter_pressure = 0.0
                highlights.append("The enemy lines recover ground and re-center.")

    def _check_off_map_outcome(self, battle: BattleState, highlights: list[str]) -> bool:
        if battle.enemy_front_line >= battle.total_lines:
            battle.phase = BattlePhase.RESOLVED
            battle.outcome = BattleOutcome.VICTORY
            battle.result_summary = "The enemy is pressed off the field and breaks."
            highlights.append("Enemy morale breaks as they are driven off the field.")
            battle.pending_triggers.append(BattleTrigger(BattleTriggerType.MORALE_BREAK, battle.result_summary))
            return True
        if battle.player_front_line < 0:
            battle.phase = BattlePhase.RESOLVED
            if battle.encounter.encounter_type == EncounterType.SCAVENGING:
                battle.outcome = BattleOutcome.RETREAT
                battle.result_summary = "Your force is driven off the map and forced to retreat."
                battle.pending_triggers.append(BattleTrigger(BattleTriggerType.FORCED_RETREAT, battle.result_summary))
            else:
                battle.outcome = BattleOutcome.DEFEAT
                battle.result_summary = "Your force is driven off the map and defeated in the portal battle."
                battle.pending_triggers.append(BattleTrigger(BattleTriggerType.MORALE_BREAK, battle.result_summary))
            highlights.append(battle.result_summary)
            return True
        return False

    def _handle_reinforcements(self, battle: BattleState, highlights: list[str]) -> list:
        arrivals: list = []
        due = [entry for entry in battle.encounter.reinforcements if int(entry.exchange_number) == int(battle.exchange_count)]
        for reinforcement in due:
            for entry in reinforcement.entries:
                new_units, new_stacks = self._spawn_enemy_entry(entry)
                battle.enemy_units.extend(new_units)
                battle.enemy_stacks.extend(new_stacks)
                arrivals.extend(new_units)
                arrivals.extend(new_stacks)
            message = reinforcement.message or "Reinforcements arrive."
            highlights.append(message)
            battle.pending_triggers.append(BattleTrigger(BattleTriggerType.REINFORCEMENT, message))
        if arrivals:
            self._seed_new_entities_action_times(battle, arrivals)
        return arrivals

    def _total_health_ratio(self, active_entities: list, all_entities: list) -> float:
        current = sum(self._entity_health(entity) for entity in active_entities)
        maximum = sum(self._entity_max_health(entity) for entity in all_entities) or 1.0
        return max(0.0, min(1.0, current / maximum))

    def resolve_exchange(self, battle: BattleState, persist: bool = True, record_memory: bool = True) -> BattleExchangeSummary:
        if battle.phase == BattlePhase.RESOLVED:
            return battle.recent_summaries[-1] if battle.recent_summaries else BattleExchangeSummary(exchange_number=battle.exchange_count)

        battle.phase = BattlePhase.ACTIVE
        battle.exchange_count += 1
        highlights: list[str] = []
        triggers: list[BattleTrigger] = []
        exchange_start_time = float(battle.battle_time_seconds)
        exchange_end_time = exchange_start_time + exchange_duration_seconds()
        self._handle_reinforcements(battle, highlights)
        if self._timeline_needs_seeding(battle):
            self._seed_initial_action_times(battle)
        self._solve_formations(battle)

        while True:
            allies = self._active_allies(battle)
            enemies = self._active_enemies(battle)
            if not allies or not enemies:
                break
            actor = self._select_next_actor(battle)
            if actor is None:
                break
            raw_actor_time = getattr(actor, "next_action_time", exchange_end_time)
            actor_time = exchange_end_time if raw_actor_time is None else float(raw_actor_time)
            if actor_time > exchange_end_time:
                break
            battle.battle_time_seconds = actor_time
            self._execute_actor_turn(battle, actor, highlights)

        battle.battle_time_seconds = exchange_end_time

        allies = self._active_allies(battle)
        enemies = self._active_enemies(battle)
        if not enemies:
            battle.phase = BattlePhase.RESOLVED
            battle.outcome = BattleOutcome.VICTORY
            battle.result_summary = "The enemy force is destroyed."
        elif not allies:
            battle.phase = BattlePhase.RESOLVED
            battle.outcome = BattleOutcome.RETREAT if battle.encounter.encounter_type == EncounterType.SCAVENGING else BattleOutcome.DEFEAT
            battle.result_summary = "Your force collapses under enemy pressure."
        else:
            ally_strength = self._team_strength_on_front(allies, battle.player_front_line)
            enemy_strength = self._team_strength_on_front(enemies, battle.enemy_front_line)
            progress_multiplier = battle_factor("line_progress_advantage_multiplier", 1.25)
            player_progress = ally_strength > (enemy_strength * progress_multiplier)
            enemy_progress = enemy_strength > (ally_strength * progress_multiplier)
            if battle.orders.stance == CommanderStance.ADVANCE:
                player_progress = player_progress or ally_strength > enemy_strength
            if battle.orders.stance == CommanderStance.DEFENSIVE:
                enemy_progress = enemy_progress and (enemy_strength > ally_strength * battle_factor("defensive_line_hold_multiplier", 1.4))

            if player_progress and not enemy_progress:
                self._advance_front(battle, BattleTeam.ALLY, highlights)
                triggers.append(BattleTrigger(BattleTriggerType.LANE_BREAK, "Allied pressure opens the line."))
            elif enemy_progress and not player_progress:
                self._advance_front(battle, BattleTeam.ENEMY, highlights)
                triggers.append(BattleTrigger(BattleTriggerType.LANE_BREAK, "Enemy pressure caves in the line."))

            if not self._check_off_map_outcome(battle, highlights):
                self._apply_recentering(battle, player_progress, enemy_progress, highlights)
                self._solve_formations(battle)

        self._refresh_mission_state(battle, mission_complete=(battle.phase == BattlePhase.RESOLVED))

        for unit in battle.ally_units:
            if unit.notable and unit.health_state in {"UNCONSCIOUS", "DEAD"}:
                triggers.append(BattleTrigger(BattleTriggerType.HERO_DOWN, f"{unit.name} is {unit.health_state.lower()}."))
        if battle.encounter.allow_retreat and battle.outcome == BattleOutcome.ONGOING:
            ally_hp_ratio = self._total_health_ratio(self._active_allies(battle), battle.ally_units)
            if ally_hp_ratio <= battle_factor("retreat_opportunity_health_ratio_threshold", 0.35):
                triggers.append(BattleTrigger(BattleTriggerType.RETREAT_OPPORTUNITY, "Retreat is available if you want to preserve the team."))

        summary = BattleExchangeSummary(
            exchange_number=battle.exchange_count,
            highlights=highlights[-12:],
            triggers=triggers,
            player_front_line=battle.player_front_line,
            enemy_front_line=battle.enemy_front_line,
            player_hp_ratio=self._total_health_ratio(self._active_allies(battle), battle.ally_units),
            enemy_hp_ratio=self._total_health_ratio(self._active_enemies(battle), battle.enemy_units + battle.enemy_stacks),
        )
        battle.recent_summaries.append(summary)
        battle.recent_summaries = battle.recent_summaries[-8:]
        battle.pending_triggers = triggers
        battle.cached_victory_odds = None
        battle.cached_orders_signature = ""

        if record_memory:
            self._append_memory_event(battle, f"Exchange {battle.exchange_count}: {' '.join(summary.highlights[:3])}")

        if battle.phase == BattlePhase.RESOLVED and persist:
            self._finalize_battle(battle, record_memory=record_memory)
        elif persist:
            self.save_battle(battle)
        return summary

    def auto_resolve(self, battle: BattleState, max_exchanges: int = 24, persist: bool = True) -> BattleState:
        while battle.phase != BattlePhase.RESOLVED and battle.exchange_count < max_exchanges:
            self.resolve_exchange(battle, persist=False, record_memory=False)
        if battle.phase != BattlePhase.RESOLVED:
            battle.phase = BattlePhase.RESOLVED
            battle.outcome = BattleOutcome.RETREAT if battle.encounter.allow_retreat else BattleOutcome.DEFEAT
            battle.result_summary = "The battle times out into a withdrawal."
        if persist:
            self._finalize_battle(battle, record_memory=True)
        return battle
    def _finalize_battle(self, battle: BattleState, record_memory: bool = True):
        self._refresh_mission_state(battle, mission_complete=True)
        player = self.player_service.get_player_sync(battle.player_id)
        if player is not None:
            for unit in battle.ally_units:
                source = self._player_source_character(battle.player_id, unit.character_instance_id)
                if source is None:
                    continue
                source.health = max(0.0, float(unit.health))
                state_name = self._normalize_health_state_name(unit.health_state)
                if battle.outcome == BattleOutcome.DEFEAT and source.health <= 0:
                    state_name = "DEAD"
                source.healthState = HealthState[state_name]
                if isinstance(source, MainCharacter):
                    source.stats.missionCount = int(getattr(source.stats, "missionCount", 0) or 0) + 1
            self.player_service.persist_player(player)
        if record_memory:
            self._append_memory_event(battle, battle.result_summary or f"Battle ends: {battle.outcome.name}.")
        self.clear_battle(battle.player_id)

    def estimate_victory_odds(self, battle: BattleState, simulations: int = 32) -> float:
        signature = battle.orders.signature()
        if battle.cached_victory_odds is not None and battle.cached_orders_signature == signature:
            return float(battle.cached_victory_odds)
        wins = 0
        for index in range(max(1, int(simulations))):
            clone = BattleState.from_dict(battle.to_dict())
            clone.phase = BattlePhase.ACTIVE
            local_rng = random.Random(1000 + index)
            original_rng = self.damage_calculator._rng
            self.damage_calculator._rng = local_rng
            try:
                self.auto_resolve(clone, max_exchanges=18, persist=False)
            finally:
                self.damage_calculator._rng = original_rng
            if clone.outcome == BattleOutcome.VICTORY:
                wins += 1
        odds = wins / max(1, int(simulations))
        battle.cached_victory_odds = odds
        battle.cached_orders_signature = signature
        self.save_battle(battle)
        return odds

    def cycle_stance(self, battle: BattleState):
        values = list(CommanderStance)
        index = values.index(battle.orders.stance)
        battle.orders.stance = values[(index + 1) % len(values)]
        battle.cached_victory_odds = None
        self.save_battle(battle)

    def cycle_target_priority(self, battle: BattleState):
        values = list(TargetPriority)
        index = values.index(battle.orders.target_priority)
        battle.orders.target_priority = values[(index + 1) % len(values)]
        battle.cached_victory_odds = None
        self.save_battle(battle)

    def cycle_token_policy(self, battle: BattleState):
        values = list(TokenPolicy)
        index = values.index(battle.orders.token_policy)
        battle.orders.token_policy = values[(index + 1) % len(values)]
        battle.cached_victory_odds = None
        self.save_battle(battle)

    def set_active_tab(self, battle: BattleState, tab_name: str):
        battle.active_tab = str(tab_name or "Orders")
        self.save_battle(battle)

    def hold_position(self, battle: BattleState):
        battle.orders.stance = CommanderStance.HOLD
        self.save_battle(battle)

    def retreat(self, battle: BattleState) -> BattleState:
        if not battle.encounter.allow_retreat:
            raise ValueError("Retreat is disabled in this encounter.")
        battle.phase = BattlePhase.RESOLVED
        battle.outcome = BattleOutcome.RETREAT
        battle.result_summary = "You order a retreat and disengage the force."
        self._finalize_battle(battle, record_memory=True)
        return battle

    def _resolve_inventory_item(self, player, identifier) -> Item | None:
        if hasattr(identifier, "itemId"):
            return self.item_service.get_item_by_id(str(getattr(identifier, "itemId", "") or "")) or identifier
        if hasattr(identifier, "name"):
            return self.item_service.get_item(str(getattr(identifier, "itemId", "") or getattr(identifier, "name", "")))
        return self.item_service.get_item(str(identifier or ""))

    def list_available_consumables(self, battle: BattleState) -> list[tuple[str, str]]:
        player = self.player_service.get_player_sync(battle.player_id)
        if player is None:
            return []
        results = []
        for entry in getattr(player, "inventory", []) or []:
            item = self._resolve_inventory_item(player, entry)
            if not isinstance(item, Consumable):
                continue
            item_id = str(getattr(item, "itemId", "") or "")
            label = self.item_service.get_item_label(item) if item_id else str(getattr(item, "name", "Consumable") or "Consumable")
            results.append((item_id or label, label))
        return results

    def use_consumable(self, battle: BattleState, item_identifier: str) -> str:
        player = self.player_service.get_player_sync(battle.player_id)
        if player is None:
            raise ValueError("Player not found.")
        inventory = list(getattr(player, "inventory", []) or [])
        item = self.item_service.get_consumable(str(item_identifier or ""))
        if item is None:
            item = self.item_service.get_consumable_by_id(self.item_service.parse_item_id_from_label(item_identifier))
        if item is None:
            raise ValueError("Consumable not found.")

        removed = False
        remaining = []
        for entry in inventory:
            resolved = self._resolve_inventory_item(player, entry)
            if not removed and resolved is not None and str(getattr(resolved, "itemId", "") or "") == str(getattr(item, "itemId", "") or ""):
                removed = True
                continue
            remaining.append(entry)
        if not removed:
            raise ValueError("That consumable is not in the player's inventory.")
        player.inventory = remaining
        power_values = [power for power in getattr(item, "itemPower", []) or [] if getattr(power, "powerType", None) == PowerType.CONSUMABLE_POWER]
        amount = float(getattr(power_values[0], "power", 10) if power_values else 10)
        offensive = bool(getattr(item, "damageType", []))
        if offensive:
            allies = self._active_allies(battle)
            target_source = allies[0] if allies else None
            target = self._select_target(battle, target_source, self._active_enemies(battle), battle.orders)
            if target is None:
                raise ValueError("No valid enemy target for this consumable.")
            damage_result = self._apply_damage_with_result(target, amount)
            if damage_result["defeated_units"] > 0 and allies:
                self._record_kill(battle, allies[0], target, damage_result["defeated_units"])
            self._refresh_mission_state(battle, mission_complete=(battle.phase == BattlePhase.RESOLVED))
            message = f"Used {item.name} on {self._entity_name(target)} for {damage_result['damage']:.1f} damage."
        else:
            allies = self._active_allies(battle)
            if not allies:
                raise ValueError("No allied targets available.")
            target = min(allies, key=lambda entity: self._entity_health(entity) / max(1.0, self._entity_max_health(entity)))
            healed = self._heal_entity(
                target,
                amount * max(battle_factor("minimum_resource_efficiency_multiplier", 0.5), 1.0 + battle.orders.resource_efficiency_modifier),
            )
            self._refresh_mission_state(battle, mission_complete=(battle.phase == BattlePhase.RESOLVED))
            message = f"Used {item.name} on {self._entity_name(target)} and restored {healed:.1f} health."
        self.player_service.persist_player(player)
        self.save_battle(battle)
        return message
    def _is_adversarial_strategy(self, text: str) -> bool:
        lowered = str(text or "").strip().lower()
        if not lowered:
            return True
        return any(re.search(pattern, lowered) for pattern in self.STRATEGY_INJECTION_PATTERNS)

    def _neutral_strategy_result(self, reason: str) -> dict[str, Any]:
        return {
            "score": 5,
            "reasons": [reason],
            "risk_flags": [],
            "confidence": 0.0,
        }

    def judge_strategy(self, battle: BattleState, strategy_text: str) -> dict[str, Any]:
        text = str(strategy_text or "").strip()
        if self._is_adversarial_strategy(text):
            return self._neutral_strategy_result("Strategy text was empty or looked adversarial, so neutral orders were applied.")
        if self.openai_service is None or not getattr(self.openai_service, "is_configured", lambda: False)():
            return self._neutral_strategy_result("OpenAI is not configured, so neutral orders were applied.")
        if not hasattr(self.openai_service, "judge_combat_strategy"):
            return self._neutral_strategy_result("Combat judge is unavailable, so neutral orders were applied.")

        prompt_packet = {
            "encounter": battle.encounter.to_dict(),
            "orders": battle.orders.to_dict(),
            "strategy_text": text,
            "recent_highlights": [summary.to_dict() for summary in battle.recent_summaries[-2:]],
        }
        results = []
        for _ in range(3):
            try:
                judgment = self.openai_service.judge_combat_strategy(prompt_packet)
                results.append(judgment)
            except Exception:
                continue
        if not results:
            return self._neutral_strategy_result("Strategy judge failed, so neutral orders were applied.")
        scores = sorted(int(max(1, min(10, getattr(result, "score", 5)))) for result in results)
        median_score = scores[len(scores) // 2]
        median_result = sorted(results, key=lambda result: int(max(1, min(10, getattr(result, "score", 5)))))[len(results) // 2]
        return {
            "score": median_score,
            "reasons": list(getattr(median_result, "reasons", []) or []),
            "risk_flags": list(getattr(median_result, "risk_flags", []) or []),
            "confidence": float(getattr(median_result, "confidence", 0.0) or 0.0),
        }

    def apply_strategy(self, battle: BattleState, strategy_text: str) -> dict[str, Any]:
        judgment = self.judge_strategy(battle, strategy_text)
        score = int(judgment["score"])
        battle.orders.strategy_text = strategy_text
        battle.orders.strategy_score = score
        battle.orders.strategy_reasons = list(judgment["reasons"])
        battle.orders.strategy_risk_flags = list(judgment["risk_flags"])
        battle.orders.strategy_confidence = float(judgment["confidence"])
        if score <= battle_factor_int("strategy_low_score_max", 3):
            battle.orders.lane_discipline_modifier = battle_factor("strategy_low_lane_discipline_modifier", -0.05)
            battle.orders.resource_efficiency_modifier = battle_factor("strategy_low_resource_efficiency_modifier", -0.10)
            battle.orders.width_control_bonus = 0
        elif score <= battle_factor_int("strategy_mid_score_max", 6):
            battle.orders.lane_discipline_modifier = battle_factor("strategy_mid_lane_discipline_modifier", 0.0)
            battle.orders.resource_efficiency_modifier = battle_factor("strategy_mid_resource_efficiency_modifier", 0.0)
            battle.orders.width_control_bonus = 0
        elif score <= battle_factor_int("strategy_high_score_max", 8):
            battle.orders.lane_discipline_modifier = battle_factor("strategy_high_lane_discipline_modifier", 0.05)
            battle.orders.resource_efficiency_modifier = battle_factor("strategy_high_resource_efficiency_modifier", 0.05)
            battle.orders.width_control_bonus = 0
        else:
            battle.orders.lane_discipline_modifier = battle_factor("strategy_top_lane_discipline_modifier", 0.10)
            battle.orders.resource_efficiency_modifier = battle_factor("strategy_top_resource_efficiency_modifier", 0.10)
            battle.orders.width_control_bonus = battle_factor_int("strategy_top_width_control_bonus", 1)
        battle.cached_victory_odds = None
        battle.cached_orders_signature = ""
        self.save_battle(battle)
        return judgment

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
        self.memory_service.append_manual_event(
            player_id=battle.player_id,
            participant_ids=participant_ids,
            summary=str(summary or "").strip(),
            event_type="combat_event",
            tags=["combat", battle.encounter.encounter_type.name.lower(), battle.encounter.terrain.lower()],
            location=battle.encounter.terrain,
            stakes=battle.encounter.objective_text,
        )

    def build_battle_snapshot(self, battle: BattleState) -> dict[str, Any]:
        odds = self.estimate_victory_odds(battle) if battle.phase != BattlePhase.RESOLVED else (1.0 if battle.outcome == BattleOutcome.VICTORY else 0.0)
        recent_summary = battle.recent_summaries[-1] if battle.recent_summaries else None
        return {
            "encounter_name": battle.encounter.name,
            "mission_name": battle.mission_name or battle.encounter.name,
            "terrain": battle.encounter.terrain,
            "exchange": battle.exchange_count,
            "stance": battle.orders.stance.name,
            "width": battle.width,
            "total_lines": battle.total_lines,
            "player_front_line": battle.player_front_line,
            "enemy_front_line": battle.enemy_front_line,
            "phase": battle.phase.name,
            "outcome": battle.outcome.name,
            "objective": battle.encounter.objective_text,
            "objective_description": battle.mission_objective.describe(),
            "objective_status": battle.mission_objective_status.value,
            "allow_retreat": battle.encounter.allow_retreat,
            "cached_victory_odds": odds,
            "mission_statistics": battle.mission_statistics.to_dict(),
            "recent_highlights": recent_summary.highlights if recent_summary else [],
            "recent_triggers": [trigger.message for trigger in (recent_summary.triggers if recent_summary else [])],
            "allies": [
                {
                    "name": unit.name,
                    "health": round(unit.health, 1),
                    "max_health": round(unit.max_health, 1),
                    "state": unit.health_state,
                    "line": unit.line,
                    "lane": unit.lane_start,
                    "role": unit.role.name,
                }
                for unit in battle.ally_units
            ],
            "enemies": [
                {
                    "name": unit.name,
                    "health": round(self._entity_health(unit), 1),
                    "max_health": round(self._entity_max_health(unit), 1),
                    "state": unit.health_state,
                    "line": unit.line,
                    "lane": unit.lane_start,
                    "role": unit.role.name,
                    "count": getattr(unit, "current_count", 1),
                }
                for unit in list(battle.enemy_units) + list(battle.enemy_stacks)
            ],
        }
