from __future__ import annotations

from typing import Any, Callable

from src.domain.Character import Buff, Character, HealthState
from src.domain.MainCharacter import CharacterInfo, MainCharacter
from src.domain.CharacterUtil import (
    Achievement,
    Affinities,
    Attribute,
    AttributeBonus,
    Attributes,
    Bonus,
    BonusType,
    CharacterStatistics,
)
from src.domain.GeneralSkills import GeneralSkills
from src.domain.Items import Gear, Item
from src.domain.Spells import Spell


def _enum_from_name(enum_cls, value: Any, default):
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized in enum_cls.__members__:
            return enum_cls[normalized]
    return default


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _attributes_to_dict(attributes: Attributes | None) -> dict[str, Any]:
    if attributes is None:
        return {
            "physicalPower": 5,
            "physicalStamina": 5,
            "physicalResistance": 5,
            "magicPower": 5,
            "magicStamina": 5,
            "magicResistance": 5,
        }

    return {
        "physicalPower": _coerce_float(attributes.physicalPower, 5),
        "physicalStamina": _coerce_float(attributes.physicalStamina, 5),
        "physicalResistance": _coerce_float(attributes.physicalResistance, 5),
        "magicPower": _coerce_float(attributes.magicPower, 5),
        "magicStamina": _coerce_float(attributes.magicStamina, 5),
        "magicResistance": _coerce_float(attributes.magicResistance, 5),
    }


def _attributes_from_dict(data: Any) -> Attributes:
    if not isinstance(data, dict):
        return Attributes()

    return Attributes(
        physicalPower=_coerce_float(data.get("physicalPower", 5), 5),
        physicalStamina=_coerce_float(data.get("physicalStamina", 5), 5),
        physicalResistance=_coerce_float(data.get("physicalResistance", 5), 5),
        magicPower=_coerce_float(data.get("magicPower", 5), 5),
        magicStamina=_coerce_float(data.get("magicStamina", 5), 5),
        magicResistance=_coerce_float(data.get("magicResistance", 5), 5),
    )


def _affinities_to_dict(affinities: Affinities | None) -> dict[str, Any]:
    if affinities is None:
        return {"chi": 0.5, "mana": 0.5, "psi": 0.5, "aether": 0.5}

    return {
        "chi": _coerce_float(affinities.chi, 0.5),
        "mana": _coerce_float(affinities.mana, 0.5),
        "psi": _coerce_float(affinities.psi, 0.5),
        "aether": _coerce_float(affinities.aether, 0.5),
    }


def _affinities_from_dict(data: Any) -> Affinities:
    if not isinstance(data, dict):
        return Affinities()

    return Affinities(
        chi=_coerce_float(data.get("chi", 0.5), 0.5),
        mana=_coerce_float(data.get("mana", 0.5), 0.5),
        psi=_coerce_float(data.get("psi", 0.5), 0.5),
        aether=_coerce_float(data.get("aether", 0.5), 0.5),
    )


def _attribute_bonus_to_dict(attribute_bonus: AttributeBonus | None) -> dict[str, Any] | None:
    if attribute_bonus is None:
        return None

    return {
        "attribute": attribute_bonus.attribute.name,
        "bonus": _coerce_int(attribute_bonus.bonus, 0),
    }


def _attribute_bonus_from_dict(data: Any) -> AttributeBonus | None:
    if not isinstance(data, dict):
        return None

    attribute = _enum_from_name(Attribute, data.get("attribute"), None)
    if attribute is None:
        return None

    return AttributeBonus(attribute=attribute, bonus=_coerce_int(data.get("bonus", 0), 0))


def _bonus_to_dict(bonus: Bonus | None) -> dict[str, Any] | None:
    if bonus is None:
        return None

    return {
        "bonusType": bonus.bonusType.name,
        "attributeBonus": _attribute_bonus_to_dict(bonus.attributeBonus),
        "affinities": _affinities_to_dict(bonus.affinities) if bonus.affinities is not None else None,
        "nanoMultiplier": _coerce_float(bonus.nanoMultiplier, 0.0),
        "reason": str(bonus.reason or ""),
        "permanent": bool(bonus.permanent),
    }


def _bonus_from_dict(data: Any) -> Bonus | None:
    if not isinstance(data, dict):
        return None

    bonus_type = _enum_from_name(BonusType, data.get("bonusType"), BonusType.FLAT)
    return Bonus(
        bonusType=bonus_type,
        attributeBonus=_attribute_bonus_from_dict(data.get("attributeBonus")),
        affinities=_affinities_from_dict(data.get("affinities")) if isinstance(data.get("affinities"), dict) else None,
        nanoMultiplier=_coerce_float(data.get("nanoMultiplier", 0.0), 0.0),
        reason=str(data.get("reason", "") or ""),
        permanent=bool(data.get("permanent", False)),
    )


def _achievement_to_dict(achievement: Achievement) -> dict[str, Any]:
    bonuses = [_bonus_to_dict(entry) for entry in getattr(achievement, "bonuses", []) if entry is not None]
    first_bonus = bonuses[0] if bonuses else None
    return {
        "name": str(achievement.name or ""),
        "title": str(achievement.title or ""),
        "description": str(getattr(achievement, "description", "") or ""),
        "bonuses": bonuses,
        # Backward compatibility for older readers expecting a single bonus field.
        "bonus": first_bonus,
    }


def _achievement_from_dict(data: Any) -> Achievement | None:
    if not isinstance(data, dict):
        return None

    name = str(data.get("name", "") or "").strip()
    if not name:
        return None

    bonuses: list[Bonus] = []
    raw_bonuses = data.get("bonuses")
    if isinstance(raw_bonuses, list):
        for raw_bonus in raw_bonuses:
            parsed_bonus = _bonus_from_dict(raw_bonus)
            if parsed_bonus is not None:
                bonuses.append(parsed_bonus)
    else:
        # Backward compatibility: legacy single `bonus` field.
        parsed_bonus = _bonus_from_dict(data.get("bonus"))
        if parsed_bonus is not None:
            bonuses.append(parsed_bonus)

    return Achievement(
        name=name,
        bonuses=bonuses,
        title=str(data.get("title", "") or ""),
        description=str(data.get("description", "") or ""),
    )


def _buff_to_dict(buff: Buff) -> dict[str, Any]:
    return {
        "duration": _coerce_int(buff.duration, 0),
        "bonus": _bonus_to_dict(buff.bonus),
    }


def _buff_from_dict(data: Any) -> Buff | None:
    if not isinstance(data, dict):
        return None

    bonus = _bonus_from_dict(data.get("bonus"))
    if bonus is None:
        return None

    return Buff(bonus=bonus, duration=_coerce_int(data.get("duration", 0), 0))


def _stats_to_dict(stats: CharacterStatistics | None) -> dict[str, Any] | None:
    if stats is None:
        return None

    return {
        "kills": _coerce_int(stats.kills, 0),
        "damageTaken": _coerce_int(stats.damageTaken, 0),
        "missionCount": _coerce_int(stats.missionCount, 0),
    }


def _stats_from_dict(data: Any) -> CharacterStatistics | None:
    if not isinstance(data, dict):
        return None

    return CharacterStatistics(
        kills=_coerce_int(data.get("kills", 0), 0),
        damageTaken=_coerce_int(data.get("damageTaken", 0), 0),
        missionCount=_coerce_int(data.get("missionCount", 0), 0),
    )


def _skills_to_list(general_skills: list[GeneralSkills] | None) -> list[dict[str, Any]]:
    if not general_skills:
        return []

    result = []
    for skill in general_skills:
        result.append({"name": str(skill.name or ""), "description": str(skill.description or "")})
    return result


def _skills_from_list(data: Any) -> list[GeneralSkills]:
    if not isinstance(data, list):
        return []

    result = []
    for item in data:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "") or "").strip()
        description = str(item.get("description", "") or "")
        if not name:
            continue
        result.append(GeneralSkills(name, description))
    return result


def _spells_to_list(spells: list[Spell] | None) -> list[dict[str, Any]]:
    if not spells:
        return []

    result = []
    for spell in spells:
        try:
            result.append(spell.to_dict())
        except Exception:
            continue
    return result


def _spells_from_list(data: Any) -> list[Spell]:
    if not isinstance(data, list):
        return []

    result = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            result.append(Spell.from_dict(item))
        except Exception:
            continue
    return result


def _item_to_ref(item: Item | None) -> str | None:
    if item is None:
        return None

    item_id = getattr(item, "itemId", None)
    if item_id:
        return str(item_id)
    return None


def _gear_to_dict(gear: Gear | None) -> dict[str, Any]:
    if gear is None:
        return {
            "head_item_id": None,
            "neck_item_id": None,
            "body_item_id": None,
            "hands_item_id": None,
            "ring_item_id": None,
            "legs_item_id": None,
            "feet_item_id": None,
            "primary_weapon_item_id": None,
            "offhand_item_id": None,
            "inventory_item_ids": [],
        }

    return {
        "head_item_id": _item_to_ref(gear.head),
        "neck_item_id": _item_to_ref(gear.neck),
        "body_item_id": _item_to_ref(gear.body),
        "hands_item_id": _item_to_ref(gear.hands),
        "ring_item_id": _item_to_ref(gear.ring),
        "legs_item_id": _item_to_ref(gear.legs),
        "feet_item_id": _item_to_ref(gear.feet),
        "primary_weapon_item_id": _item_to_ref(gear.primaryWeapon),
        "offhand_item_id": _item_to_ref(gear.offhand),
        "inventory_item_ids": [_item_to_ref(item) for item in gear.inventory if _item_to_ref(item)],
    }


def _resolve_item(item_id: Any, item_resolver: Callable[[str], Item | None], error_item: Item | None) -> Item | None:
    if not item_id:
        return None

    item = item_resolver(str(item_id))
    if item is None:
        return error_item
    return item


def _gear_from_dict(data: Any, item_resolver: Callable[[str], Item | None], error_item: Item | None) -> Gear:
    if not isinstance(data, dict):
        return Gear()

    inventory_ids = data.get("inventory_item_ids", [])
    inventory = []
    if isinstance(inventory_ids, list):
        for item_id in inventory_ids:
            resolved = _resolve_item(item_id, item_resolver, error_item)
            if resolved is not None:
                inventory.append(resolved)

    return Gear(
        head=_resolve_item(data.get("head_item_id"), item_resolver, error_item),
        neck=_resolve_item(data.get("neck_item_id"), item_resolver, error_item),
        body=_resolve_item(data.get("body_item_id"), item_resolver, error_item),
        hands=_resolve_item(data.get("hands_item_id"), item_resolver, error_item),
        ring=_resolve_item(data.get("ring_item_id"), item_resolver, error_item),
        legs=_resolve_item(data.get("legs_item_id"), item_resolver, error_item),
        feet=_resolve_item(data.get("feet_item_id"), item_resolver, error_item),
        primaryWeapon=_resolve_item(data.get("primary_weapon_item_id"), item_resolver, error_item),
        offhand=_resolve_item(data.get("offhand_item_id"), item_resolver, error_item),
        inventory=inventory,
    )




def _character_info_to_dict(character_info: CharacterInfo | None) -> dict[str, Any] | None:
    if character_info is None:
        return None
    return character_info.to_dict()


def _character_info_from_dict(data: Any) -> CharacterInfo | None:
    if not isinstance(data, dict):
        return None
    return CharacterInfo.from_dict(data)

def character_to_state(character: Character) -> dict[str, Any]:
    return {
        "name": str(character.name or ""),
        "level": _coerce_int(character.level, 0),
        "characterType": "MainCharacter" if isinstance(character, MainCharacter) else "Character",
        "raceTier": str(character.raceTier or "Tier I"),
        "race": str(getattr(character, "race", "Human1") or "Human1"),
        "party": _coerce_int(character.party, 0),
        "health": _coerce_int(character.health, 100),
        "healthState": character.healthState.name if isinstance(character.healthState, HealthState) else str(character.healthState),
        "activeAchievementTitle": str(getattr(character, "activeAchievementTitle", "") or ""),
        "attributes": _attributes_to_dict(character.attributes),
        "affinities": _affinities_to_dict(character.affinities),
        "gear": _gear_to_dict(character.gear),
        "achievements": [_achievement_to_dict(a) for a in (character.achievements or [])],
        "buffs": [_buff_to_dict(buff) for buff in (character.buffs or [])],
        "spells": _spells_to_list(getattr(character, "spells", [])),
        "generalSkills": _skills_to_list(getattr(character, "generalSkills", [])),
        "stats": _stats_to_dict(getattr(character, "stats", None)),
        "description": str(getattr(character, "description", "") or ""),
        "portraitURL": str(getattr(character, "portraitURL", "") or ""),
        "footerImageURL": str(getattr(character, "footerImageURL", "") or ""),
        "characterInfo": _character_info_to_dict(getattr(character, "characterInfo", None)),
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

    attributes = _attributes_from_dict(data.get("attributes"))
    affinities = _affinities_from_dict(data.get("affinities"))
    gear = _gear_from_dict(data.get("gear"), item_resolver, error_item)

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

    general_skills = _skills_from_list(data.get("generalSkills", []))
    spells = _spells_from_list(data.get("spells", []))
    stats = _stats_from_dict(data.get("stats"))
    description = str(data.get("description", "") or "")
    portrait_url = str(data.get("portraitURL", "") or "")
    footer_image_url = str(data.get("footerImageURL", "") or "")

    character_type = str(data.get("characterType", "") or "").strip()
    character_info = _character_info_from_dict(data.get("characterInfo"))
    character_kwargs = {
        "name": name,
        "attributes": attributes,
        "level": _coerce_int(data.get("level", 0), 0),
        "raceTier": str(data.get("raceTier", "Tier I") or "Tier I"),
        "race": str(data.get("race", data.get("raceId", "Human1")) or "Human1"),
        "affinities": affinities,
        "gear": gear,
        "achievements": achievements,
        "generalSkills": general_skills,
        "spells": spells,
        "party": _coerce_int(data.get("party", 0), 0),
        "buffs": buffs,
        "stats": stats,
    }

    if character_type == "MainCharacter" or character_info is not None:
        character = MainCharacter(
            characterInfo=character_info if character_info is not None else CharacterInfo(),
            **character_kwargs,
        )
    else:
        character = Character(**character_kwargs)

    character.health = _coerce_int(data.get("health", 100), 100)
    character.healthState = _enum_from_name(HealthState, data.get("healthState"), HealthState.HEALTHY)
    character.activeAchievementTitle = str(data.get("activeAchievementTitle", "") or "")
    character.description = description
    character.portraitURL = portrait_url
    character.footerImageURL = footer_image_url

    character.CalculateBonus()
    return character

