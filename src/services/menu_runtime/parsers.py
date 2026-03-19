from __future__ import annotations

import json

from src.domain.character_util import DEFAULT_DURABILITY, EquipSlot, ItemType


def build_spell_payload_from_draft(draft: dict) -> dict:
    return {
        "name": draft.get("name", ""),
        "level": draft.get("level", 0),
        "power": draft.get("power", ""),
        "affinity": draft.get("affinity", ""),
        "casting_time": draft.get("casting_time", ""),
        "range": draft.get("range", ""),
        "components": {
            "verbal": bool(draft.get("component_verbal", False)),
            "somatic": bool(draft.get("component_somatic", False)),
            "material": draft.get("component_material", False),
        },
        "duration": draft.get("duration", ""),
        "description": draft.get("description", ""),
        "higher_level": draft.get("higher_level", ""),
    }


def build_item_payload_from_draft(draft: dict) -> dict:
    damage_type = str(draft.get("damage_type", "NONE") or "NONE").strip().upper()
    power_type = str(draft.get("power_type", "NONE") or "NONE").strip().upper()

    power_spell_name = str(draft.get("power_spell_name", "")).strip()
    power_value = int(draft.get("power_value", 0) or 0)

    item_power = []
    if power_type != "NONE":
        item_power.append(
            {
                "powerType": power_type,
                "power": power_value,
                "spellName": power_spell_name,
            }
        )

    stat_bonuses_raw = str(draft.get("stat_bonuses_json", "[]") or "[]")
    stat_bonuses = json.loads(stat_bonuses_raw)
    if not isinstance(stat_bonuses, list):
        raise ValueError("Stat bonuses must be a JSON array.")

    return {
        "name": str(draft.get("name", "")).strip(),
        "slot": str(draft.get("slot", EquipSlot.NOT_EQUIPABLE.name)),
        "tier": int(draft.get("tier", 0) or 0),
        "durability": int(draft.get("durability", DEFAULT_DURABILITY) or DEFAULT_DURABILITY),
        "itemType": str(draft.get("item_type", ItemType.DEFAULT.name)),
        "itemPower": item_power,
        "damageType": [] if damage_type == "NONE" else [damage_type],
        "statBonuses": stat_bonuses,
    }
