from __future__ import annotations

from typing import Any, Callable

from src.domain.character_util import Attributes
from src.domain.items import Gear, Weapon
from src.domain.Race import CreatureSize
from src.domain.combat.encounter import EncounterEnemyEntry
from src.domain.combat.enums import BattleTeam, CombatRole, lane_width_for_size
from src.domain.combat_timing import (
    ExertionLevel,
    speed_factor_from_attributes,
    stamina_limit_from_physical_stamina,
    stamina_regen_per_second_from_physical_stamina,
)
from src.domain.combat.units import CombatUnitState, EnemyStackState
from src.services.combat_loadout_service import select_active_character_weapon
from src.domain.mission import EliminationObjective, MissionObjective, MissionObjectiveStatus, MissionStatistics
from src.domain.combat.encounter import EncounterDefinition
from src.domain.combat.enums import BattleOutcome, BattlePhase, EncounterType
from src.domain.combat.state import BattleState, CommanderOrders
from src.domain.combat_timing import exchange_duration_seconds


class BattleRosterBuilder:
    def __init__(self, context, item_service, character_service, health_state_for_ratio: Callable[[float, float], Any]):
        self.context = context
        self.item_service = item_service
        self.character_service = character_service
        self.health_state_for_ratio = health_state_for_ratio

    def party_members(self, player) -> list:
        get_mission_party = getattr(player, "GetMissionPartyCharacters", None)
        if callable(get_mission_party):
            return list(get_mission_party())
        return list(getattr(player, "characters", []) or [])

    def build_ally_units(self, player) -> list[CombatUnitState]:
        units = []
        for index, character in enumerate(self.party_members(player)):
            units.append(
                self.character_to_unit(
                    character=character,
                    team=BattleTeam.ALLY,
                    unit_id=f"ally_{index}_{getattr(character, 'playerInstanceId', '') or getattr(character, 'name', 'unit')}",
                    character_instance_id=str(getattr(character, "playerInstanceId", "") or ""),
                    is_player_owned=True,
                )
            )
        return units

    def spawn_enemy_entry(self, entry: EncounterEnemyEntry) -> tuple[list[CombatUnitState], list[EnemyStackState]]:
        template = None
        template_character_id = ""
        race_id = ""
        if entry.kind == "character":
            template_character_id = str(entry.identifier or "")
            template = self.character_service.get_character(template_character_id)
            if template is None:
                return [], []
            race_id = str(getattr(template, "race", "Human1") or "Human1")
        else:
            race_id = str(entry.identifier or "Human1")
            race = self.context.all_races.get(race_id)
            if race is None:
                return [], []
            template = getattr(race, "averageSpecimine", None)
            if template is None:
                return [], []
            for character_id, character in self.context.all_characters.items():
                if character is template or getattr(character, "name", "") == getattr(template, "name", ""):
                    template_character_id = character_id
                    break

        if template is None:
            return [], []

        if entry.use_stack and int(entry.count) > 1:
            stack = self.character_to_stack(
                character=template,
                count=int(entry.count),
                stack_id=f"stack_{entry.kind}_{entry.identifier}_{entry.count}",
                template_character_id=template_character_id,
                race_id=race_id,
                name_override=entry.name_override or getattr(template, "name", "Enemy Stack"),
            )
            return [], [stack]

        units = []
        for index in range(int(entry.count)):
            units.append(
                self.character_to_unit(
                    character=template,
                    team=BattleTeam.ENEMY,
                    unit_id=f"enemy_{entry.kind}_{entry.identifier}_{index}",
                    template_character_id=template_character_id,
                    name_override=entry.name_override or getattr(template, "name", "Enemy"),
                    notable=bool(entry.notable),
                )
            )
        return units, []

    def resolve_item_id(self, item) -> str:
        if item is None:
            return ""
        item_id = str(getattr(item, "itemId", "") or "").strip()
        if item_id:
            return item_id
        name = str(getattr(item, "name", "") or "").strip()
        resolved = self.item_service.get_item(name)
        if resolved is None:
            return ""
        return str(getattr(resolved, "itemId", "") or "")

    def race_lookup(self, race_id: str):
        return self.context.all_races.get(str(race_id or "").strip())

    def resolve_size_for_character(self, character) -> CreatureSize:
        race_id = str(getattr(character, "race", "Human1") or "Human1")
        race = self.context.all_races.get(race_id)
        if race is None:
            return CreatureSize.STANDARD
        return getattr(race, "size", CreatureSize.STANDARD)

    @staticmethod
    def extract_direct_damage_spells(character) -> list[str]:
        result = []
        for spell in getattr(character, "spells", []) or []:
            try:
                if float(getattr(spell, "power", 0) or 0) > 0:
                    result.append(str(getattr(spell, "name", "") or ""))
            except Exception:
                continue
        return result

    def infer_role(self, character) -> CombatRole:
        active_weapon = select_active_character_weapon(character, race_lookup=self.race_lookup)
        if isinstance(active_weapon, Weapon) and active_weapon.isRanged:
            return CombatRole.RANGED
        direct_damage_spells = self.extract_direct_damage_spells(character)
        if direct_damage_spells and active_weapon is None:
            return CombatRole.RANGED
        if not active_weapon and not direct_damage_spells:
            return CombatRole.SUPPORT
        return CombatRole.FRONTLINE

    def character_to_unit(
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
        attrs = getattr(character, "finalAttributes", getattr(character, "attributes", Attributes()))
        gear = getattr(character, "gear", Gear())
        size = self.resolve_size_for_character(character)
        get_max_health = getattr(character, "GetMaxHealth", None)
        max_health = max(
            1.0, float(get_max_health() if callable(get_max_health) else getattr(character, "health", 100.0) or 100.0)
        )
        current_health = max(0.0, min(float(getattr(character, "health", max_health) or max_health), max_health))
        get_speed = getattr(character, "GetSpeed", None)
        speed = float(
            get_speed()
            if callable(get_speed)
            else speed_factor_from_attributes(getattr(attrs, "physicalPower", 5.0), getattr(attrs, "magicPower", 5.0))
        )
        get_stamina_limit = getattr(character, "GetStaminaLimit", None)
        stamina_limit = float(
            get_stamina_limit()
            if callable(get_stamina_limit)
            else stamina_limit_from_physical_stamina(getattr(attrs, "physicalStamina", 5.0))
        )
        get_stamina_regen = getattr(character, "GetStaminaRegenPerSecond", None)
        stamina_regen = float(
            get_stamina_regen()
            if callable(get_stamina_regen)
            else stamina_regen_per_second_from_physical_stamina(getattr(attrs, "physicalStamina", 5.0))
        )
        inventory_item_ids = []
        for item in getattr(gear, "inventory", []) or []:
            item_id = self.resolve_item_id(item)
            if item_id:
                inventory_item_ids.append(item_id)
        return CombatUnitState(
            unit_id=unit_id,
            name=name_override or str(getattr(character, "name", "Unit") or "Unit"),
            team=team,
            role=self.infer_role(character),
            size=size,
            level=int(getattr(character, "level", 0) or 0),
            health=current_health,
            max_health=max_health,
            health_state=self.health_state_for_ratio(current_health, max_health).name,
            lane_width=lane_width_for_size(size),
            starting_line=0,
            character_instance_id=character_instance_id,
            is_player_owned=is_player_owned,
            is_boss=is_boss,
            is_elite=is_elite,
            template_character_id=template_character_id,
            race_id=str(getattr(character, "race", "Human1") or "Human1"),
            physical_power=float(getattr(attrs, "physicalPower", 5.0)),
            physical_stamina=float(getattr(attrs, "physicalStamina", 5.0)),
            physical_resistance=float(getattr(attrs, "physicalResistance", 5.0)),
            magic_power=float(getattr(attrs, "magicPower", 5.0)),
            magic_stamina=float(getattr(attrs, "magicStamina", 5.0)),
            magic_resistance=float(getattr(attrs, "magicResistance", 5.0)),
            speed=speed,
            stamina_current=stamina_limit,
            stamina_limit=stamina_limit,
            stamina_regen_per_second=stamina_regen,
            stamina_last_update_time=0.0,
            next_action_time=0.0,
            exertion_level=ExertionLevel.FRESH.name,
            primary_weapon_item_id=self.resolve_item_id(getattr(gear, "primaryWeapon", None)),
            offhand_item_id=self.resolve_item_id(getattr(gear, "offhand", None)),
            inventory_item_ids=inventory_item_ids,
            spell_names=self.extract_direct_damage_spells(character),
            notable=notable,
        )

    def character_to_stack(
        self,
        character,
        count: int,
        stack_id: str,
        template_character_id: str,
        race_id: str,
        name_override: str,
    ) -> EnemyStackState:
        attrs = getattr(character, "finalAttributes", getattr(character, "attributes", Attributes()))
        gear = getattr(character, "gear", Gear())
        size = self.resolve_size_for_character(character)
        get_max_health = getattr(character, "GetMaxHealth", None)
        unit_health = max(
            1.0, float(get_max_health() if callable(get_max_health) else getattr(character, "health", 100.0) or 100.0)
        )
        get_speed = getattr(character, "GetSpeed", None)
        speed = float(
            get_speed()
            if callable(get_speed)
            else speed_factor_from_attributes(getattr(attrs, "physicalPower", 5.0), getattr(attrs, "magicPower", 5.0))
        )
        get_stamina_limit = getattr(character, "GetStaminaLimit", None)
        stamina_limit = float(
            get_stamina_limit()
            if callable(get_stamina_limit)
            else stamina_limit_from_physical_stamina(getattr(attrs, "physicalStamina", 5.0))
        )
        get_stamina_regen = getattr(character, "GetStaminaRegenPerSecond", None)
        stamina_regen = float(
            get_stamina_regen()
            if callable(get_stamina_regen)
            else stamina_regen_per_second_from_physical_stamina(getattr(attrs, "physicalStamina", 5.0))
        )
        return EnemyStackState(
            stack_id=stack_id,
            name=name_override,
            team=BattleTeam.ENEMY,
            role=self.infer_role(character),
            size=size,
            count=max(1, int(count)),
            max_count=max(1, int(count)),
            unit_health=unit_health,
            total_health=float(max(1, int(count))) * unit_health,
            health_state="HEALTHY",
            lane_width=lane_width_for_size(size),
            starting_line=0,
            template_character_id=template_character_id,
            is_boss=False,
            is_elite=False,
            race_id=race_id,
            level=int(getattr(character, "level", 0) or 0),
            physical_power=float(getattr(attrs, "physicalPower", 5.0)),
            physical_stamina=float(getattr(attrs, "physicalStamina", 5.0)),
            physical_resistance=float(getattr(attrs, "physicalResistance", 5.0)),
            magic_power=float(getattr(attrs, "magicPower", 5.0)),
            magic_stamina=float(getattr(attrs, "magicStamina", 5.0)),
            magic_resistance=float(getattr(attrs, "magicResistance", 5.0)),
            speed=speed,
            stamina_current=stamina_limit,
            stamina_limit=stamina_limit,
            stamina_regen_per_second=stamina_regen,
            stamina_last_update_time=0.0,
            next_action_time=0.0,
            exertion_level=ExertionLevel.FRESH.name,
            primary_weapon_item_id=self.resolve_item_id(getattr(gear, "primaryWeapon", None)),
            offhand_item_id=self.resolve_item_id(getattr(gear, "offhand", None)),
            spell_names=self.extract_direct_damage_spells(character),
        )


class BattleSetupMixin:
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

        objective = (
            mission_objective if mission_objective is not None else self._default_objective_for_encounter(encounter)
        )
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
