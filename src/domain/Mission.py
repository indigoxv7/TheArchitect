from __future__ import annotations

from typing import Any


class MissionUnitOption:
    def __init__(
        self,
        unitId: str,
        capacityMin: int | None = None,
        capacityMax: int | None = None,
        canBeElite: bool = False,
    ):
        self.unitId = str(unitId or "").strip()
        self.capacityMin = self._coerce_optional_int(capacityMin)
        self.capacityMax = self._coerce_optional_int(capacityMax)
        if self.capacityMin is not None:
            self.capacityMin = max(0, self.capacityMin)
        if self.capacityMax is not None:
            self.capacityMax = max(0, self.capacityMax)
        if self.capacityMin is not None and self.capacityMax is not None and self.capacityMax < self.capacityMin:
            self.capacityMax = self.capacityMin
        self.canBeElite = bool(canBeElite)

    @staticmethod
    def _coerce_optional_int(value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except Exception:
            return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "unitId": self.unitId,
            "capacityMin": self.capacityMin,
            "capacityMax": self.capacityMax,
            "canBeElite": self.canBeElite,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MissionUnitOption":
        if not isinstance(data, dict):
            raise ValueError("Mission unit option data must be a dictionary.")
        unit_id = str(data.get("unitId", "") or "").strip()
        if not unit_id:
            raise ValueError("Mission unit option must include a unitId.")
        return cls(
            unitId=unit_id,
            capacityMin=data.get("capacityMin"),
            capacityMax=data.get("capacityMax"),
            canBeElite=bool(data.get("canBeElite", False)),
        )


class MissionAllegianceConfig:
    def __init__(
        self,
        allegianceId: str,
        powerPointCap: int = 0,
        unitOptions: list[MissionUnitOption] | None = None,
        clusterProbability: float = 0.0,
        clusterProbabilityVariance: float = 0.0,
        levelMin: int = 0,
        levelMax: int = 0,
    ):
        self.allegianceId = str(allegianceId or "").strip()
        self.powerPointCap = max(0, self._coerce_int(powerPointCap, 0))
        self.unitOptions = [entry for entry in (unitOptions or []) if isinstance(entry, MissionUnitOption)]
        self.clusterProbability = self._clamp_probability(clusterProbability)
        self.clusterProbabilityVariance = self._clamp_probability(clusterProbabilityVariance)
        self.levelMin = max(0, self._coerce_int(levelMin, 0))
        self.levelMax = max(0, self._coerce_int(levelMax, self.levelMin))
        if self.levelMax < self.levelMin:
            self.levelMax = self.levelMin

    @staticmethod
    def _coerce_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except Exception:
            return default

    @staticmethod
    def _clamp_probability(value: Any) -> float:
        try:
            numeric = float(value)
        except Exception:
            numeric = 0.0
        return max(0.0, min(1.0, numeric))

    def to_dict(self) -> dict[str, Any]:
        return {
            "allegianceId": self.allegianceId,
            "powerPointCap": self.powerPointCap,
            "unitOptions": [entry.to_dict() for entry in self.unitOptions],
            "clusterProbability": self.clusterProbability,
            "clusterProbabilityVariance": self.clusterProbabilityVariance,
            "levelMin": self.levelMin,
            "levelMax": self.levelMax,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MissionAllegianceConfig":
        if not isinstance(data, dict):
            raise ValueError("Mission allegiance config data must be a dictionary.")
        allegiance_id = str(data.get("allegianceId", "") or "").strip()
        if not allegiance_id:
            raise ValueError("Mission allegiance config must include an allegianceId.")
        unit_options = []
        for raw_entry in data.get("unitOptions", []) or []:
            unit_options.append(MissionUnitOption.from_dict(raw_entry))
        return cls(
            allegianceId=allegiance_id,
            powerPointCap=data.get("powerPointCap", 0),
            unitOptions=unit_options,
            clusterProbability=data.get("clusterProbability", 0.0),
            clusterProbabilityVariance=data.get("clusterProbabilityVariance", 0.0),
            levelMin=data.get("levelMin", 0),
            levelMax=data.get("levelMax", 0),
        )


class Mission:
    def __init__(
        self,
        name: str,
        allegianceConfigs: list[MissionAllegianceConfig] | None = None,
        missionId: str = "",
    ):
        self.name = str(name or "")
        self.allegianceConfigs = [entry for entry in (allegianceConfigs or []) if isinstance(entry, MissionAllegianceConfig)]
        self.missionId = str(missionId or "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "missionId": self.missionId,
            "name": self.name,
            "allegianceConfigs": [entry.to_dict() for entry in self.allegianceConfigs],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Mission":
        if not isinstance(data, dict):
            raise ValueError("Mission data must be a dictionary.")
        name = str(data.get("name", "") or "").strip()
        if not name:
            raise ValueError("Mission data must include a non-empty name.")
        allegiance_configs = []
        for raw_entry in data.get("allegianceConfigs", []) or []:
            allegiance_configs.append(MissionAllegianceConfig.from_dict(raw_entry))
        return cls(
            name=name,
            allegianceConfigs=allegiance_configs,
            missionId=str(data.get("missionId", "") or ""),
        )


