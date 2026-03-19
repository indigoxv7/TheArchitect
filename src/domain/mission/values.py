from __future__ import annotations

from typing import Any


def clean_text(value: Any) -> str:
    return str(value or "").strip()


def coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def coerce_optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except Exception:
        return None


def clamp_fraction(value: Any, default: float = 0.0) -> float:
    return max(0.0, min(1.0, coerce_float(value, default)))


def clamp_non_negative_int(value: Any, default: int = 0) -> int:
    return max(0, coerce_int(value, default))


def clamp_non_negative_float(value: Any, default: float = 0.0) -> float:
    return max(0.0, coerce_float(value, default))


def normalize_string_int_map(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}

    result: dict[str, int] = {}
    for key, count in value.items():
        text = clean_text(key)
        if text:
            result[text] = clamp_non_negative_int(count, 0)
    return result


def normalize_string_bool_map(value: Any) -> dict[str, bool]:
    if not isinstance(value, dict):
        return {}

    result: dict[str, bool] = {}
    for key, alive in value.items():
        text = clean_text(key)
        if text:
            result[text] = bool(alive)
    return result


def normalize_string_float_map(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}

    result: dict[str, float] = {}
    for key, distance in value.items():
        text = clean_text(key)
        if text:
            result[text] = clamp_non_negative_float(distance, 0.0)
    return result
