from src.domain.character_util import Attribute, BonusType
from .forms import _safe_float, _safe_int


def _default_bonus_payload() -> dict:
    return {
        "bonusType": BonusType.FLAT.name,
        "attributeBonus": None,
        "affinities": None,
        "nanoMultiplier": 0.0,
        "reason": "",
        "permanent": False,
    }


def _normalize_bonus_payload(raw) -> dict:
    payload = _default_bonus_payload()
    if not isinstance(raw, dict):
        return payload

    bonus_type = str(raw.get("bonusType", BonusType.FLAT.name) or BonusType.FLAT.name).strip().upper()
    if bonus_type not in BonusType.__members__:
        bonus_type = BonusType.FLAT.name
    payload["bonusType"] = bonus_type

    attribute_bonus = raw.get("attributeBonus")
    if isinstance(attribute_bonus, dict):
        attr_name = str(attribute_bonus.get("attribute", "") or "").strip().upper()
        if attr_name in Attribute.__members__:
            payload["attributeBonus"] = {
                "attribute": attr_name,
                "bonus": _safe_int(attribute_bonus.get("bonus", 0), 0),
            }

    affinities = raw.get("affinities")
    if isinstance(affinities, dict):
        payload["affinities"] = {
            "chi": _safe_float(affinities.get("chi", 0.0), 0.0),
            "mana": _safe_float(affinities.get("mana", 0.0), 0.0),
            "psi": _safe_float(affinities.get("psi", 0.0), 0.0),
            "aether": _safe_float(affinities.get("aether", 0.0), 0.0),
        }

    payload["nanoMultiplier"] = _safe_float(raw.get("nanoMultiplier", 0.0), 0.0)
    payload["reason"] = str(raw.get("reason", "") or "")
    payload["permanent"] = bool(raw.get("permanent", False))
    return payload


def _normalize_buff_entry(raw) -> dict:
    if not isinstance(raw, dict):
        return {"duration": 0, "bonus": _default_bonus_payload()}

    return {
        "duration": max(0, _safe_int(raw.get("duration", 0), 0)),
        "bonus": _normalize_bonus_payload(raw.get("bonus")),
    }


def _normalize_achievement_entry(raw) -> dict:
    if not isinstance(raw, dict):
        return {"name": "", "title": "", "bonuses": []}

    bonuses = []
    raw_bonuses = raw.get("bonuses")
    if isinstance(raw_bonuses, list):
        bonuses = [_normalize_bonus_payload(entry) for entry in raw_bonuses if isinstance(entry, dict)]
    elif isinstance(raw.get("bonus"), dict):
        # Backward compatibility with earlier single-bonus achievement schema.
        bonuses = [_normalize_bonus_payload(raw.get("bonus"))]

    return {
        "name": str(raw.get("name", "") or ""),
        "title": str(raw.get("title", "") or ""),
        "description": str(raw.get("description", "") or ""),
        "bonuses": bonuses,
    }


def _bonus_summary_text(bonus: dict) -> str:
    normalized = _normalize_bonus_payload(bonus)
    attr = normalized.get("attributeBonus")
    if isinstance(attr, dict):
        attr_text = f"{attr.get('attribute', 'NONE')} {attr.get('bonus', 0)}"
    else:
        attr_text = "No Attribute"
    reason = str(normalized.get("reason", "") or "").strip() or "No Reason"
    permanence = "Permanent" if normalized.get("permanent") else "Temporary"
    return f"{normalized.get('bonusType', BonusType.FLAT.name)} | {attr_text} | {permanence} | {reason}"


def _summarize_bonus_list(bonuses: list[dict]) -> str:
    if not bonuses:
        return "No bonuses"
    if len(bonuses) == 1:
        return _bonus_summary_text(bonuses[0])
    return f"{len(bonuses)} bonuses (first: {_bonus_summary_text(bonuses[0])})"


def _list_bonus_lines(bonuses: list[dict]) -> str:
    if not bonuses:
        return "No bonuses"
    lines = []
    for index, bonus in enumerate(bonuses, start=1):
        lines.append(f"{index}. {_bonus_summary_text(bonus)}")
    return "\n".join(lines)


def _bonus_object_to_payload(bonus_obj) -> dict:
    if bonus_obj is None:
        return _default_bonus_payload()

    attribute_bonus = None
    raw_attribute_bonus = getattr(bonus_obj, "attributeBonus", None)
    if raw_attribute_bonus is not None and getattr(raw_attribute_bonus, "attribute", None) is not None:
        attribute_bonus = {
            "attribute": raw_attribute_bonus.attribute.name,
            "bonus": _safe_int(getattr(raw_attribute_bonus, "bonus", 0), 0),
        }

    affinities = None
    raw_affinities = getattr(bonus_obj, "affinities", None)
    if raw_affinities is not None:
        affinities = {
            "chi": _safe_float(getattr(raw_affinities, "chi", 0.0), 0.0),
            "mana": _safe_float(getattr(raw_affinities, "mana", 0.0), 0.0),
            "psi": _safe_float(getattr(raw_affinities, "psi", 0.0), 0.0),
            "aether": _safe_float(getattr(raw_affinities, "aether", 0.0), 0.0),
        }

    bonus_type = getattr(getattr(bonus_obj, "bonusType", None), "name", BonusType.FLAT.name)
    if bonus_type not in BonusType.__members__:
        bonus_type = BonusType.FLAT.name

    return {
        "bonusType": bonus_type,
        "attributeBonus": attribute_bonus,
        "affinities": affinities,
        "nanoMultiplier": _safe_float(getattr(bonus_obj, "nanoMultiplier", 0.0), 0.0),
        "reason": str(getattr(bonus_obj, "reason", "") or ""),
        "permanent": bool(getattr(bonus_obj, "permanent", False)),
    }


def _achievement_object_to_entry(achievement_obj) -> dict:
    bonuses = [
        _bonus_object_to_payload(entry) for entry in getattr(achievement_obj, "bonuses", []) if entry is not None
    ]
    return {
        "name": str(getattr(achievement_obj, "name", "") or ""),
        "title": str(getattr(achievement_obj, "title", "") or ""),
        "description": str(getattr(achievement_obj, "description", "") or ""),
        "bonuses": bonuses,
    }
