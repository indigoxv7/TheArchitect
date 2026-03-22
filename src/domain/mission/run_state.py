from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.domain.mission.node_events import MissionNodeEvent
from src.domain.mission.objectives import MissionObjectiveStatus
from src.domain.mission.statistics import MissionStatistics


class MissionRunStatus(Enum):
    PREPARING = "Preparing"
    ACTIVE = "Active"
    SUCCESS = "Success"
    FAILED = "Failed"
    FORCED_RETREAT = "Forced Retreat"


@dataclass
class MissionPartyState:
    selectedCharacterInstanceIds: list[str] = field(default_factory=list)

    def __post_init__(self):
        normalized: list[str] = []
        seen: set[str] = set()
        for entry in self.selectedCharacterInstanceIds or []:
            text = str(entry or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            normalized.append(text)
        self.selectedCharacterInstanceIds = normalized

    def to_dict(self) -> dict[str, Any]:
        return {"selectedCharacterInstanceIds": list(self.selectedCharacterInstanceIds)}

    @classmethod
    def from_dict(cls, data: Any) -> "MissionPartyState":
        if not isinstance(data, dict):
            return cls()
        return cls(selectedCharacterInstanceIds=data.get("selectedCharacterInstanceIds", []))


@dataclass
class MissionNodeUnitState:
    runtimeUnitId: str
    allegianceId: str
    unitId: str
    unitLabel: str
    characterState: dict[str, Any]
    isBoss: bool = False
    isElite: bool = False
    defeated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtimeUnitId": self.runtimeUnitId,
            "allegianceId": self.allegianceId,
            "unitId": self.unitId,
            "unitLabel": self.unitLabel,
            "characterState": dict(self.characterState),
            "isBoss": bool(self.isBoss),
            "isElite": bool(self.isElite),
            "defeated": bool(self.defeated),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "MissionNodeUnitState":
        if not isinstance(data, dict):
            raise ValueError("Mission node unit data must be a dictionary.")
        return cls(
            runtimeUnitId=str(data.get("runtimeUnitId", "") or ""),
            allegianceId=str(data.get("allegianceId", "") or ""),
            unitId=str(data.get("unitId", "") or ""),
            unitLabel=str(data.get("unitLabel", "") or ""),
            characterState=dict(data.get("characterState", {}) or {}),
            isBoss=bool(data.get("isBoss", False)),
            isElite=bool(data.get("isElite", False)),
            defeated=bool(data.get("defeated", False)),
        )


@dataclass
class MissionNodeState:
    nodeId: int
    unitStates: list[MissionNodeUnitState] = field(default_factory=list)
    nanoAmount: int = 0
    clueTargetNodeId: int | None = None
    treasureCollected: bool = False
    clueResolved: bool = False

    def living_unit_states(self) -> list[MissionNodeUnitState]:
        return [unit for unit in self.unitStates if not unit.defeated]

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodeId": int(self.nodeId),
            "unitStates": [entry.to_dict() for entry in self.unitStates],
            "nanoAmount": int(self.nanoAmount),
            "clueTargetNodeId": self.clueTargetNodeId,
            "treasureCollected": bool(self.treasureCollected),
            "clueResolved": bool(self.clueResolved),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "MissionNodeState":
        if not isinstance(data, dict):
            raise ValueError("Mission node state data must be a dictionary.")
        return cls(
            nodeId=int(data.get("nodeId", 0) or 0),
            unitStates=[
                MissionNodeUnitState.from_dict(entry)
                for entry in data.get("unitStates", []) or []
                if isinstance(entry, dict)
            ],
            nanoAmount=max(0, int(data.get("nanoAmount", 0) or 0)),
            clueTargetNodeId=(
                int(data.get("clueTargetNodeId"))
                if data.get("clueTargetNodeId", None) not in (None, "")
                else None
            ),
            treasureCollected=bool(data.get("treasureCollected", False)),
            clueResolved=bool(data.get("clueResolved", False)),
        )


@dataclass
class MissionRunState:
    playerId: int
    missionId: str
    missionName: str
    missionTemplateState: dict[str, Any]
    mapState: dict[str, Any]
    partyState: MissionPartyState = field(default_factory=MissionPartyState)
    status: MissionRunStatus = MissionRunStatus.PREPARING
    currentNodeId: int | None = None
    visitedNodeIds: list[int] = field(default_factory=list)
    revealedNodeIds: list[int] = field(default_factory=list)
    nodeStates: list[MissionNodeState] = field(default_factory=list)
    missionStatistics: MissionStatistics = field(default_factory=MissionStatistics)
    missionObjectiveStatus: MissionObjectiveStatus = MissionObjectiveStatus.IN_PROGRESS
    campaignIds: list[str] = field(default_factory=list)
    pendingBattleNodeId: int | None = None
    pendingNodeEvents: list[MissionNodeEvent] = field(default_factory=list)
    missionCountRecorded: bool = False
    lastBattleSummary: str = ""
    resultSummary: str = ""

    def __post_init__(self):
        self.playerId = int(self.playerId)
        self.missionId = str(self.missionId or "")
        self.missionName = str(self.missionName or "")
        self.missionTemplateState = dict(self.missionTemplateState or {})
        self.mapState = dict(self.mapState or {})
        if not isinstance(self.partyState, MissionPartyState):
            self.partyState = MissionPartyState.from_dict(self.partyState)
        visited: list[int] = []
        seen_visited: set[int] = set()
        for entry in self.visitedNodeIds or []:
            node_id = int(entry)
            if node_id in seen_visited:
                continue
            seen_visited.add(node_id)
            visited.append(node_id)
        self.visitedNodeIds = visited
        revealed: list[int] = []
        seen_revealed: set[int] = set()
        for entry in self.revealedNodeIds or []:
            node_id = int(entry)
            if node_id in seen_revealed:
                continue
            seen_revealed.add(node_id)
            revealed.append(node_id)
        self.revealedNodeIds = revealed
        self.nodeStates = [
            entry if isinstance(entry, MissionNodeState) else MissionNodeState.from_dict(entry)
            for entry in (self.nodeStates or [])
            if entry is not None
        ]
        if not isinstance(self.missionStatistics, MissionStatistics):
            self.missionStatistics = MissionStatistics.from_dict(self.missionStatistics)
        if not isinstance(self.missionObjectiveStatus, MissionObjectiveStatus):
            try:
                self.missionObjectiveStatus = MissionObjectiveStatus[
                    str(self.missionObjectiveStatus or MissionObjectiveStatus.IN_PROGRESS.name)
                ]
            except Exception:
                self.missionObjectiveStatus = MissionObjectiveStatus.IN_PROGRESS
        self.campaignIds = [str(entry or "").strip() for entry in self.campaignIds or [] if str(entry or "").strip()]
        self.pendingBattleNodeId = int(self.pendingBattleNodeId) if self.pendingBattleNodeId is not None else None
        self.pendingNodeEvents = [
            entry if isinstance(entry, MissionNodeEvent) else MissionNodeEvent.from_dict(entry)
            for entry in (self.pendingNodeEvents or [])
            if entry is not None
        ]
        self.missionCountRecorded = bool(self.missionCountRecorded)
        self.lastBattleSummary = str(self.lastBattleSummary or "")
        self.resultSummary = str(self.resultSummary or "")

    def get_node(self, node_id: int) -> MissionNodeState | None:
        target = int(node_id)
        for node_state in self.nodeStates:
            if int(node_state.nodeId) == target:
                return node_state
        return None

    def mark_visited(self, node_id: int):
        target = int(node_id)
        if target not in self.visitedNodeIds:
            self.visitedNodeIds.append(target)
        if target not in self.revealedNodeIds:
            self.revealedNodeIds.append(target)

    def reveal_node(self, node_id: int):
        target = int(node_id)
        if target not in self.revealedNodeIds:
            self.revealedNodeIds.append(target)

    def to_dict(self) -> dict[str, Any]:
        return {
            "playerId": int(self.playerId),
            "missionId": self.missionId,
            "missionName": self.missionName,
            "missionTemplateState": dict(self.missionTemplateState),
            "mapState": dict(self.mapState),
            "partyState": self.partyState.to_dict(),
            "status": self.status.name,
            "currentNodeId": self.currentNodeId,
            "visitedNodeIds": list(self.visitedNodeIds),
            "revealedNodeIds": list(self.revealedNodeIds),
            "nodeStates": [entry.to_dict() for entry in self.nodeStates],
            "missionStatistics": self.missionStatistics.to_dict(),
            "missionObjectiveStatus": self.missionObjectiveStatus.name,
            "campaignIds": list(self.campaignIds),
            "pendingBattleNodeId": self.pendingBattleNodeId,
            "pendingNodeEvents": [entry.to_dict() for entry in self.pendingNodeEvents],
            "missionCountRecorded": bool(self.missionCountRecorded),
            "lastBattleSummary": self.lastBattleSummary,
            "resultSummary": self.resultSummary,
        }

    @classmethod
    def from_dict(cls, data: Any) -> "MissionRunState":
        if not isinstance(data, dict):
            raise ValueError("Mission run state data must be a dictionary.")
        status_name = str(data.get("status", MissionRunStatus.PREPARING.name) or MissionRunStatus.PREPARING.name)
        objective_status_name = str(
            data.get("missionObjectiveStatus", MissionObjectiveStatus.IN_PROGRESS.name)
            or MissionObjectiveStatus.IN_PROGRESS.name
        )
        return cls(
            playerId=int(data.get("playerId", 0) or 0),
            missionId=str(data.get("missionId", "") or ""),
            missionName=str(data.get("missionName", "") or ""),
            missionTemplateState=dict(data.get("missionTemplateState", {}) or {}),
            mapState=dict(data.get("mapState", {}) or {}),
            partyState=MissionPartyState.from_dict(data.get("partyState", {})),
            status=MissionRunStatus[status_name] if status_name in MissionRunStatus.__members__ else MissionRunStatus.PREPARING,
            currentNodeId=(int(data.get("currentNodeId")) if data.get("currentNodeId", None) not in (None, "") else None),
            visitedNodeIds=data.get("visitedNodeIds", []),
            revealedNodeIds=data.get("revealedNodeIds", []),
            nodeStates=data.get("nodeStates", []),
            missionStatistics=MissionStatistics.from_dict(data.get("missionStatistics", {})),
            missionObjectiveStatus=(
                MissionObjectiveStatus[objective_status_name]
                if objective_status_name in MissionObjectiveStatus.__members__
                else MissionObjectiveStatus.IN_PROGRESS
            ),
            campaignIds=data.get("campaignIds", []),
            pendingBattleNodeId=(
                int(data.get("pendingBattleNodeId"))
                if data.get("pendingBattleNodeId", None) not in (None, "")
                else None
            ),
            pendingNodeEvents=data.get("pendingNodeEvents", []),
            missionCountRecorded=bool(data.get("missionCountRecorded", False)),
            lastBattleSummary=str(data.get("lastBattleSummary", "") or ""),
            resultSummary=str(data.get("resultSummary", "") or ""),
        )
