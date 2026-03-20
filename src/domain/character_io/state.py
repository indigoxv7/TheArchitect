from __future__ import annotations

from typing import Any, Callable

from src.domain.Character import Character, HealthState
from src.domain.character_util import FriendlyFireTolerance
from src.domain.items import Item
from src.domain.main_character import CharacterInfo, LLMControlProfile, MainCharacter
from src.domain.character_io.common import (
    _achievement_from_dict,
    _achievement_to_dict,
    _affinities_from_dict,
    _affinities_to_dict,
    _attributes_from_dict,
    _attributes_to_dict,
    _buff_from_dict,
    _buff_to_dict,
    _coerce_float,
    _coerce_int,
    _enum_from_name,
    _stats_from_dict,
    _stats_to_dict,
)
from src.domain.character_io.components import (
    _character_info_from_dict,
    _character_info_to_dict,
    _gear_from_dict,
    _gear_to_dict,
    _hobbies_from_list,
    _hobbies_to_list,
    _llm_control_profile_from_dict,
    _llm_control_profile_to_dict,
    _skills_from_list,
    _skills_to_list,
    _spells_from_list,
    _spells_to_list,
)


def character_to_state(character: Character) -> dict[str, Any]:
    return {
        "name": str(character.name or ""),
        "level": _coerce_int(character.level, 0),
        "characterType": "MainCharacter" if isinstance(character, MainCharacter) else "Character",
        "raceTier": str(character.raceTier or "Tier I"),
        "race": str(getattr(character, "race", "Human1") or "Human1"),
        "health": _coerce_float(character.health, 0.0),
        "healthState": character.healthState.name
        if isinstance(character.healthState, HealthState)
        else str(character.healthState),
        "activeAchievementTitle": str(getattr(character, "activeAchievementTitle", "") or ""),
        "attributes": _attributes_to_dict(character.attributes),
        "affinities": _affinities_to_dict(character.affinities),
        "gear": _gear_to_dict(character.gear),
        "achievements": [_achievement_to_dict(a) for a in (character.achievements or [])],
        "buffs": [_buff_to_dict(buff) for buff in (character.buffs or [])],
        "spells": _spells_to_list(getattr(character, "spells", [])),
        "generalSkills": _skills_to_list(getattr(character, "generalSkills", [])),
        "stats": _stats_to_dict(getattr(character, "stats", None)) if isinstance(character, MainCharacter) else None,
        "hobbies": _hobbies_to_list(getattr(character, "hobbies", None))
        if isinstance(character, MainCharacter)
        else [],
        "description": str(getattr(character, "description", "") or ""),
        "portraitURL": str(getattr(character, "portraitURL", "") or ""),
        "footerImageURL": str(getattr(character, "footerImageURL", "") or ""),
        "characterInfo": _character_info_to_dict(getattr(character, "characterInfo", None)),
        "llmControlProfile": _llm_control_profile_to_dict(getattr(character, "llmControlProfile", None)),
        "friendlyFireTolerance": getattr(
            getattr(character, "friendlyFireTolerance", FriendlyFireTolerance.NO_FRIENDLY_FIRE),
            "value",
            FriendlyFireTolerance.NO_FRIENDLY_FIRE.value,
        ),
    }


def character_from_state(
    data: dict[str, Any],
    item_resolver: Callable[[str], Item | None],
    error_item: Item | None = None,
) -> Character:
    if not isinstance(data, dict):
        raise ValueError("Character state must be a dictionary.")

    name = str(data.get("name", "") or "").strip()
    if not name:
        raise ValueError("Character state must include a non-empty name.")

    achievements = []
    raw_achievements = data.get("achievements", [])
    if isinstance(raw_achievements, list):
        for raw_achievement in raw_achievements:
            parsed = _achievement_from_dict(raw_achievement)
            if parsed is not None:
                achievements.append(parsed)

    buffs = []
    raw_buffs = data.get("buffs", [])
    if isinstance(raw_buffs, list):
        for raw_buff in raw_buffs:
            parsed = _buff_from_dict(raw_buff)
            if parsed is not None:
                buffs.append(parsed)

    character_info = _character_info_from_dict(data.get("characterInfo"))
    llm_control_profile = _llm_control_profile_from_dict(data.get("llmControlProfile"))
    character_kwargs = {
        "name": name,
        "attributes": _attributes_from_dict(data.get("attributes")),
        "level": _coerce_int(data.get("level", 0), 0),
        "raceTier": str(data.get("raceTier", "Tier I") or "Tier I"),
        "race": str(data.get("race", data.get("raceId", "Human1")) or "Human1"),
        "affinities": _affinities_from_dict(data.get("affinities")),
        "gear": _gear_from_dict(data.get("gear"), item_resolver, error_item),
        "achievements": achievements,
        "generalSkills": _skills_from_list(data.get("generalSkills", [])),
        "spells": _spells_from_list(data.get("spells", [])),
        "buffs": buffs,
        "friendlyFireTolerance": _enum_from_name(
            FriendlyFireTolerance,
            data.get("friendlyFireTolerance"),
            FriendlyFireTolerance.NO_FRIENDLY_FIRE,
        ),
    }

    character_type = str(data.get("characterType", "") or "").strip()
    if character_type == "MainCharacter" or character_info is not None:
        character = MainCharacter(
            characterInfo=character_info if character_info is not None else CharacterInfo(),
            llmControlProfile=llm_control_profile if llm_control_profile is not None else LLMControlProfile(),
            stats=_stats_from_dict(data.get("stats")),
            hobbies=_hobbies_from_list(data.get("hobbies")),
            **character_kwargs,
        )
    else:
        character = Character(**character_kwargs)

    if "health" in data:
        character.health = _coerce_float(data.get("health", character.GetMaxHealth()), character.GetMaxHealth())
    else:
        character.health = character.GetMaxHealth()
    character.healthState = _enum_from_name(HealthState, data.get("healthState"), HealthState.HEALTHY)
    character.activeAchievementTitle = str(data.get("activeAchievementTitle", "") or "")
    character.description = str(data.get("description", "") or "")
    character.portraitURL = str(data.get("portraitURL", "") or "")
    character.footerImageURL = str(data.get("footerImageURL", "") or "")
    character.CalculateBonus()
    return character
