from __future__ import annotations

from enum import Enum
from typing import Any


class MissionObjectiveType(Enum):
    ELIMINATION = "Elimination"
    ASSASSINATION = "Assassination"
    DEFENSE = "Defense"
    DELIVERY = "Delivery"
    ESCORT = "Escort"
    SURVIVAL = "Survival"
    RESCUE = "Rescue"
    SCAVENGE = "Scavenge"
    RECRUIT = "Recruit"


class MissionObjectiveStatus(Enum):
    IN_PROGRESS = "In Progress"
    SUCCESS = "Success"
    FAILURE = "Failure"


class MissionStatistics:
    def __init__(
        self,
        totalStartingEnemies: int = 0,
        totalStartingAllies: int = 0,
        enemiesRemaining: int = 0,
        alliesRemaining: int = 0,
        timeInsideMissionHours: float = 0.0,
        unitsRecruited: int = 0,
        basicResourcesGathered: int = 0,
        packagesDelivered: int = 0,
        bossesDefeated: int = 0,
        startingImportantObjects: int = 0,
        importantObjectsRemaining: int = 0,
        allyDistanceMovedFromStartingPoint: float = 0.0,
        deliveredPackageCounts: dict[str, int] | None = None,
        unitAliveStates: dict[str, bool] | None = None,
        unitDistancesMoved: dict[str, float] | None = None,
    ):
        self.totalStartingEnemies = max(0, self._coerce_int(totalStartingEnemies, 0))
        self.totalStartingAllies = max(0, self._coerce_int(totalStartingAllies, 0))
        self.enemiesRemaining = max(0, self._coerce_int(enemiesRemaining, self.totalStartingEnemies))
        self.alliesRemaining = max(0, self._coerce_int(alliesRemaining, self.totalStartingAllies))
        self.timeInsideMissionHours = max(0.0, self._coerce_float(timeInsideMissionHours, 0.0))
        self.unitsRecruited = max(0, self._coerce_int(unitsRecruited, 0))
        self.basicResourcesGathered = max(0, self._coerce_int(basicResourcesGathered, 0))
        self.packagesDelivered = max(0, self._coerce_int(packagesDelivered, 0))
        self.bossesDefeated = max(0, self._coerce_int(bossesDefeated, 0))
        self.startingImportantObjects = max(0, self._coerce_int(startingImportantObjects, 0))
        self.importantObjectsRemaining = max(0, self._coerce_int(importantObjectsRemaining, self.startingImportantObjects))
        self.allyDistanceMovedFromStartingPoint = max(0.0, self._coerce_float(allyDistanceMovedFromStartingPoint, 0.0))
        self.deliveredPackageCounts = self._normalize_delivered_package_counts(deliveredPackageCounts)
        self.unitAliveStates = self._normalize_alive_states(unitAliveStates)
        self.unitDistancesMoved = self._normalize_unit_distances(unitDistancesMoved)

    @staticmethod
    def _coerce_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except Exception:
            return default

    @staticmethod
    def _coerce_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default

    @classmethod
    def _normalize_delivered_package_counts(cls, value: Any) -> dict[str, int]:
        if not isinstance(value, dict):
            return {}
        result: dict[str, int] = {}
        for key, count in value.items():
            text = str(key or "").strip()
            if not text:
                continue
            result[text] = max(0, cls._coerce_int(count, 0))
        return result

    @staticmethod
    def _normalize_alive_states(value: Any) -> dict[str, bool]:
        if not isinstance(value, dict):
            return {}
        result: dict[str, bool] = {}
        for key, alive in value.items():
            text = str(key or "").strip()
            if text:
                result[text] = bool(alive)
        return result

    @classmethod
    def _normalize_unit_distances(cls, value: Any) -> dict[str, float]:
        if not isinstance(value, dict):
            return {}
        result: dict[str, float] = {}
        for key, distance in value.items():
            text = str(key or "").strip()
            if text:
                result[text] = max(0.0, cls._coerce_float(distance, 0.0))
        return result

    @staticmethod
    def _fraction(remaining: int, total: int) -> float:
        if total <= 0:
            return 0.0
        return max(0.0, min(1.0, float(remaining) / float(total)))

    @property
    def enemiesEliminated(self) -> int:
        return max(0, self.totalStartingEnemies - self.enemiesRemaining)

    @property
    def enemiesEliminatedFraction(self) -> float:
        if self.totalStartingEnemies <= 0:
            return 1.0
        return max(0.0, min(1.0, float(self.enemiesEliminated) / float(self.totalStartingEnemies)))

    @property
    def enemiesRemainingFraction(self) -> float:
        return self._fraction(self.enemiesRemaining, self.totalStartingEnemies)

    @property
    def alliesRemainingFraction(self) -> float:
        return self._fraction(self.alliesRemaining, self.totalStartingAllies)

    @property
    def importantObjectsRemainingFraction(self) -> float:
        return self._fraction(self.importantObjectsRemaining, self.startingImportantObjects)

    def get_enemies_remaining_percentage(self) -> float:
        return self.enemiesRemainingFraction * 100.0

    def get_allies_remaining_percentage(self) -> float:
        return self.alliesRemainingFraction * 100.0

    def get_delivered_package_count(self, item_id: str = "", allegiance_id: str = "") -> int:
        item_key = str(item_id or "").strip()
        allegiance_key = str(allegiance_id or "").strip()
        if not item_key and not allegiance_key:
            return self.packagesDelivered
        composite_key = f"{item_key}|{allegiance_key}"
        return max(0, self.deliveredPackageCounts.get(composite_key, 0))

    def is_unit_alive(self, unit_id: str) -> bool:
        return bool(self.unitAliveStates.get(str(unit_id or "").strip(), False))

    def get_unit_distance_moved(self, unit_id: str) -> float:
        return max(0.0, self.unitDistancesMoved.get(str(unit_id or "").strip(), 0.0))

    def count_escaped_allies(self, minimum_distance: float) -> int:
        minimum_distance = max(0.0, self._coerce_float(minimum_distance, 0.0))
        if self.unitAliveStates or self.unitDistancesMoved:
            escaped = 0
            unit_ids = set(self.unitAliveStates.keys()) | set(self.unitDistancesMoved.keys())
            for unit_id in unit_ids:
                if self.is_unit_alive(unit_id) and self.get_unit_distance_moved(unit_id) >= minimum_distance:
                    escaped += 1
            return escaped
        if self.allyDistanceMovedFromStartingPoint >= minimum_distance:
            return self.alliesRemaining
        return 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "totalStartingEnemies": self.totalStartingEnemies,
            "totalStartingAllies": self.totalStartingAllies,
            "enemiesRemaining": self.enemiesRemaining,
            "alliesRemaining": self.alliesRemaining,
            "timeInsideMissionHours": self.timeInsideMissionHours,
            "unitsRecruited": self.unitsRecruited,
            "basicResourcesGathered": self.basicResourcesGathered,
            "packagesDelivered": self.packagesDelivered,
            "bossesDefeated": self.bossesDefeated,
            "startingImportantObjects": self.startingImportantObjects,
            "importantObjectsRemaining": self.importantObjectsRemaining,
            "allyDistanceMovedFromStartingPoint": self.allyDistanceMovedFromStartingPoint,
            "deliveredPackageCounts": dict(self.deliveredPackageCounts),
            "unitAliveStates": dict(self.unitAliveStates),
            "unitDistancesMoved": dict(self.unitDistancesMoved),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "MissionStatistics":
        if not isinstance(data, dict):
            return cls()
        return cls(
            totalStartingEnemies=data.get("totalStartingEnemies", 0),
            totalStartingAllies=data.get("totalStartingAllies", 0),
            enemiesRemaining=data.get("enemiesRemaining", 0),
            alliesRemaining=data.get("alliesRemaining", 0),
            timeInsideMissionHours=data.get("timeInsideMissionHours", 0.0),
            unitsRecruited=data.get("unitsRecruited", 0),
            basicResourcesGathered=data.get("basicResourcesGathered", 0),
            packagesDelivered=data.get("packagesDelivered", 0),
            bossesDefeated=data.get("bossesDefeated", 0),
            startingImportantObjects=data.get("startingImportantObjects", 0),
            importantObjectsRemaining=data.get("importantObjectsRemaining", 0),
            allyDistanceMovedFromStartingPoint=data.get("allyDistanceMovedFromStartingPoint", 0.0),
            deliveredPackageCounts=data.get("deliveredPackageCounts", {}),
            unitAliveStates=data.get("unitAliveStates", {}),
            unitDistancesMoved=data.get("unitDistancesMoved", {}),
        )


class MissionObjective:
    objectiveType: MissionObjectiveType = MissionObjectiveType.ELIMINATION

    def __init__(self, objectiveType: MissionObjectiveType | str):
        self.objectiveType = self._coerce_type(objectiveType)

    @staticmethod
    def _coerce_type(value: MissionObjectiveType | str) -> MissionObjectiveType:
        if isinstance(value, MissionObjectiveType):
            return value
        text = str(value or "").strip().upper()
        if text in MissionObjectiveType.__members__:
            return MissionObjectiveType[text]
        for member in MissionObjectiveType:
            if member.value.upper() == text:
                return member
        return MissionObjectiveType.ELIMINATION

    def is_success(self, statistics: MissionStatistics, mission_complete: bool = False) -> bool:
        return False

    def is_failure(self, statistics: MissionStatistics, mission_complete: bool = False) -> bool:
        return False

    def evaluate(self, statistics: MissionStatistics, mission_complete: bool = False) -> MissionObjectiveStatus:
        if self.is_failure(statistics, mission_complete=mission_complete):
            return MissionObjectiveStatus.FAILURE
        if self.is_success(statistics, mission_complete=mission_complete):
            return MissionObjectiveStatus.SUCCESS
        return MissionObjectiveStatus.IN_PROGRESS

    def describe(self) -> str:
        return self.objectiveType.value

    def to_dict(self) -> dict[str, Any]:
        return {"objectiveType": self.objectiveType.name}

    @classmethod
    def from_dict(cls, data: Any) -> "MissionObjective":
        if not isinstance(data, dict):
            raise ValueError("Mission objective data must be a dictionary.")
        objective_type = cls._coerce_type(data.get("objectiveType"))
        objective_class = OBJECTIVE_TYPE_MAP.get(objective_type, EliminationObjective)
        return objective_class._from_dict_internal(data)


class EliminationObjective(MissionObjective):
    objectiveType = MissionObjectiveType.ELIMINATION

    def __init__(self, requiredEliminationFraction: float = 1.0):
        super().__init__(self.objectiveType)
        self.requiredEliminationFraction = self._clamp_fraction(requiredEliminationFraction, 1.0)

    @staticmethod
    def _clamp_fraction(value: Any, default: float = 0.0) -> float:
        try:
            numeric = float(value)
        except Exception:
            numeric = default
        return max(0.0, min(1.0, numeric))

    def is_success(self, statistics: MissionStatistics, mission_complete: bool = False) -> bool:
        return statistics.enemiesEliminatedFraction >= self.requiredEliminationFraction

    def describe(self) -> str:
        return f"Eliminate {self.requiredEliminationFraction * 100.0:.0f}% of enemies"

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload["requiredEliminationFraction"] = self.requiredEliminationFraction
        return payload

    @classmethod
    def _from_dict_internal(cls, data: dict[str, Any]) -> "EliminationObjective":
        return cls(requiredEliminationFraction=data.get("requiredEliminationFraction", 1.0))


class AssassinationObjective(MissionObjective):
    objectiveType = MissionObjectiveType.ASSASSINATION

    def __init__(self, requiredBossesDefeated: int = 1):
        super().__init__(self.objectiveType)
        self.requiredBossesDefeated = max(0, MissionStatistics._coerce_int(requiredBossesDefeated, 1))

    def is_success(self, statistics: MissionStatistics, mission_complete: bool = False) -> bool:
        return statistics.bossesDefeated >= self.requiredBossesDefeated

    def describe(self) -> str:
        return f"Defeat {self.requiredBossesDefeated} boss(es)"

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload["requiredBossesDefeated"] = self.requiredBossesDefeated
        return payload

    @classmethod
    def _from_dict_internal(cls, data: dict[str, Any]) -> "AssassinationObjective":
        return cls(requiredBossesDefeated=data.get("requiredBossesDefeated", 1))


class DefenseObjective(MissionObjective):
    objectiveType = MissionObjectiveType.DEFENSE

    def __init__(self, requiredAlliesRemainingFraction: float = 1.0):
        super().__init__(self.objectiveType)
        self.requiredAlliesRemainingFraction = EliminationObjective._clamp_fraction(requiredAlliesRemainingFraction, 1.0)

    def is_success(self, statistics: MissionStatistics, mission_complete: bool = False) -> bool:
        return mission_complete and statistics.alliesRemainingFraction >= self.requiredAlliesRemainingFraction

    def is_failure(self, statistics: MissionStatistics, mission_complete: bool = False) -> bool:
        return statistics.totalStartingAllies > 0 and statistics.alliesRemainingFraction < self.requiredAlliesRemainingFraction

    def describe(self) -> str:
        return f"Keep at least {self.requiredAlliesRemainingFraction * 100.0:.0f}% of allies alive"

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload["requiredAlliesRemainingFraction"] = self.requiredAlliesRemainingFraction
        return payload

    @classmethod
    def _from_dict_internal(cls, data: dict[str, Any]) -> "DefenseObjective":
        return cls(requiredAlliesRemainingFraction=data.get("requiredAlliesRemainingFraction", 1.0))


class DeliveryObjective(MissionObjective):
    objectiveType = MissionObjectiveType.DELIVERY

    def __init__(
        self,
        requiredItemId: str = "",
        targetAllegianceId: str = "",
        requiredPackagesDelivered: int = 1,
    ):
        super().__init__(self.objectiveType)
        self.requiredItemId = str(requiredItemId or "").strip()
        self.targetAllegianceId = str(targetAllegianceId or "").strip()
        self.requiredPackagesDelivered = max(1, MissionStatistics._coerce_int(requiredPackagesDelivered, 1))

    def is_success(self, statistics: MissionStatistics, mission_complete: bool = False) -> bool:
        return statistics.get_delivered_package_count(self.requiredItemId, self.targetAllegianceId) >= self.requiredPackagesDelivered

    def describe(self) -> str:
        package_text = f"Deliver {self.requiredPackagesDelivered} package(s)"
        if self.requiredItemId:
            package_text += f" of {self.requiredItemId}"
        if self.targetAllegianceId:
            package_text += f" to {self.targetAllegianceId}"
        return package_text

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "requiredItemId": self.requiredItemId,
                "targetAllegianceId": self.targetAllegianceId,
                "requiredPackagesDelivered": self.requiredPackagesDelivered,
            }
        )
        return payload

    @classmethod
    def _from_dict_internal(cls, data: dict[str, Any]) -> "DeliveryObjective":
        return cls(
            requiredItemId=data.get("requiredItemId", ""),
            targetAllegianceId=data.get("targetAllegianceId", ""),
            requiredPackagesDelivered=data.get("requiredPackagesDelivered", 1),
        )


class EscortObjective(MissionObjective):
    objectiveType = MissionObjectiveType.ESCORT

    def __init__(self, escortUnitId: str = ""):
        super().__init__(self.objectiveType)
        self.escortUnitId = str(escortUnitId or "").strip()

    def is_success(self, statistics: MissionStatistics, mission_complete: bool = False) -> bool:
        return mission_complete and self.escortUnitId != "" and statistics.is_unit_alive(self.escortUnitId)

    def is_failure(self, statistics: MissionStatistics, mission_complete: bool = False) -> bool:
        return self.escortUnitId != "" and self.escortUnitId in statistics.unitAliveStates and not statistics.is_unit_alive(self.escortUnitId)

    def describe(self) -> str:
        return f"Escort unit {self.escortUnitId or '<Unset>'}"

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload["escortUnitId"] = self.escortUnitId
        return payload

    @classmethod
    def _from_dict_internal(cls, data: dict[str, Any]) -> "EscortObjective":
        return cls(escortUnitId=data.get("escortUnitId", ""))


class SurvivalObjective(MissionObjective):
    objectiveType = MissionObjectiveType.SURVIVAL

    def __init__(self, requiredHoursSurvived: float = 1.0):
        super().__init__(self.objectiveType)
        self.requiredHoursSurvived = max(0.0, MissionStatistics._coerce_float(requiredHoursSurvived, 1.0))

    def is_success(self, statistics: MissionStatistics, mission_complete: bool = False) -> bool:
        return statistics.timeInsideMissionHours >= self.requiredHoursSurvived

    def describe(self) -> str:
        return f"Survive for {self.requiredHoursSurvived:g} hour(s)"

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload["requiredHoursSurvived"] = self.requiredHoursSurvived
        return payload

    @classmethod
    def _from_dict_internal(cls, data: dict[str, Any]) -> "SurvivalObjective":
        return cls(requiredHoursSurvived=data.get("requiredHoursSurvived", 1.0))


class RescueObjective(MissionObjective):
    objectiveType = MissionObjectiveType.RESCUE

    def __init__(self, requiredAlliesEscaped: int = 1, requiredEscapeDistance: float = 0.0):
        super().__init__(self.objectiveType)
        self.requiredAlliesEscaped = max(0, MissionStatistics._coerce_int(requiredAlliesEscaped, 1))
        self.requiredEscapeDistance = max(0.0, MissionStatistics._coerce_float(requiredEscapeDistance, 0.0))

    def is_success(self, statistics: MissionStatistics, mission_complete: bool = False) -> bool:
        return statistics.count_escaped_allies(self.requiredEscapeDistance) >= self.requiredAlliesEscaped

    def is_failure(self, statistics: MissionStatistics, mission_complete: bool = False) -> bool:
        return statistics.alliesRemaining < self.requiredAlliesEscaped

    def describe(self) -> str:
        return (
            f"Rescue {self.requiredAlliesEscaped} ally/allies and move them "
            f"{self.requiredEscapeDistance:g}+ distance"
        )

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "requiredAlliesEscaped": self.requiredAlliesEscaped,
                "requiredEscapeDistance": self.requiredEscapeDistance,
            }
        )
        return payload

    @classmethod
    def _from_dict_internal(cls, data: dict[str, Any]) -> "RescueObjective":
        return cls(
            requiredAlliesEscaped=data.get("requiredAlliesEscaped", 1),
            requiredEscapeDistance=data.get("requiredEscapeDistance", 0.0),
        )


class ScavengeObjective(MissionObjective):
    objectiveType = MissionObjectiveType.SCAVENGE

    def __init__(self, requiredBasicResources: int = 1):
        super().__init__(self.objectiveType)
        self.requiredBasicResources = max(0, MissionStatistics._coerce_int(requiredBasicResources, 1))

    def is_success(self, statistics: MissionStatistics, mission_complete: bool = False) -> bool:
        return statistics.basicResourcesGathered >= self.requiredBasicResources

    def describe(self) -> str:
        return f"Gather {self.requiredBasicResources} basic resources"

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload["requiredBasicResources"] = self.requiredBasicResources
        return payload

    @classmethod
    def _from_dict_internal(cls, data: dict[str, Any]) -> "ScavengeObjective":
        return cls(requiredBasicResources=data.get("requiredBasicResources", 1))


class RecruitObjective(MissionObjective):
    objectiveType = MissionObjectiveType.RECRUIT

    def __init__(self, requiredUnitsRecruited: int = 1):
        super().__init__(self.objectiveType)
        self.requiredUnitsRecruited = max(0, MissionStatistics._coerce_int(requiredUnitsRecruited, 1))

    def is_success(self, statistics: MissionStatistics, mission_complete: bool = False) -> bool:
        return statistics.unitsRecruited >= self.requiredUnitsRecruited

    def describe(self) -> str:
        return f"Recruit {self.requiredUnitsRecruited} unit(s)"

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload["requiredUnitsRecruited"] = self.requiredUnitsRecruited
        return payload

    @classmethod
    def _from_dict_internal(cls, data: dict[str, Any]) -> "RecruitObjective":
        return cls(requiredUnitsRecruited=data.get("requiredUnitsRecruited", 1))


OBJECTIVE_TYPE_MAP: dict[MissionObjectiveType, type[MissionObjective]] = {
    MissionObjectiveType.ELIMINATION: EliminationObjective,
    MissionObjectiveType.ASSASSINATION: AssassinationObjective,
    MissionObjectiveType.DEFENSE: DefenseObjective,
    MissionObjectiveType.DELIVERY: DeliveryObjective,
    MissionObjectiveType.ESCORT: EscortObjective,
    MissionObjectiveType.SURVIVAL: SurvivalObjective,
    MissionObjectiveType.RESCUE: RescueObjective,
    MissionObjectiveType.SCAVENGE: ScavengeObjective,
    MissionObjectiveType.RECRUIT: RecruitObjective,
}


class MissionUnitOption:
    def __init__(
        self,
        unitId: str,
        capacityMin: int | None = None,
        capacityMax: int | None = None,
        eliteChance: float = 0.0,
        isBoss: bool = False,
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
        self.eliteChance = EliminationObjective._clamp_fraction(eliteChance, 0.0)
        self.isBoss = bool(isBoss)

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
            "eliteChance": self.eliteChance,
            "isBoss": self.isBoss,
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
            eliteChance=data.get("eliteChance", 0.0),
            isBoss=bool(data.get("isBoss", False)),
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
        objective: MissionObjective,
        allegianceConfigs: list[MissionAllegianceConfig] | None = None,
        portalMission: bool = True,
        missionId: str = "",
    ):
        self.name = str(name or "")
        self.objective = objective if isinstance(objective, MissionObjective) else MissionObjective.from_dict(objective)
        self.allegianceConfigs = [entry for entry in (allegianceConfigs or []) if isinstance(entry, MissionAllegianceConfig)]
        self.portalMission = bool(portalMission)
        self.missionId = str(missionId or "")

    def evaluate_objective(
        self,
        statistics: MissionStatistics | dict[str, Any] | None,
        mission_complete: bool = False,
    ) -> MissionObjectiveStatus:
        stats = statistics if isinstance(statistics, MissionStatistics) else MissionStatistics.from_dict(statistics or {})
        return self.objective.evaluate(stats, mission_complete=mission_complete)

    def to_dict(self) -> dict[str, Any]:
        return {
            "missionId": self.missionId,
            "name": self.name,
            "objective": self.objective.to_dict(),
            "allegianceConfigs": [entry.to_dict() for entry in self.allegianceConfigs],
            "portalMission": self.portalMission,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Mission":
        if not isinstance(data, dict):
            raise ValueError("Mission data must be a dictionary.")
        name = str(data.get("name", "") or "").strip()
        if not name:
            raise ValueError("Mission data must include a non-empty name.")
        objective = MissionObjective.from_dict(data.get("objective", {}))
        allegiance_configs = []
        for raw_entry in data.get("allegianceConfigs", []) or []:
            allegiance_configs.append(MissionAllegianceConfig.from_dict(raw_entry))
        return cls(
            name=name,
            objective=objective,
            allegianceConfigs=allegiance_configs,
            portalMission=bool(data.get("portalMission", True)),
            missionId=str(data.get("missionId", "") or ""),
        )
