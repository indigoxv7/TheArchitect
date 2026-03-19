from __future__ import annotations

from src.domain.character_util import ItemType


WEAPON_ITEM_TYPES = {
    ItemType.MELEE_WEAPON,
    ItemType.MELEE_THROWABLE,
    ItemType.RANGED_WEAPON,
}


def _serialize_number(value: float | int) -> float | int:
    numeric = float(value)
    if numeric.is_integer():
        return int(numeric)
    return numeric


def _unique_strings(values: list[str]) -> list[str]:
    result = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result

