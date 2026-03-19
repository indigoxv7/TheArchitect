from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.domain.mission.values import (
    clean_text,
    clamp_non_negative_float,
    clamp_non_negative_int,
    normalize_string_bool_map,
    normalize_string_float_map,
    normalize_string_int_map,
)


@dataclass
class MissionStatistics:
    totalStartingEnemies: int = 0
    totalStartingAllies: int = 0
    enemiesRemaining: int = 0
    alliesRemaining: int = 0
    timeInsideMissionHours: float = 0.0
    unitsRecruited: int = 0
    basicResourcesGathered: int = 0
    packagesDelivered: int = 0
    bossesDefeated: int = 0
    startingImportantObjects: int = 0
    importantObjectsRemaining: int = 0
    allyDistanceMovedFromStartingPoint: float = 0.0
    deliveredPackageCounts: dict[str, int] = field(default_factory=dict)
    unitAliveStates: dict[str, bool] = field(default_factory=dict)
    unitDistancesMoved: dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        self.totalStartingEnemies = clamp_non_negative_int(self.totalStartingEnemies, 0)
        self.totalStartingAllies = clamp_non_negative_int(self.totalStartingAllies, 0)
        self.enemiesRemaining = clamp_non_negative_int(self.enemiesRemaining, self.totalStartingEnemies)
        self.alliesRemaining = clamp_non_negative_int(self.alliesRemaining, self.totalStartingAllies)
        self.timeInsideMissionHours = clamp_non_negative_float(self.timeInsideMissionHours, 0.0)
        self.unitsRecruited = clamp_non_negative_int(self.unitsRecruited, 0)
        self.basicResourcesGathered = clamp_non_negative_int(self.basicResourcesGathered, 0)
        self.packagesDelivered = clamp_non_negative_int(self.packagesDelivered, 0)
        self.bossesDefeated = clamp_non_negative_int(self.bossesDefeated, 0)
        self.startingImportantObjects = clamp_non_negative_int(self.startingImportantObjects, 0)
        self.importantObjectsRemaining = clamp_non_negative_int(
            self.importantObjectsRemaining,
            self.startingImportantObjects,
        )
        self.allyDistanceMovedFromStartingPoint = clamp_non_negative_float(
            self.allyDistanceMovedFromStartingPoint,
            0.0,
        )
        self.deliveredPackageCounts = normalize_string_int_map(self.deliveredPackageCounts)
        self.unitAliveStates = normalize_string_bool_map(self.unitAliveStates)
        self.unitDistancesMoved = normalize_string_float_map(self.unitDistancesMoved)

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
        item_key = clean_text(item_id)
        allegiance_key = clean_text(allegiance_id)
        if not item_key and not allegiance_key:
            return self.packagesDelivered

        composite_key = f"{item_key}|{allegiance_key}"
        return max(0, self.deliveredPackageCounts.get(composite_key, 0))

    def is_unit_alive(self, unit_id: str) -> bool:
        return bool(self.unitAliveStates.get(clean_text(unit_id), False))

    def get_unit_distance_moved(self, unit_id: str) -> float:
        return max(0.0, self.unitDistancesMoved.get(clean_text(unit_id), 0.0))

    def count_escaped_allies(self, minimum_distance: float) -> int:
        minimum_distance = clamp_non_negative_float(minimum_distance, 0.0)
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
