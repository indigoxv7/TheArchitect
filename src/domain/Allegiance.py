from __future__ import annotations

from enum import Enum
from typing import Any


class AllegianceDefaultPolicy(Enum):
    HOSTILE_BY_DEFAULT = "hostile by default"
    NEUTRAL_BY_DEFAULT = "neutral by default"


class AllegianceRelationship(Enum):
    HATED_ENEMIES = "hated enemies"
    ENEMIES = "enemies"
    NEUTRAL = "neutral"
    DEFENSIVE_ALLIES = "defensive allies"
    FULL_ALLIES = "full allies"


class Allegiance:
    def __init__(
        self,
        name: str,
        defaultPolicy: AllegianceDefaultPolicy = AllegianceDefaultPolicy.HOSTILE_BY_DEFAULT,
        relationships: dict[str, AllegianceRelationship] | None = None,
        allegianceId: str = "",
    ):
        self.name = str(name or "")
        self.defaultPolicy = (
            defaultPolicy
            if isinstance(defaultPolicy, AllegianceDefaultPolicy)
            else AllegianceDefaultPolicy.HOSTILE_BY_DEFAULT
        )
        self.relationships = self._normalize_relationships(relationships)
        self.allegianceId = str(allegianceId or "")

    @staticmethod
    def _normalize_policy(value: Any) -> AllegianceDefaultPolicy:
        if isinstance(value, AllegianceDefaultPolicy):
            return value
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return AllegianceDefaultPolicy.HOSTILE_BY_DEFAULT
            upper = text.upper()
            if upper in AllegianceDefaultPolicy.__members__:
                return AllegianceDefaultPolicy[upper]
            for entry in AllegianceDefaultPolicy:
                if entry.value.lower() == text.lower():
                    return entry
        return AllegianceDefaultPolicy.HOSTILE_BY_DEFAULT

    @staticmethod
    def _normalize_relationship(value: Any) -> AllegianceRelationship | None:
        if isinstance(value, AllegianceRelationship):
            return value
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            upper = text.upper()
            if upper in AllegianceRelationship.__members__:
                return AllegianceRelationship[upper]
            for entry in AllegianceRelationship:
                if entry.value.lower() == text.lower():
                    return entry
        return None

    @classmethod
    def _normalize_relationships(cls, relationships: Any) -> dict[str, AllegianceRelationship]:
        if not isinstance(relationships, dict):
            return {}
        normalized: dict[str, AllegianceRelationship] = {}
        for other_id, relationship in relationships.items():
            other_key = str(other_id or "").strip()
            if not other_key:
                continue
            normalized_relationship = cls._normalize_relationship(relationship)
            if normalized_relationship is None:
                continue
            normalized[other_key] = normalized_relationship
        return normalized

    def get_relationship_to(self, other_allegiance_id: str) -> AllegianceRelationship:
        other_id = str(other_allegiance_id or "").strip()
        if other_id and other_id == self.allegianceId:
            return AllegianceRelationship.FULL_ALLIES
        explicit = self.relationships.get(other_id)
        if explicit is not None:
            return explicit
        if self.defaultPolicy == AllegianceDefaultPolicy.NEUTRAL_BY_DEFAULT:
            return AllegianceRelationship.NEUTRAL
        return AllegianceRelationship.ENEMIES

    def to_dict(self) -> dict[str, Any]:
        return {
            "allegianceId": self.allegianceId,
            "name": self.name,
            "defaultPolicy": self.defaultPolicy.name,
            "relationships": {
                other_id: relationship.name for other_id, relationship in sorted(self.relationships.items())
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Allegiance":
        if not isinstance(data, dict):
            raise ValueError("Allegiance data must be a dictionary.")

        name = str(data.get("name", "") or "").strip()
        if not name:
            raise ValueError("Allegiance data must include a non-empty name.")

        return cls(
            name=name,
            defaultPolicy=cls._normalize_policy(data.get("defaultPolicy")),
            relationships=cls._normalize_relationships(data.get("relationships")),
            allegianceId=str(data.get("allegianceId", "") or ""),
        )
