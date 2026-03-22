from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.domain.mission.map_generation import MissionMapGenerationRange
from src.domain.mission.objectives import MissionObjective, MissionObjectiveStatus
from src.domain.mission.statistics import MissionStatistics
from src.domain.mission.values import clean_text, clamp_fraction, clamp_non_negative_int, coerce_optional_int


@dataclass
class MissionUnitOption:
    unitId: str
    capacityMin: int | None = None
    capacityMax: int | None = None
    eliteChance: float = 0.0
    isBoss: bool = False

    def __post_init__(self):
        self.unitId = clean_text(self.unitId)
        self.capacityMin = coerce_optional_int(self.capacityMin)
        self.capacityMax = coerce_optional_int(self.capacityMax)
        if self.capacityMin is not None:
            self.capacityMin = max(0, self.capacityMin)
        if self.capacityMax is not None:
            self.capacityMax = max(0, self.capacityMax)
        if self.capacityMin is not None and self.capacityMax is not None and self.capacityMax < self.capacityMin:
            self.capacityMax = self.capacityMin
        self.eliteChance = clamp_fraction(self.eliteChance, 0.0)
        self.isBoss = bool(self.isBoss)

    def to_dict(self) -> dict[str, Any]:
        return {
            "unitId": self.unitId,
            "capacityMin": self.capacityMin,
            "capacityMax": self.capacityMax,
            "eliteChance": self.eliteChance,
            "isBoss": self.isBoss,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MissionUnitOption":
        if not isinstance(data, dict):
            raise ValueError("Mission unit option data must be a dictionary.")
        unit_id = clean_text(data.get("unitId", ""))
        if not unit_id:
            raise ValueError("Mission unit option must include a unitId.")
        return cls(
            unitId=unit_id,
            capacityMin=data.get("capacityMin"),
            capacityMax=data.get("capacityMax"),
            eliteChance=data.get("eliteChance", 0.0),
            isBoss=bool(data.get("isBoss", False)),
        )


@dataclass
class MissionAllegianceConfig:
    allegianceId: str
    powerPointCap: int = 0
    unitOptions: list[MissionUnitOption] = field(default_factory=list)
    clusterProbability: float = 0.0
    clusterProbabilityVariance: float = 0.0
    levelMin: int = 0
    levelMax: int = 0

    def __post_init__(self):
        self.allegianceId = clean_text(self.allegianceId)
        self.powerPointCap = clamp_non_negative_int(self.powerPointCap, 0)
        self.unitOptions = [entry for entry in (self.unitOptions or []) if isinstance(entry, MissionUnitOption)]
        self.clusterProbability = clamp_fraction(self.clusterProbability, 0.0)
        self.clusterProbabilityVariance = clamp_fraction(self.clusterProbabilityVariance, 0.0)
        self.levelMin = clamp_non_negative_int(self.levelMin, 0)
        self.levelMax = clamp_non_negative_int(self.levelMax, self.levelMin)
        if self.levelMax < self.levelMin:
            self.levelMax = self.levelMin

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
        allegiance_id = clean_text(data.get("allegianceId", ""))
        if not allegiance_id:
            raise ValueError("Mission allegiance config must include an allegianceId.")
        unit_options = [MissionUnitOption.from_dict(raw_entry) for raw_entry in data.get("unitOptions", []) or []]
        return cls(
            allegianceId=allegiance_id,
            powerPointCap=data.get("powerPointCap", 0),
            unitOptions=unit_options,
            clusterProbability=data.get("clusterProbability", 0.0),
            clusterProbabilityVariance=data.get("clusterProbabilityVariance", 0.0),
            levelMin=data.get("levelMin", 0),
            levelMax=data.get("levelMax", 0),
        )


@dataclass
class MissionTemplate:
    name: str
    objective: MissionObjective
    allegianceConfigs: list[MissionAllegianceConfig] = field(default_factory=list)
    biomeId: str = ""
    terrainPoolIds: list[str] = field(default_factory=list)
    climatePoolIds: list[str] = field(default_factory=list)
    nodeGenerationProfileId: str = ""
    descriptionPackId: str = ""
    portalMission: bool = True
    mapGenerationRange: MissionMapGenerationRange = field(default_factory=MissionMapGenerationRange)
    missionId: str = ""

    def __post_init__(self):
        self.name = str(self.name or "")
        self.objective = self._coerce_objective(self.objective)
        self.allegianceConfigs = [entry for entry in (self.allegianceConfigs or []) if isinstance(entry, MissionAllegianceConfig)]
        self.biomeId = clean_text(self.biomeId)
        self.terrainPoolIds = [clean_text(entry) for entry in (self.terrainPoolIds or []) if clean_text(entry)]
        self.climatePoolIds = [clean_text(entry) for entry in (self.climatePoolIds or []) if clean_text(entry)]
        self.nodeGenerationProfileId = clean_text(self.nodeGenerationProfileId)
        self.descriptionPackId = clean_text(self.descriptionPackId)
        self.portalMission = bool(self.portalMission)
        self.mapGenerationRange = self.mapGenerationRange if isinstance(self.mapGenerationRange, MissionMapGenerationRange) else MissionMapGenerationRange.from_dict(self.mapGenerationRange)
        self.missionId = str(self.missionId or "")

    @staticmethod
    def _coerce_objective(value: MissionObjective | dict[str, Any]) -> MissionObjective:
        if isinstance(value, MissionObjective):
            return value
        return MissionObjective.from_dict(value)

    def evaluate_objective(self, statistics: MissionStatistics | dict[str, Any] | None, mission_complete: bool = False) -> MissionObjectiveStatus:
        stats = statistics if isinstance(statistics, MissionStatistics) else MissionStatistics.from_dict(statistics or {})
        return self.objective.evaluate(stats, mission_complete=mission_complete)

    def to_dict(self) -> dict[str, Any]:
        return {
            "missionId": self.missionId,
            "name": self.name,
            "objective": self.objective.to_dict(),
            "allegianceConfigs": [entry.to_dict() for entry in self.allegianceConfigs],
            "biomeId": self.biomeId,
            "terrainPoolIds": list(self.terrainPoolIds),
            "climatePoolIds": list(self.climatePoolIds),
            "nodeGenerationProfileId": self.nodeGenerationProfileId,
            "descriptionPackId": self.descriptionPackId,
            "portalMission": self.portalMission,
            "mapGenerationRange": self.mapGenerationRange.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MissionTemplate":
        if not isinstance(data, dict):
            raise ValueError("Mission data must be a dictionary.")
        name = clean_text(data.get("name", ""))
        if not name:
            raise ValueError("Mission data must include a non-empty name.")
        objective = MissionObjective.from_dict(data.get("objective", {}))
        allegiance_configs = [MissionAllegianceConfig.from_dict(raw_entry) for raw_entry in data.get("allegianceConfigs", []) or []]
        return cls(
            name=name,
            objective=objective,
            allegianceConfigs=allegiance_configs,
            biomeId=clean_text(data.get("biomeId", "")),
            terrainPoolIds=data.get("terrainPoolIds", []),
            climatePoolIds=data.get("climatePoolIds", []),
            nodeGenerationProfileId=clean_text(data.get("nodeGenerationProfileId", "")),
            descriptionPackId=clean_text(data.get("descriptionPackId", "")),
            portalMission=bool(data.get("portalMission", True)),
            mapGenerationRange=MissionMapGenerationRange.from_dict(data.get("mapGenerationRange")),
            missionId=str(data.get("missionId", "") or ""),
        )
