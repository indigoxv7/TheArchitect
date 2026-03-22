from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


def clean_text(value: Any) -> str:
    return str(value or "").strip()


def normalize_text_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = clean_text(value)
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(text)
    return result


def normalize_tag_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = clean_text(value).lower()
        if not text:
            continue
        if text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def normalize_string_map(values: Any) -> dict[str, float]:
    if not isinstance(values, dict):
        return {}
    result: dict[str, float] = {}
    for key, value in values.items():
        text = clean_text(key)
        if not text:
            continue
        try:
            result[text] = float(value)
        except (TypeError, ValueError):
            continue
    return result


def normalize_payload_dict(values: Any) -> dict[str, Any]:
    if not isinstance(values, dict):
        return {}
    return dict(values)


def coerce_enum(enum_cls, value: Any, default):
    if isinstance(value, enum_cls):
        return value
    text = clean_text(value)
    if not text:
        return default
    upper = text.upper()
    if upper in enum_cls.__members__:
        return enum_cls[upper]
    for entry in enum_cls:
        if entry.value.lower() == text.lower():
            return entry
    return default


class CompatibilitySelectionMode(Enum):
    ANY = "Any"
    SELECTED = "Selected Only"


class IncompatibilityMode(Enum):
    EXPLICIT = "Explicit List"
    ALL_EXCEPT_COMPATIBLE = "All Except Compatible"


class HookType(Enum):
    LORE = "Lore"
    ENCOUNTER = "Encounter"
    CLUE = "Clue"
    TREASURE = "Treasure"
    FACTION = "Faction"
    QUEST_SEED = "Quest Seed"
    ANOMALY = "Anomaly"


class SceneDescriptionMode(Enum):
    LOCAL_ONLY = "LOCAL_ONLY"
    OPENAI_ONLY = "OPENAI_ONLY"
    LOCAL_PRIMARY_OPENAI_CACHE = "LOCAL_PRIMARY_OPENAI_CACHE"


@dataclass
class EnvironmentEffect:
    name: str
    description: str = ""
    counterplay: str = ""
    effectId: str = ""

    def __post_init__(self):
        self.name = clean_text(self.name)
        self.description = str(self.description or "")
        self.counterplay = str(self.counterplay or "")
        self.effectId = clean_text(self.effectId)

    def to_dict(self) -> dict[str, Any]:
        return {
            "effectId": self.effectId,
            "name": self.name,
            "description": self.description,
            "counterplay": self.counterplay,
        }

    @classmethod
    def from_dict(cls, data: Any) -> "EnvironmentEffect":
        if not isinstance(data, dict):
            raise ValueError("Effect data must be a dictionary.")
        name = clean_text(data.get("name", ""))
        if not name:
            raise ValueError("Effect data must include a non-empty name.")
        return cls(
            name=name,
            description=str(data.get("description", "") or ""),
            counterplay=str(data.get("counterplay", "") or ""),
            effectId=clean_text(data.get("effectId", "")),
        )


@dataclass
class WeightedTextFragment:
    text: str
    weight: float = 1.0
    requiredTags: list[str] = field(default_factory=list)
    excludedTags: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.text = clean_text(self.text)
        self.weight = max(0.0, float(self.weight or 0.0))
        self.requiredTags = normalize_tag_list(self.requiredTags)
        self.excludedTags = normalize_tag_list(self.excludedTags)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "weight": float(self.weight),
            "requiredTags": list(self.requiredTags),
            "excludedTags": list(self.excludedTags),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "WeightedTextFragment":
        if isinstance(data, str):
            return cls(text=data)
        if not isinstance(data, dict):
            raise ValueError("Description fragment data must be a dictionary or string.")
        text = clean_text(data.get("text", ""))
        if not text:
            raise ValueError("Description fragments require text.")
        return cls(
            text=text,
            weight=float(data.get("weight", 1.0) or 1.0),
            requiredTags=data.get("requiredTags", []),
            excludedTags=data.get("excludedTags", []),
        )
