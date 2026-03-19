from __future__ import annotations

from enum import Enum
from typing import Any


class CompatibilitySelectionMode(Enum):
    ANY = "Any"
    SELECTED = "Selected Only"


class IncompatibilityMode(Enum):
    EXPLICIT = "Explicit List"
    ALL_EXCEPT_COMPATIBLE = "All Except Compatible"


class EnvironmentEffect:
    def __init__(self, name: str, description: str = "", counterplay: str = "", effectId: str = ""):
        self.name = str(name or "").strip()
        self.description = str(description or "")
        self.counterplay = str(counterplay or "")
        self.effectId = str(effectId or "").strip()

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
        name = str(data.get("name", "") or "").strip()
        if not name:
            raise ValueError("Effect data must include a non-empty name.")
        return cls(
            name=name,
            description=str(data.get("description", "") or ""),
            counterplay=str(data.get("counterplay", "") or ""),
            effectId=str(data.get("effectId", "") or "").strip(),
        )


class Terrain:
    def __init__(self, name: str, description: str = "", effectIds: list[str] | None = None, terrainId: str = ""):
        self.name = str(name or "").strip()
        self.description = str(description or "")
        self.effectIds = self._normalize_ids(effectIds)
        self.terrainId = str(terrainId or "").strip()

    @staticmethod
    def _normalize_ids(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        result: list[str] = []
        for entry in value:
            text = str(entry or "").strip()
            if text and text not in result:
                result.append(text)
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "terrainId": self.terrainId,
            "name": self.name,
            "description": self.description,
            "effectIds": list(self.effectIds),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "Terrain":
        if not isinstance(data, dict):
            raise ValueError("Terrain data must be a dictionary.")
        name = str(data.get("name", "") or "").strip()
        if not name:
            raise ValueError("Terrain data must include a non-empty name.")
        return cls(
            name=name,
            description=str(data.get("description", "") or ""),
            effectIds=data.get("effectIds", []),
            terrainId=str(data.get("terrainId", "") or "").strip(),
        )


class Climate:
    def __init__(
        self,
        name: str,
        temperature: str = "",
        humidity: str = "",
        description: str = "",
        effectIds: list[str] | None = None,
        climateId: str = "",
    ):
        self.name = str(name or "").strip()
        self.temperature = str(temperature or "")
        self.humidity = str(humidity or "")
        self.description = str(description or "")
        self.effectIds = Terrain._normalize_ids(effectIds)
        self.climateId = str(climateId or "").strip()

    def to_dict(self) -> dict[str, Any]:
        return {
            "climateId": self.climateId,
            "name": self.name,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "description": self.description,
            "effectIds": list(self.effectIds),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "Climate":
        if not isinstance(data, dict):
            raise ValueError("Climate data must be a dictionary.")
        name = str(data.get("name", "") or "").strip()
        if not name:
            raise ValueError("Climate data must include a non-empty name.")
        return cls(
            name=name,
            temperature=str(data.get("temperature", data.get("temp", "")) or ""),
            humidity=str(data.get("humidity", "") or ""),
            description=str(data.get("description", "") or ""),
            effectIds=data.get("effectIds", []),
            climateId=str(data.get("climateId", "") or "").strip(),
        )


class Biome:
    def __init__(
        self,
        name: str,
        description: str = "",
        effectIds: list[str] | None = None,
        terrainCompatibilityMode: CompatibilitySelectionMode = CompatibilitySelectionMode.ANY,
        compatibleTerrainIds: list[str] | None = None,
        terrainIncompatibilityMode: IncompatibilityMode = IncompatibilityMode.EXPLICIT,
        incompatibleTerrainIds: list[str] | None = None,
        climateCompatibilityMode: CompatibilitySelectionMode = CompatibilitySelectionMode.ANY,
        compatibleClimateIds: list[str] | None = None,
        climateIncompatibilityMode: IncompatibilityMode = IncompatibilityMode.EXPLICIT,
        incompatibleClimateIds: list[str] | None = None,
        biomeId: str = "",
    ):
        self.name = str(name or "").strip()
        self.description = str(description or "")
        self.effectIds = Terrain._normalize_ids(effectIds)
        self.terrainCompatibilityMode = self._coerce_enum(
            CompatibilitySelectionMode, terrainCompatibilityMode, CompatibilitySelectionMode.ANY
        )
        self.compatibleTerrainIds = Terrain._normalize_ids(compatibleTerrainIds)
        self.terrainIncompatibilityMode = self._coerce_enum(
            IncompatibilityMode, terrainIncompatibilityMode, IncompatibilityMode.EXPLICIT
        )
        self.incompatibleTerrainIds = Terrain._normalize_ids(incompatibleTerrainIds)
        self.climateCompatibilityMode = self._coerce_enum(
            CompatibilitySelectionMode, climateCompatibilityMode, CompatibilitySelectionMode.ANY
        )
        self.compatibleClimateIds = Terrain._normalize_ids(compatibleClimateIds)
        self.climateIncompatibilityMode = self._coerce_enum(
            IncompatibilityMode, climateIncompatibilityMode, IncompatibilityMode.EXPLICIT
        )
        self.incompatibleClimateIds = Terrain._normalize_ids(incompatibleClimateIds)
        self.biomeId = str(biomeId or "").strip()

    @staticmethod
    def _coerce_enum(enum_cls, value: Any, default):
        if isinstance(value, enum_cls):
            return value
        text = str(value or "").strip()
        if not text:
            return default
        upper = text.upper()
        if upper in enum_cls.__members__:
            return enum_cls[upper]
        for entry in enum_cls:
            if entry.value.lower() == text.lower():
                return entry
        return default

    def to_dict(self) -> dict[str, Any]:
        return {
            "biomeId": self.biomeId,
            "name": self.name,
            "description": self.description,
            "effectIds": list(self.effectIds),
            "terrainCompatibilityMode": self.terrainCompatibilityMode.name,
            "compatibleTerrainIds": list(self.compatibleTerrainIds),
            "terrainIncompatibilityMode": self.terrainIncompatibilityMode.name,
            "incompatibleTerrainIds": list(self.incompatibleTerrainIds),
            "climateCompatibilityMode": self.climateCompatibilityMode.name,
            "compatibleClimateIds": list(self.compatibleClimateIds),
            "climateIncompatibilityMode": self.climateIncompatibilityMode.name,
            "incompatibleClimateIds": list(self.incompatibleClimateIds),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "Biome":
        if not isinstance(data, dict):
            raise ValueError("Biome data must be a dictionary.")
        name = str(data.get("name", "") or "").strip()
        if not name:
            raise ValueError("Biome data must include a non-empty name.")
        return cls(
            name=name,
            description=str(data.get("description", "") or ""),
            effectIds=data.get("effectIds", []),
            terrainCompatibilityMode=data.get("terrainCompatibilityMode", CompatibilitySelectionMode.ANY.name),
            compatibleTerrainIds=data.get("compatibleTerrainIds", []),
            terrainIncompatibilityMode=data.get("terrainIncompatibilityMode", IncompatibilityMode.EXPLICIT.name),
            incompatibleTerrainIds=data.get("incompatibleTerrainIds", []),
            climateCompatibilityMode=data.get("climateCompatibilityMode", CompatibilitySelectionMode.ANY.name),
            compatibleClimateIds=data.get("compatibleClimateIds", []),
            climateIncompatibilityMode=data.get("climateIncompatibilityMode", IncompatibilityMode.EXPLICIT.name),
            incompatibleClimateIds=data.get("incompatibleClimateIds", []),
            biomeId=str(data.get("biomeId", "") or "").strip(),
        )
