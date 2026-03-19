from __future__ import annotations

from typing import Any, Callable

from src.domain.GeneralSkills import GeneralSkills
from src.domain.Items import Gear, Item
from src.domain.MainCharacter import CharacterInfo, HobbyInterestLevel, LLMControlProfile
from src.domain.Spells import Spell
from src.domain.character_io_common import _enum_from_name


def _hobbies_to_list(hobbies: list[tuple[str, HobbyInterestLevel]] | None) -> list[dict[str, Any]]:
    if not hobbies:
        return []
    result = []
    for hobby_name, interest_level in hobbies:
        if not str(hobby_name or "").strip():
            continue
        result.append(
            {
                "name": str(hobby_name or ""),
                "interestLevel": getattr(interest_level, "value", HobbyInterestLevel.INDIFFERENT.value),
            }
        )
    return result


def _hobbies_from_list(data: Any) -> list[tuple[str, HobbyInterestLevel]]:
    if not isinstance(data, list):
        return []
    result: list[tuple[str, HobbyInterestLevel]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        hobby_name = str(item.get("name", "") or "").strip()
        if not hobby_name:
            continue
        interest_level = _enum_from_name(HobbyInterestLevel, item.get("interestLevel"), HobbyInterestLevel.INDIFFERENT)
        result.append((hobby_name, interest_level))
    return result


def _skills_to_list(general_skills: list[GeneralSkills] | None) -> list[dict[str, Any]]:
    if not general_skills:
        return []
    return [{"name": str(skill.name or ""), "description": str(skill.description or "")} for skill in general_skills]


def _skills_from_list(data: Any) -> list[GeneralSkills]:
    if not isinstance(data, list):
        return []
    result = []
    for item in data:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "") or "").strip()
        if not name:
            continue
        result.append(GeneralSkills(name, str(item.get("description", "") or "")))
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
    return str(item_id) if item_id else None


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
    inventory_ids = []
    for item in gear.inventory:
        item_id = _item_to_ref(item)
        if item_id:
            inventory_ids.append(item_id)
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
        "inventory_item_ids": inventory_ids,
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

    inventory = []
    inventory_ids = data.get("inventory_item_ids", [])
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


def _llm_control_profile_to_dict(llm_control_profile: LLMControlProfile | None) -> dict[str, Any] | None:
    if llm_control_profile is None:
        return None
    return llm_control_profile.to_dict()


def _llm_control_profile_from_dict(data: Any) -> LLMControlProfile | None:
    if not isinstance(data, dict):
        return None
    return LLMControlProfile.from_dict(data)
