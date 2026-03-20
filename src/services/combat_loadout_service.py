from __future__ import annotations

import copy
from typing import Callable

from src.domain.Character import Character
from src.domain.items import Weapon
from src.domain.Race import Race


def resolve_race_for_character(
    character: Character | None,
    race_lookup: Callable[[str], Race | None] | None = None,
) -> Race | None:
    if character is None or not callable(race_lookup):
        return None
    race_id = str(getattr(character, "race", "") or "").strip()
    if not race_id:
        return None
    return race_lookup(race_id)


def natural_weapons_for_character(
    character: Character | None,
    race_lookup: Callable[[str], Race | None] | None = None,
) -> list[Weapon]:
    race = resolve_race_for_character(character, race_lookup=race_lookup)
    if race is None:
        return []
    result: list[Weapon] = []
    for weapon in getattr(race, "naturalWeapons", []) or []:
        if isinstance(weapon, Weapon):
            result.append(weapon)
    return result


def prepare_natural_weapon_for_character(character: Character, weapon: Weapon) -> Weapon:
    prepared = copy.deepcopy(weapon)
    attributes = getattr(character, "finalAttributes", None) or getattr(character, "attributes", None)
    resistance_value = float(getattr(attributes, "physicalResistance", 0.0) or 0.0)
    prepared.penetrationBase = max(float(getattr(prepared, "penetrationBase", 0.0) or 0.0), resistance_value)
    return prepared


def select_natural_weapon(
    character: Character | None,
    race_lookup: Callable[[str], Race | None] | None = None,
) -> Weapon | None:
    if character is None:
        return None
    best_weapon: Weapon | None = None
    best_score = None
    for weapon in natural_weapons_for_character(character, race_lookup=race_lookup):
        prepared = prepare_natural_weapon_for_character(character, weapon)
        score = (
            float(getattr(prepared, "damageMax", 0.0) or 0.0),
            float(getattr(prepared, "damageMin", 0.0) or 0.0),
            float(getattr(prepared, "powerLevel", 0.0) or 0.0),
            float(getattr(prepared, "penetrationBase", 0.0) or 0.0),
        )
        if best_weapon is None or score > best_score:
            best_weapon = prepared
            best_score = score
    return best_weapon


def select_active_character_weapon(
    character: Character | None,
    race_lookup: Callable[[str], Race | None] | None = None,
) -> Weapon | None:
    if character is None:
        return None
    gear = getattr(character, "gear", None)
    if gear is not None:
        primary = getattr(gear, "primaryWeapon", None)
        if isinstance(primary, Weapon):
            return primary
        offhand = getattr(gear, "offhand", None)
        if isinstance(offhand, Weapon):
            return offhand
    return select_natural_weapon(character, race_lookup=race_lookup)
