from __future__ import annotations

import random

from src.domain.CharacterUtil import Attributes
from src.domain.Race import Race
from src.services.character_generation_data import ATTRIBUTE_FIELDS, BUILD_MODIFIERS


def _coerce_int(value, default: int = 5) -> int:
    try:
        return int(round(float(value)))
    except Exception:
        return int(default)


def _attributes_to_int_dict(attributes: Attributes | None, default: int = 5) -> dict[str, int]:
    attributes = attributes if attributes is not None else Attributes()
    return {field: _coerce_int(getattr(attributes, field, default), default) for field in ATTRIBUTE_FIELDS}


def _attributes_from_int_dict(values: dict[str, int]) -> Attributes:
    return Attributes(
        physicalPower=_coerce_int(values.get("physicalPower", 5), 5),
        physicalStamina=_coerce_int(values.get("physicalStamina", 5), 5),
        physicalResistance=_coerce_int(values.get("physicalResistance", 5), 5),
        magicPower=_coerce_int(values.get("magicPower", 5), 5),
        magicStamina=_coerce_int(values.get("magicStamina", 5), 5),
        magicResistance=_coerce_int(values.get("magicResistance", 5), 5),
    )


def _clamp_attribute_dict(values: dict[str, int], minimums: dict[str, int], maximums: dict[str, int]) -> dict[str, int]:
    clamped = {}
    for field in ATTRIBUTE_FIELDS:
        low = minimums.get(field, values.get(field, 5))
        high = maximums.get(field, values.get(field, 5))
        if high < low:
            high = low
        clamped[field] = max(low, min(high, values.get(field, 5)))
    return clamped


def _normalize_build_key(build_value: str) -> str:
    return str(build_value or "").strip().lower().replace("-", " ").replace("_", " ")


def randomize_attributes_point_buy(
    race: Race | None,
    starting_attributes: Attributes | None = None,
    rng: random.Random | None = None,
) -> Attributes:
    rng = rng if rng is not None else random.Random()
    base_attributes = starting_attributes
    if base_attributes is None and race is not None and getattr(race, "averageSpecimine", None) is not None:
        base_attributes = getattr(race.averageSpecimine, "attributes", None)
    current = _attributes_to_int_dict(base_attributes, default=5)

    minimums = _attributes_to_int_dict(getattr(race, "minAverageAttributes", None), default=0) if race is not None else {field: 0 for field in ATTRIBUTE_FIELDS}
    maximums = _attributes_to_int_dict(getattr(race, "maxAverageAttributes", None), default=99) if race is not None else {field: 99 for field in ATTRIBUTE_FIELDS}
    current = _clamp_attribute_dict(current, minimums, maximums)

    removable_total = sum(max(0, current[field] - minimums[field]) for field in ATTRIBUTE_FIELDS)
    if removable_total <= 0:
        return _attributes_from_int_dict(current)

    transfer_count = rng.randint(1, removable_total)
    unspent_points = 0
    for _ in range(transfer_count):
        donors = [field for field in ATTRIBUTE_FIELDS if current[field] > minimums[field]]
        if not donors:
            break
        donor = rng.choice(donors)
        current[donor] -= 1
        unspent_points += 1

    while unspent_points > 0:
        recipients = [field for field in ATTRIBUTE_FIELDS if current[field] < maximums[field]]
        if not recipients:
            break
        recipient = rng.choice(recipients)
        current[recipient] += 1
        unspent_points -= 1

    return _attributes_from_int_dict(_clamp_attribute_dict(current, minimums, maximums))


def apply_build_modifier(
    attributes: Attributes,
    build_value: str,
    minimum_attributes: Attributes | None = None,
    maximum_attributes: Attributes | None = None,
) -> Attributes:
    values = _attributes_to_int_dict(attributes, default=5)
    minimums = _attributes_to_int_dict(minimum_attributes, default=-999)
    maximums = _attributes_to_int_dict(maximum_attributes, default=999)

    modifier = BUILD_MODIFIERS.get(_normalize_build_key(build_value), {})
    for field, delta in modifier.items():
        values[field] = values.get(field, 5) + int(delta)

    return _attributes_from_int_dict(_clamp_attribute_dict(values, minimums, maximums))
