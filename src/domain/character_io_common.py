from __future__ import annotations

from typing import Any

from src.domain.Character import Buff
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


def _enum_from_name(enum_cls, value: Any, default):
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized in enum_cls.__members__:
            return enum_cls[normalized]
        lowered = value.strip().lower()
        for entry in enum_cls:
            if str(getattr(entry, "value", "")).strip().lower() == lowered:
                return entry
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
    return Bonus(
        bonusType=_enum_from_name(BonusType, data.get("bonusType"), BonusType.FLAT),
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
        "kills": _coerce_int(getattr(stats, "kills", 0), 0),
        "damageTaken": _coerce_float(getattr(stats, "damageTaken", 0.0), 0.0),
        "missionCount": _coerce_int(getattr(stats, "missionCount", 0), 0),
        "damageDone": _coerce_float(getattr(stats, "damageDone", 0.0), 0.0),
        "spellsCast": _coerce_int(getattr(stats, "spellsCast", 0), 0),
        "injuriesTaken": _coerce_int(getattr(stats, "injuriesTaken", 0), 0),
        "alliesProtected": _coerce_int(getattr(stats, "alliesProtected", 0), 0),
        "bossesKilled": _coerce_int(getattr(stats, "bossesKilled", 0), 0),
        "elitesKilled": _coerce_int(getattr(stats, "elitesKilled", 0), 0),
        "unitsKilled": {
            str(key): _coerce_int(value, 0)
            for key, value in dict(getattr(stats, "unitsKilled", {}) or {}).items()
            if str(key or "").strip() and _coerce_int(value, 0) > 0
        },
    }


def _stats_from_dict(data: Any) -> CharacterStatistics | None:
    if not isinstance(data, dict):
        return None
    return CharacterStatistics(
        kills=_coerce_int(data.get("kills", 0), 0),
        damageTaken=_coerce_float(data.get("damageTaken", 0.0), 0.0),
        missionCount=_coerce_int(data.get("missionCount", 0), 0),
        damageDone=_coerce_float(data.get("damageDone", 0.0), 0.0),
        spellsCast=_coerce_int(data.get("spellsCast", 0), 0),
        injuriesTaken=_coerce_int(data.get("injuriesTaken", 0), 0),
        alliesProtected=_coerce_int(data.get("alliesProtected", 0), 0),
        bossesKilled=_coerce_int(data.get("bossesKilled", 0), 0),
        elitesKilled=_coerce_int(data.get("elitesKilled", 0), 0),
        unitsKilled=data.get("unitsKilled", {}),
    )
