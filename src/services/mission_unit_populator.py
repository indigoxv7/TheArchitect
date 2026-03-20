from __future__ import annotations

import copy
import math
import random
from dataclasses import dataclass, field

from src.domain.items import Gear
from src.domain.mission import MissionTemplate, MissionUnitOption
from src.domain.Race import Race
from src.domain.Unit import Unit
from src.services.character_generation import generate_character_from_race


@dataclass
class PopulatedMissionUnit:
    allegianceId: str
    unitId: str
    unitLabel: str
    character: object
    pointsSpent: int
    isRequired: bool = False
    isElite: bool = False
    isBoss: bool = False


@dataclass
class PopulatedMissionUnitGroup:
    allegianceId: str
    unitId: str
    unitLabel: str
    pointsSpent: int = 0
    units: list[PopulatedMissionUnit] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.units)


@dataclass
class PopulatedMissionAllegiance:
    allegianceId: str
    powerPointCap: int
    groups: list[PopulatedMissionUnitGroup] = field(default_factory=list)
    pointsSpent: int = 0
    unusedPoints: int = 0

    @property
    def generatedUnits(self) -> list[PopulatedMissionUnit]:
        return [unit for group in self.groups for unit in group.units]


@dataclass
class PopulatedMissionTemplate:
    missionName: str
    allegiances: list[PopulatedMissionAllegiance] = field(default_factory=list)

    @property
    def generatedUnits(self) -> list[PopulatedMissionUnit]:
        return [unit for result in self.allegiances for unit in result.generatedUnits]

    @property
    def totalPointsSpent(self) -> int:
        return sum(result.pointsSpent for result in self.allegiances)

    @property
    def totalUnusedPoints(self) -> int:
        return sum(result.unusedPoints for result in self.allegiances)


class MissionUnitPopulator:
    def __init__(self, unit_service, power_rating_service):
        self.unit_service = unit_service
        self.power_rating_service = power_rating_service

    def populate(self, mission: MissionTemplate, seed: int | None = None) -> PopulatedMissionTemplate:
        rng = random.Random(seed)
        allegiance_results = [
            self._populate_allegiance(mission.name, config, rng) for config in mission.allegianceConfigs
        ]
        return PopulatedMissionTemplate(
            missionName=str(getattr(mission, "name", "") or "Mission Preview"),
            allegiances=allegiance_results,
        )

    def _populate_allegiance(self, mission_name: str, config, rng: random.Random) -> PopulatedMissionAllegiance:
        result = PopulatedMissionAllegiance(
            allegianceId=str(getattr(config, "allegianceId", "") or "").strip(),
            powerPointCap=max(0, int(getattr(config, "powerPointCap", 0) or 0)),
        )
        option_counts = {str(option.unitId): 0 for option in config.unitOptions}
        group_by_unit_id: dict[str, PopulatedMissionUnitGroup] = {}
        remaining_points = int(result.powerPointCap)

        for option in config.unitOptions:
            required_count = max(0, int(getattr(option, "capacityMin", 0) or 0))
            for _ in range(required_count):
                generated = self._generate_unit(
                    mission_name=mission_name,
                    allegiance_id=result.allegianceId,
                    option=option,
                    unit_index=option_counts[str(option.unitId)] + 1,
                    config=config,
                    rng=rng,
                    is_required=True,
                )
                self._record_generated_unit(result, group_by_unit_id, generated)
                option_counts[str(option.unitId)] += 1
                remaining_points -= generated.pointsSpent

        while True:
            candidates = []
            for option in config.unitOptions:
                unit_id = str(option.unitId or "").strip()
                if not unit_id:
                    continue
                if self._is_at_capacity(option, option_counts[unit_id]):
                    continue
                generated = self._generate_unit(
                    mission_name=mission_name,
                    allegiance_id=result.allegianceId,
                    option=option,
                    unit_index=option_counts[unit_id] + 1,
                    config=config,
                    rng=rng,
                    is_required=False,
                )
                if generated.pointsSpent <= max(0, remaining_points):
                    candidates.append(generated)

            if not candidates:
                break

            selected = rng.choice(candidates)
            self._record_generated_unit(result, group_by_unit_id, selected)
            option_counts[selected.unitId] += 1
            remaining_points -= selected.pointsSpent

        result.groups = sorted(group_by_unit_id.values(), key=lambda entry: (entry.unitLabel.lower(), entry.unitId))
        result.unusedPoints = max(0, remaining_points)
        return result

    @staticmethod
    def _is_at_capacity(option: MissionUnitOption, current_count: int) -> bool:
        capacity_max = getattr(option, "capacityMax", None)
        if capacity_max is None:
            return False
        return int(current_count) >= int(capacity_max)

    def _record_generated_unit(
        self,
        result: PopulatedMissionAllegiance,
        group_by_unit_id: dict[str, PopulatedMissionUnitGroup],
        generated: PopulatedMissionUnit,
    ) -> None:
        group = group_by_unit_id.get(generated.unitId)
        if group is None:
            group = PopulatedMissionUnitGroup(
                allegianceId=generated.allegianceId,
                unitId=generated.unitId,
                unitLabel=generated.unitLabel,
            )
            group_by_unit_id[generated.unitId] = group
        group.units.append(generated)
        group.pointsSpent += generated.pointsSpent
        result.pointsSpent += generated.pointsSpent

    def _generate_unit(
        self,
        mission_name: str,
        allegiance_id: str,
        option: MissionUnitOption,
        unit_index: int,
        config,
        rng: random.Random,
        is_required: bool,
    ) -> PopulatedMissionUnit:
        unit = self.unit_service.get_unit_by_id(option.unitId)
        if unit is None:
            raise ValueError(f"Unit '{option.unitId}' does not exist.")
        effective_race = self.unit_service.resolve_effective_race(unit)
        if effective_race is None:
            raise ValueError(f"Unit '{option.unitId}' could not resolve an effective race.")

        generated_character = self._build_character_from_unit(
            unit=unit,
            effective_race=effective_race,
            config=config,
            option=option,
            unit_index=unit_index,
            rng=rng,
        )
        points_spent = max(1, int(math.ceil(self.power_rating_service.character_power_level(generated_character))))
        return PopulatedMissionUnit(
            allegianceId=allegiance_id,
            unitId=str(option.unitId or "").strip(),
            unitLabel=self.unit_service.get_unit_label(unit),
            character=generated_character,
            pointsSpent=points_spent,
            isRequired=is_required,
            isElite=bool(getattr(generated_character, "_mission_is_elite", False)),
            isBoss=bool(getattr(generated_character, "_mission_is_boss", False)),
        )

    def _build_character_from_unit(self, unit: Unit, effective_race: Race, config, option, unit_index: int, rng):
        base_name = str(getattr(effective_race, "name", "") or self.unit_service.get_effective_name(unit) or "Unit")
        is_boss = bool(getattr(option, "isBoss", False))
        is_elite = rng.random() < float(getattr(option, "eliteChance", 0.0) or 0.0)
        display_name = self._build_unit_name(base_name, unit_index, is_boss=is_boss, is_elite=is_elite)
        character = generate_character_from_race(name=display_name, race=effective_race, rng=rng)

        level_min = max(0, int(getattr(config, "levelMin", 0) or 0))
        level_max = max(level_min, int(getattr(config, "levelMax", level_min) or level_min))
        if level_max > 0:
            character.level = rng.randint(level_min, level_max)
        elif level_min > 0:
            character.level = level_min

        self._randomize_spells(character, effective_race, rng)
        self._randomize_gear(character, effective_race, rng)
        character.CalculateBonus()
        character.health = character.GetMaxHealth()
        character.RefreshHealthState()
        setattr(character, "_mission_is_boss", is_boss)
        setattr(character, "_mission_is_elite", is_elite)
        return character

    @staticmethod
    def _build_unit_name(base_name: str, unit_index: int, is_boss: bool, is_elite: bool) -> str:
        prefixes = []
        if is_boss:
            prefixes.append("Boss")
        elif is_elite:
            prefixes.append("Elite")
        prefix_text = f"{' '.join(prefixes)} " if prefixes else ""
        return f"{prefix_text}{base_name} {unit_index}"

    @staticmethod
    def _randomize_spells(character, race: Race, rng: random.Random) -> None:
        spell_list = list(getattr(race, "spellList", []) or [])
        if not spell_list:
            return

        selected_spells = []
        max_level = max(0, min(int(getattr(character, "level", 0) or 0), len(spell_list) - 1))
        for level in range(max_level + 1):
            entries = [copy.deepcopy(spell) for spell in spell_list[level] if spell is not None]
            if not entries:
                continue
            selected_spells.append(rng.choice(entries))
        if selected_spells:
            character.spells = selected_spells

    @staticmethod
    def _randomize_gear(character, race: Race, rng: random.Random) -> None:
        gear = (
            copy.deepcopy(getattr(character, "gear", None)) if getattr(character, "gear", None) is not None else Gear()
        )
        gear_options = getattr(race, "gearOptions", None)
        if gear_options is None:
            character.gear = gear
            return

        slot_field_map = {
            "headOptions": "head",
            "neckOptions": "neck",
            "bodyOptions": "body",
            "handsOptions": "hands",
            "ringOptions": "ring",
            "legsOptions": "legs",
            "feetOptions": "feet",
            "primaryWeaponOptions": "primaryWeapon",
            "offhandOptions": "offhand",
        }
        for option_field, gear_field in slot_field_map.items():
            options = [
                copy.deepcopy(item) if item is not None else None
                for item in getattr(gear_options, option_field, []) or []
            ]
            if options:
                setattr(gear, gear_field, rng.choice(options))

        inventory_options = [
            copy.deepcopy(item) for item in getattr(gear_options, "inventoryOptions", []) or [] if item is not None
        ]
        if inventory_options:
            max_inventory = min(3, len(inventory_options))
            inventory_count = rng.randint(0, max_inventory)
            gear.inventory = rng.sample(inventory_options, k=inventory_count)

        character.gear = gear
