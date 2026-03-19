from __future__ import annotations

from typing import Any, Callable

from src.domain.CharacterUtil import Attributes
from src.domain.Items import Gear, Weapon
from src.domain.Race import CreatureSize
from src.domain.combat import (
    BattleTeam,
    CombatRole,
    CombatUnitState,
    EncounterEnemyEntry,
    EnemyStackState,
    lane_width_for_size,
)
from src.domain.combat_timing import (
    ExertionLevel,
    speed_factor_from_attributes,
    stamina_limit_from_physical_stamina,
    stamina_regen_per_second_from_physical_stamina,
)
from src.services.combat_loadout_service import select_active_character_weapon


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
        max_health = max(1.0, float(get_max_health() if callable(get_max_health) else getattr(character, "health", 100.0) or 100.0))
        current_health = max(0.0, min(float(getattr(character, "health", max_health) or max_health), max_health))
        get_speed = getattr(character, "GetSpeed", None)
        speed = float(get_speed() if callable(get_speed) else speed_factor_from_attributes(getattr(attrs, "physicalPower", 5.0), getattr(attrs, "magicPower", 5.0)))
        get_stamina_limit = getattr(character, "GetStaminaLimit", None)
        stamina_limit = float(get_stamina_limit() if callable(get_stamina_limit) else stamina_limit_from_physical_stamina(getattr(attrs, "physicalStamina", 5.0)))
        get_stamina_regen = getattr(character, "GetStaminaRegenPerSecond", None)
        stamina_regen = float(get_stamina_regen() if callable(get_stamina_regen) else stamina_regen_per_second_from_physical_stamina(getattr(attrs, "physicalStamina", 5.0)))
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
        unit_health = max(1.0, float(get_max_health() if callable(get_max_health) else getattr(character, "health", 100.0) or 100.0))
        get_speed = getattr(character, "GetSpeed", None)
        speed = float(get_speed() if callable(get_speed) else speed_factor_from_attributes(getattr(attrs, "physicalPower", 5.0), getattr(attrs, "magicPower", 5.0)))
        get_stamina_limit = getattr(character, "GetStaminaLimit", None)
        stamina_limit = float(get_stamina_limit() if callable(get_stamina_limit) else stamina_limit_from_physical_stamina(getattr(attrs, "physicalStamina", 5.0)))
        get_stamina_regen = getattr(character, "GetStaminaRegenPerSecond", None)
        stamina_regen = float(get_stamina_regen() if callable(get_stamina_regen) else stamina_regen_per_second_from_physical_stamina(getattr(attrs, "physicalStamina", 5.0)))
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
