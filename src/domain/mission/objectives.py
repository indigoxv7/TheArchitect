from __future__ import annotations

from enum import Enum
from typing import Any

from src.domain.mission.statistics import MissionStatistics
from src.domain.mission.values import clean_text, clamp_fraction, clamp_non_negative_float, clamp_non_negative_int


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


def coerce_objective_type(value: MissionObjectiveType | str) -> MissionObjectiveType:
    if isinstance(value, MissionObjectiveType):
        return value

    text = clean_text(value).upper()
    if text in MissionObjectiveType.__members__:
        return MissionObjectiveType[text]

    for member in MissionObjectiveType:
        if member.value.upper() == text:
            return member
    return MissionObjectiveType.ELIMINATION


class MissionObjective:
    objectiveType: MissionObjectiveType = MissionObjectiveType.ELIMINATION

    def __init__(self, objectiveType: MissionObjectiveType | str):
        self.objectiveType = coerce_objective_type(objectiveType)

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

        objective_type = coerce_objective_type(data.get("objectiveType"))
        objective_class = OBJECTIVE_TYPE_MAP.get(objective_type, EliminationObjective)
        return objective_class._from_dict_internal(data)


class EliminationObjective(MissionObjective):
    objectiveType = MissionObjectiveType.ELIMINATION

    def __init__(self, requiredEliminationFraction: float = 1.0):
        super().__init__(self.objectiveType)
        self.requiredEliminationFraction = clamp_fraction(requiredEliminationFraction, 1.0)

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
        self.requiredBossesDefeated = clamp_non_negative_int(requiredBossesDefeated, 1)

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
        self.requiredAlliesRemainingFraction = clamp_fraction(requiredAlliesRemainingFraction, 1.0)

    def is_success(self, statistics: MissionStatistics, mission_complete: bool = False) -> bool:
        return mission_complete and statistics.alliesRemainingFraction >= self.requiredAlliesRemainingFraction

    def is_failure(self, statistics: MissionStatistics, mission_complete: bool = False) -> bool:
        return (
            statistics.totalStartingAllies > 0
            and statistics.alliesRemainingFraction < self.requiredAlliesRemainingFraction
        )

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
        self.requiredItemId = clean_text(requiredItemId)
        self.targetAllegianceId = clean_text(targetAllegianceId)
        self.requiredPackagesDelivered = max(1, clamp_non_negative_int(requiredPackagesDelivered, 1))

    def is_success(self, statistics: MissionStatistics, mission_complete: bool = False) -> bool:
        return (
            statistics.get_delivered_package_count(self.requiredItemId, self.targetAllegianceId)
            >= self.requiredPackagesDelivered
        )

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
        self.escortUnitId = clean_text(escortUnitId)

    def is_success(self, statistics: MissionStatistics, mission_complete: bool = False) -> bool:
        return mission_complete and self.escortUnitId != "" and statistics.is_unit_alive(self.escortUnitId)

    def is_failure(self, statistics: MissionStatistics, mission_complete: bool = False) -> bool:
        return (
            self.escortUnitId != ""
            and self.escortUnitId in statistics.unitAliveStates
            and not statistics.is_unit_alive(self.escortUnitId)
        )

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
        self.requiredHoursSurvived = clamp_non_negative_float(requiredHoursSurvived, 1.0)

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
        self.requiredAlliesEscaped = clamp_non_negative_int(requiredAlliesEscaped, 1)
        self.requiredEscapeDistance = clamp_non_negative_float(requiredEscapeDistance, 0.0)

    def is_success(self, statistics: MissionStatistics, mission_complete: bool = False) -> bool:
        return statistics.count_escaped_allies(self.requiredEscapeDistance) >= self.requiredAlliesEscaped

    def is_failure(self, statistics: MissionStatistics, mission_complete: bool = False) -> bool:
        return statistics.alliesRemaining < self.requiredAlliesEscaped

    def describe(self) -> str:
        return (
            f"Rescue {self.requiredAlliesEscaped} ally/allies and move them {self.requiredEscapeDistance:g}+ distance"
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
        self.requiredBasicResources = clamp_non_negative_int(requiredBasicResources, 1)

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
        self.requiredUnitsRecruited = clamp_non_negative_int(requiredUnitsRecruited, 1)

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
