from __future__ import annotations

from enum import Enum
from typing import Any, Callable

from src.domain.Character import Character
from src.domain.character_util import Attributes
from src.domain.items import Weapon
from src.domain.spells import Spell
from src.domain.gear_options import GearOptions


class CreatureSize(Enum):
    TINY = 0
    SMALL = 1
    STANDARD = 2
    LARGE = 3
    GIANT = 5


class Race:
    def __init__(
        self,
        name: str,
        detailedDescription: str = "",
        beifDescription: str = "",
        juvenileNomenclature: str = "young",
        size: CreatureSize = CreatureSize.STANDARD,
        averageSpecimine: Character | None = None,
        maxAverageAttributes: Attributes | None = None,
        minAverageAttributes: Attributes | None = None,
        spellList: list[list[Spell]] | None = None,
        FamedEnemyList: list[Character] | None = None,
        gearOptions: GearOptions | None = None,
        naturalWeapons: list[Weapon] | None = None,
        raceId: str = "",
    ):
        self.name = str(name or "")
        self.detailedDescription = str(detailedDescription or "")
        self.beifDescription = str(beifDescription or "")
        self.juvenileNomenclature = str(juvenileNomenclature or "young")
        self.size = size if isinstance(size, CreatureSize) else CreatureSize.STANDARD
        self.averageSpecimine = averageSpecimine
        self.maxAverageAttributes = maxAverageAttributes if maxAverageAttributes is not None else Attributes()
        self.minAverageAttributes = minAverageAttributes if minAverageAttributes is not None else Attributes()
        self.spellList = self._normalize_spell_list(spellList)
        self.FamedEnemyList = [entry for entry in (FamedEnemyList or []) if entry is not None]
        self.gearOptions = gearOptions if isinstance(gearOptions, GearOptions) else GearOptions()
        self.naturalWeapons = [weapon for weapon in (naturalWeapons or []) if isinstance(weapon, Weapon)]
        self.raceId = str(raceId or "")

    @staticmethod
    def _coerce_size(value: Any) -> CreatureSize:
        if isinstance(value, CreatureSize):
            return value

        if isinstance(value, str):
            text = value.strip()
            if not text:
                return CreatureSize.STANDARD
            if text in CreatureSize.__members__:
                return CreatureSize[text]
            upper = text.upper()
            if upper in CreatureSize.__members__:
                return CreatureSize[upper]
            for entry in CreatureSize:
                if entry.name.lower() == text.lower():
                    return entry
        try:
            numeric = int(value)
        except Exception:
            return CreatureSize.STANDARD

        for entry in CreatureSize:
            if entry.value == numeric:
                return entry
        return CreatureSize.STANDARD

    @staticmethod
    def _normalize_spell_list(spell_list: Any) -> list[list[Spell]]:
        normalized: list[list[Spell]] = [[] for _ in range(21)]
        if not isinstance(spell_list, list):
            return normalized

        for level, entries in enumerate(spell_list[:21]):
            if not isinstance(entries, list):
                continue
            level_entries: list[Spell] = []
            for spell in entries:
                if isinstance(spell, Spell):
                    level_entries.append(spell)
            normalized[level] = level_entries
        return normalized

    @staticmethod
    def _attributes_to_dict(attributes: Attributes | None) -> dict[str, Any]:
        attributes = attributes if attributes is not None else Attributes()
        return {
            "physicalPower": float(getattr(attributes, "physicalPower", 5)),
            "physicalStamina": float(getattr(attributes, "physicalStamina", 5)),
            "physicalResistance": float(getattr(attributes, "physicalResistance", 5)),
            "magicPower": float(getattr(attributes, "magicPower", 5)),
            "magicStamina": float(getattr(attributes, "magicStamina", 5)),
            "magicResistance": float(getattr(attributes, "magicResistance", 5)),
        }

    @staticmethod
    def _attributes_from_dict(data: Any) -> Attributes:
        if not isinstance(data, dict):
            return Attributes()

        def _coerce(value: Any, default: float = 5.0) -> float:
            try:
                return float(value)
            except Exception:
                return default

        return Attributes(
            physicalPower=_coerce(data.get("physicalPower", 5.0)),
            physicalStamina=_coerce(data.get("physicalStamina", 5.0)),
            physicalResistance=_coerce(data.get("physicalResistance", 5.0)),
            magicPower=_coerce(data.get("magicPower", 5.0)),
            magicStamina=_coerce(data.get("magicStamina", 5.0)),
            magicResistance=_coerce(data.get("magicResistance", 5.0)),
        )

    def to_dict(
        self,
        resolve_character_id: Callable[[Character], str | None] | None = None,
        resolve_item_id: Callable[[Any], str | None] | None = None,
    ) -> dict[str, Any]:
        average_id = None
        if callable(resolve_character_id) and self.averageSpecimine is not None:
            average_id = resolve_character_id(self.averageSpecimine)

        famed_ids: list[str] = []
        if callable(resolve_character_id):
            for entry in self.FamedEnemyList:
                character_id = resolve_character_id(entry)
                if character_id:
                    famed_ids.append(character_id)

        spell_names = []
        for level_entries in self.spellList:
            names = []
            for spell in level_entries:
                if spell is not None and getattr(spell, "name", ""):
                    names.append(str(spell.name))
            spell_names.append(names)

        return {
            "raceId": self.raceId,
            "name": self.name,
            "detailedDescription": self.detailedDescription,
            "beifDescription": self.beifDescription,
            "juvenileNomenclature": self.juvenileNomenclature,
            "size": self.size.name,
            "averageSpecimineCharacterId": average_id,
            "maxAverageAttributes": self._attributes_to_dict(self.maxAverageAttributes),
            "minAverageAttributes": self._attributes_to_dict(self.minAverageAttributes),
            "spellList": spell_names,
            "famedEnemyCharacterIds": famed_ids,
            "gearOptions": self.gearOptions.to_dict(resolve_item_id=resolve_item_id),
            "naturalWeaponItemIds": [
                item_id
                for item_id in [
                    resolve_item_id(weapon) if callable(resolve_item_id) else None for weapon in self.naturalWeapons
                ]
                if item_id
            ],
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        resolve_character: Callable[[str], Character | None] | None = None,
        resolve_spell: Callable[[str], Spell | None] | None = None,
        resolve_item: Callable[[str], Any] | None = None,
    ) -> "Race":
        if not isinstance(data, dict):
            raise ValueError("Race data must be a dictionary.")

        name = str(data.get("name", "") or "").strip()
        if not name:
            raise ValueError("Race data must include a non-empty name.")

        average_character: Character | None = None
        average_id = str(
            data.get("averageSpecimineCharacterId")
            or data.get("averageSpecimineId")
            or data.get("averageSpecimine")
            or ""
        ).strip()
        if average_id and callable(resolve_character):
            average_character = resolve_character(average_id)

        famed_enemy_entries = data.get("famedEnemyCharacterIds", data.get("FamedEnemyList", []))
        famed_enemies: list[Character] = []
        if isinstance(famed_enemy_entries, list) and callable(resolve_character):
            for entry in famed_enemy_entries:
                character_id = str(entry or "").strip()
                if not character_id:
                    continue
                resolved = resolve_character(character_id)
                if resolved is not None:
                    famed_enemies.append(resolved)

        raw_spell_list = data.get("spellList", [])
        spell_list: list[list[Spell]] = [[] for _ in range(21)]
        if isinstance(raw_spell_list, list):
            for level, entries in enumerate(raw_spell_list[:21]):
                if not isinstance(entries, list):
                    continue
                resolved_entries: list[Spell] = []
                for entry in entries:
                    if isinstance(entry, Spell):
                        resolved_entries.append(entry)
                        continue
                    if isinstance(entry, dict):
                        spell_name = str(entry.get("name", "") or "").strip()
                    else:
                        spell_name = str(entry or "").strip()
                    if not spell_name or not callable(resolve_spell):
                        continue
                    resolved_spell = resolve_spell(spell_name)
                    if resolved_spell is not None:
                        resolved_entries.append(resolved_spell)
                spell_list[level] = resolved_entries

        beif_description = str(data.get("beifDescription", data.get("briefDescription", "")) or "")

        natural_weapons: list[Weapon] = []
        raw_natural_weapon_ids = data.get("naturalWeaponItemIds", data.get("naturalWeapons", []))
        if isinstance(raw_natural_weapon_ids, list) and callable(resolve_item):
            for entry in raw_natural_weapon_ids:
                if isinstance(entry, Weapon):
                    natural_weapons.append(entry)
                    continue
                item_id = str(entry or "").strip()
                if not item_id:
                    continue
                resolved_item = resolve_item(item_id)
                if isinstance(resolved_item, Weapon):
                    natural_weapons.append(resolved_item)

        return cls(
            name=name,
            detailedDescription=str(data.get("detailedDescription", "") or ""),
            beifDescription=beif_description,
            juvenileNomenclature=str(data.get("juvenileNomenclature", "young") or "young"),
            size=cls._coerce_size(data.get("size", CreatureSize.STANDARD.name)),
            averageSpecimine=average_character,
            maxAverageAttributes=cls._attributes_from_dict(data.get("maxAverageAttributes")),
            minAverageAttributes=cls._attributes_from_dict(data.get("minAverageAttributes")),
            spellList=spell_list,
            FamedEnemyList=famed_enemies,
            gearOptions=GearOptions.from_dict(data.get("gearOptions"), resolve_item=resolve_item),
            naturalWeapons=natural_weapons,
            raceId=str(data.get("raceId", "") or ""),
        )
