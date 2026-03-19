from __future__ import annotations

from typing import Any, Callable

from src.domain.character import Character
from src.domain.character_util import Attributes
from src.domain.race import CreatureSize, Race
from src.domain.spells import Spell
from src.domain.gear_options import GearOptions


class Unit:
    def __init__(
        self,
        baseRaceId: str,
        name: str | None = None,
        detailedDescription: str | None = None,
        beifDescription: str | None = None,
        juvenileNomenclature: str | None = None,
        size: CreatureSize | None = None,
        averageSpecimine: Character | None = None,
        maxAverageAttributes: Attributes | None = None,
        minAverageAttributes: Attributes | None = None,
        spellList: list[list[Spell]] | None = None,
        FamedEnemyList: list[Character] | None = None,
        gearOptions: GearOptions | None = None,
        unitId: str = "",
    ):
        self.baseRaceId = str(baseRaceId or "").strip()
        self.name = None if name is None else str(name or "")
        self.detailedDescription = None if detailedDescription is None else str(detailedDescription or "")
        self.beifDescription = None if beifDescription is None else str(beifDescription or "")
        self.juvenileNomenclature = None if juvenileNomenclature is None else str(juvenileNomenclature or "")
        self.size = size if isinstance(size, CreatureSize) else None
        self.averageSpecimine = averageSpecimine
        self.maxAverageAttributes = maxAverageAttributes
        self.minAverageAttributes = minAverageAttributes
        self.spellList = self._normalize_optional_spell_list(spellList)
        self.FamedEnemyList = None if FamedEnemyList is None else [entry for entry in FamedEnemyList if entry is not None]
        self.gearOptions = gearOptions if isinstance(gearOptions, GearOptions) else None
        self.unitId = str(unitId or "")

    @staticmethod
    def _normalize_optional_spell_list(spell_list: Any) -> list[list[Spell]] | None:
        if spell_list is None:
            return None
        return Race._normalize_spell_list(spell_list)

    def get_effective_value(self, field_name: str, base_race: Race):
        value = getattr(self, field_name)
        if value is not None:
            return value
        return getattr(base_race, field_name)

    def to_effective_race(self, base_race: Race) -> Race:
        return Race(
            name=self.get_effective_value("name", base_race),
            detailedDescription=self.get_effective_value("detailedDescription", base_race),
            beifDescription=self.get_effective_value("beifDescription", base_race),
            juvenileNomenclature=self.get_effective_value("juvenileNomenclature", base_race),
            size=self.get_effective_value("size", base_race),
            averageSpecimine=self.get_effective_value("averageSpecimine", base_race),
            maxAverageAttributes=self.get_effective_value("maxAverageAttributes", base_race),
            minAverageAttributes=self.get_effective_value("minAverageAttributes", base_race),
            spellList=self.get_effective_value("spellList", base_race),
            FamedEnemyList=self.get_effective_value("FamedEnemyList", base_race),
            gearOptions=self.get_effective_value("gearOptions", base_race),
            raceId=base_race.raceId,
        )

    def to_dict(
        self,
        resolve_character_id: Callable[[Character], str | None] | None = None,
        resolve_item_id: Callable[[Any], str | None] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "unitId": self.unitId,
            "baseRaceId": self.baseRaceId,
        }

        if self.name is not None:
            payload["name"] = self.name
        if self.detailedDescription is not None:
            payload["detailedDescription"] = self.detailedDescription
        if self.beifDescription is not None:
            payload["beifDescription"] = self.beifDescription
        if self.juvenileNomenclature is not None:
            payload["juvenileNomenclature"] = self.juvenileNomenclature
        if self.size is not None:
            payload["size"] = self.size.name

        if self.averageSpecimine is not None and callable(resolve_character_id):
            payload["averageSpecimineCharacterId"] = resolve_character_id(self.averageSpecimine)

        if self.maxAverageAttributes is not None:
            payload["maxAverageAttributes"] = Race._attributes_to_dict(self.maxAverageAttributes)
        if self.minAverageAttributes is not None:
            payload["minAverageAttributes"] = Race._attributes_to_dict(self.minAverageAttributes)

        if self.spellList is not None:
            spell_names = []
            for level_entries in self.spellList:
                names = []
                for spell in level_entries:
                    spell_name = str(getattr(spell, "name", "") or "").strip()
                    if spell_name:
                        names.append(spell_name)
                spell_names.append(names)
            payload["spellList"] = spell_names

        if self.FamedEnemyList is not None and callable(resolve_character_id):
            payload["famedEnemyCharacterIds"] = [
                character_id
                for character_id in [resolve_character_id(character) for character in self.FamedEnemyList]
                if character_id
            ]

        if self.gearOptions is not None:
            payload["gearOptions"] = self.gearOptions.to_dict(resolve_item_id=resolve_item_id)

        return payload

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        resolve_character: Callable[[str], Character | None] | None = None,
        resolve_spell: Callable[[str], Spell | None] | None = None,
        resolve_item: Callable[[str], Any] | None = None,
    ) -> "Unit":
        if not isinstance(data, dict):
            raise ValueError("Unit data must be a dictionary.")

        base_race_id = str(data.get("baseRaceId", "") or "").strip()
        if not base_race_id:
            raise ValueError("Unit data must include a baseRaceId.")

        average_specimine = None
        if "averageSpecimineCharacterId" in data and callable(resolve_character):
            character_id = str(data.get("averageSpecimineCharacterId", "") or "").strip()
            if character_id:
                average_specimine = resolve_character(character_id)

        famed_enemy_list = None
        if "famedEnemyCharacterIds" in data:
            famed_enemy_list = []
            if callable(resolve_character):
                for entry in data.get("famedEnemyCharacterIds", []) or []:
                    character_id = str(entry or "").strip()
                    if not character_id:
                        continue
                    resolved = resolve_character(character_id)
                    if resolved is not None:
                        famed_enemy_list.append(resolved)

        spell_list = None
        if "spellList" in data:
            spell_list = [[] for _ in range(21)]
            raw_spell_list = data.get("spellList", [])
            if isinstance(raw_spell_list, list):
                for level, entries in enumerate(raw_spell_list[:21]):
                    if not isinstance(entries, list):
                        continue
                    resolved_entries: list[Spell] = []
                    for entry in entries:
                        if isinstance(entry, Spell):
                            resolved_entries.append(entry)
                            continue
                        spell_name = str(entry or "").strip()
                        if not spell_name or not callable(resolve_spell):
                            continue
                        resolved_spell = resolve_spell(spell_name)
                        if resolved_spell is not None:
                            resolved_entries.append(resolved_spell)
                    spell_list[level] = resolved_entries

        size = None
        if "size" in data and data.get("size") is not None:
            size = Race._coerce_size(data.get("size"))

        beif_description = None
        if "beifDescription" in data or "briefDescription" in data:
            beif_description = str(data.get("beifDescription", data.get("briefDescription", "")) or "")

        max_average_attributes = None
        if "maxAverageAttributes" in data:
            max_average_attributes = Race._attributes_from_dict(data.get("maxAverageAttributes"))

        min_average_attributes = None
        if "minAverageAttributes" in data:
            min_average_attributes = Race._attributes_from_dict(data.get("minAverageAttributes"))

        gear_options = None
        if "gearOptions" in data:
            gear_options = GearOptions.from_dict(data.get("gearOptions"), resolve_item=resolve_item)

        return cls(
            baseRaceId=base_race_id,
            name=data.get("name") if "name" in data else None,
            detailedDescription=data.get("detailedDescription") if "detailedDescription" in data else None,
            beifDescription=beif_description,
            juvenileNomenclature=data.get("juvenileNomenclature") if "juvenileNomenclature" in data else None,
            size=size,
            averageSpecimine=average_specimine,
            maxAverageAttributes=max_average_attributes,
            minAverageAttributes=min_average_attributes,
            spellList=spell_list,
            FamedEnemyList=famed_enemy_list,
            gearOptions=gear_options,
            unitId=str(data.get("unitId", "") or ""),
        )

