from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.domain.Mission import EliminationObjective, MissionObjective, MissionObjectiveStatus, MissionStatistics
from src.domain.combat_encounter import EncounterDefinition
from src.domain.combat_enums import (
    BattleOutcome,
    BattlePhase,
    BattleTeam,
    BattleTriggerType,
    CommanderStance,
    TargetPriority,
    TokenPolicy,
    enum_from_name,
)
from src.domain.combat_units import CombatUnitState, EnemyStackState


@dataclass
class CommanderOrders:
    stance: CommanderStance = CommanderStance.HOLD
    target_priority: TargetPriority = TargetPriority.FRONTLINE
    token_policy: TokenPolicy = TokenPolicy.NORMAL
    strategy_text: str = ""
    strategy_score: int = 5
    strategy_reasons: list[str] = field(default_factory=list)
    strategy_risk_flags: list[str] = field(default_factory=list)
    strategy_confidence: float = 0.0
    lane_discipline_modifier: float = 0.0
    resource_efficiency_modifier: float = 0.0
    width_control_bonus: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "stance": self.stance.name,
            "target_priority": self.target_priority.name,
            "token_policy": self.token_policy.name,
            "strategy_text": self.strategy_text,
            "strategy_score": int(self.strategy_score),
            "strategy_reasons": list(self.strategy_reasons),
            "strategy_risk_flags": list(self.strategy_risk_flags),
            "strategy_confidence": float(self.strategy_confidence),
            "lane_discipline_modifier": float(self.lane_discipline_modifier),
            "resource_efficiency_modifier": float(self.resource_efficiency_modifier),
            "width_control_bonus": int(self.width_control_bonus),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "CommanderOrders":
        data = data if isinstance(data, dict) else {}
        return cls(
            stance=enum_from_name(CommanderStance, data.get("stance"), CommanderStance.HOLD),
            target_priority=enum_from_name(
                TargetPriority,
                data.get("target_priority"),
                TargetPriority.FRONTLINE,
            ),
            token_policy=enum_from_name(TokenPolicy, data.get("token_policy"), TokenPolicy.NORMAL),
            strategy_text=str(data.get("strategy_text", "") or ""),
            strategy_score=int(data.get("strategy_score", 5) or 5),
            strategy_reasons=[str(item) for item in data.get("strategy_reasons", []) or []],
            strategy_risk_flags=[str(item) for item in data.get("strategy_risk_flags", []) or []],
            strategy_confidence=float(data.get("strategy_confidence", 0.0) or 0.0),
            lane_discipline_modifier=float(data.get("lane_discipline_modifier", 0.0) or 0.0),
            resource_efficiency_modifier=float(data.get("resource_efficiency_modifier", 0.0) or 0.0),
            width_control_bonus=int(data.get("width_control_bonus", 0) or 0),
        )

    def signature(self) -> str:
        return "|".join(
            [
                self.stance.name,
                self.target_priority.name,
                self.token_policy.name,
                str(int(self.strategy_score)),
                str(int(self.width_control_bonus)),
            ]
        )


@dataclass
class BattleTrigger:
    trigger_type: BattleTriggerType
    message: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trigger_type": self.trigger_type.name,
            "message": self.message,
            "payload": dict(self.payload),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "BattleTrigger":
        data = data if isinstance(data, dict) else {}
        return cls(
            trigger_type=enum_from_name(
                BattleTriggerType,
                data.get("trigger_type"),
                BattleTriggerType.LANE_BREAK,
            ),
            message=str(data.get("message", "") or ""),
            payload=dict(data.get("payload", {}) or {}),
        )


@dataclass
class BattleExchangeSummary:
    exchange_number: int
    highlights: list[str] = field(default_factory=list)
    triggers: list[BattleTrigger] = field(default_factory=list)
    player_front_line: int = 0
    enemy_front_line: int = 0
    player_hp_ratio: float = 1.0
    enemy_hp_ratio: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "exchange_number": int(self.exchange_number),
            "highlights": list(self.highlights),
            "triggers": [trigger.to_dict() for trigger in self.triggers],
            "player_front_line": int(self.player_front_line),
            "enemy_front_line": int(self.enemy_front_line),
            "player_hp_ratio": float(self.player_hp_ratio),
            "enemy_hp_ratio": float(self.enemy_hp_ratio),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "BattleExchangeSummary":
        data = data if isinstance(data, dict) else {}
        return cls(
            exchange_number=max(0, int(data.get("exchange_number", 0) or 0)),
            highlights=[str(item) for item in data.get("highlights", []) or []],
            triggers=[
                BattleTrigger.from_dict(item)
                for item in data.get("triggers", []) or []
                if isinstance(item, dict)
            ],
            player_front_line=int(data.get("player_front_line", 0) or 0),
            enemy_front_line=int(data.get("enemy_front_line", 0) or 0),
            player_hp_ratio=float(data.get("player_hp_ratio", 1.0) or 1.0),
            enemy_hp_ratio=float(data.get("enemy_hp_ratio", 1.0) or 1.0),
        )


@dataclass
class BattleState:
    player_id: int
    battle_id: str
    encounter: EncounterDefinition
    phase: BattlePhase = BattlePhase.ORDERS
    outcome: BattleOutcome = BattleOutcome.ONGOING
    result_summary: str = ""
    width: int = 3
    total_lines: int = 6
    player_front_line: int = 0
    enemy_front_line: int = 0
    default_player_front_line: int = 0
    default_enemy_front_line: int = 0
    player_recenter_pressure: float = 0.0
    enemy_recenter_pressure: float = 0.0
    exchange_count: int = 0
    battle_time_seconds: float = 0.0
    ally_units: list[CombatUnitState] = field(default_factory=list)
    enemy_units: list[CombatUnitState] = field(default_factory=list)
    enemy_stacks: list[EnemyStackState] = field(default_factory=list)
    orders: CommanderOrders = field(default_factory=CommanderOrders)
    recent_summaries: list[BattleExchangeSummary] = field(default_factory=list)
    pending_triggers: list[BattleTrigger] = field(default_factory=list)
    active_tab: str = "Orders"
    cached_victory_odds: float | None = None
    cached_orders_signature: str = ""
    mission_menu_name: str = ""
    mission_id: str = ""
    mission_name: str = ""
    mission_objective: MissionObjective = field(default_factory=lambda: EliminationObjective(1.0))
    mission_statistics: MissionStatistics = field(default_factory=MissionStatistics)
    mission_objective_status: MissionObjectiveStatus = MissionObjectiveStatus.IN_PROGRESS

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": int(self.player_id),
            "battle_id": self.battle_id,
            "encounter": self.encounter.to_dict(),
            "phase": self.phase.name,
            "outcome": self.outcome.name,
            "result_summary": self.result_summary,
            "width": int(self.width),
            "total_lines": int(self.total_lines),
            "player_front_line": int(self.player_front_line),
            "enemy_front_line": int(self.enemy_front_line),
            "default_player_front_line": int(self.default_player_front_line),
            "default_enemy_front_line": int(self.default_enemy_front_line),
            "player_recenter_pressure": float(self.player_recenter_pressure),
            "enemy_recenter_pressure": float(self.enemy_recenter_pressure),
            "exchange_count": int(self.exchange_count),
            "battle_time_seconds": float(self.battle_time_seconds),
            "ally_units": [unit.to_dict() for unit in self.ally_units],
            "enemy_units": [unit.to_dict() for unit in self.enemy_units],
            "enemy_stacks": [stack.to_dict() for stack in self.enemy_stacks],
            "orders": self.orders.to_dict(),
            "recent_summaries": [summary.to_dict() for summary in self.recent_summaries],
            "pending_triggers": [trigger.to_dict() for trigger in self.pending_triggers],
            "active_tab": self.active_tab,
            "cached_victory_odds": self.cached_victory_odds,
            "cached_orders_signature": self.cached_orders_signature,
            "mission_menu_name": self.mission_menu_name,
            "mission_id": self.mission_id,
            "mission_name": self.mission_name,
            "mission_objective": self.mission_objective.to_dict(),
            "mission_statistics": self.mission_statistics.to_dict(),
            "mission_objective_status": self.mission_objective_status.name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "BattleState":
        data = data if isinstance(data, dict) else {}
        encounter = EncounterDefinition.from_dict(data.get("encounter"))
        return cls(
            player_id=int(data.get("player_id", 0) or 0),
            battle_id=str(data.get("battle_id", "") or ""),
            encounter=encounter,
            phase=enum_from_name(BattlePhase, data.get("phase"), BattlePhase.ORDERS),
            outcome=enum_from_name(BattleOutcome, data.get("outcome"), BattleOutcome.ONGOING),
            result_summary=str(data.get("result_summary", "") or ""),
            width=max(1, int(data.get("width", encounter.width) or encounter.width)),
            total_lines=max(4, int(data.get("total_lines", encounter.total_lines) or encounter.total_lines)),
            player_front_line=int(data.get("player_front_line", encounter.player_front_line) or encounter.player_front_line),
            enemy_front_line=int(data.get("enemy_front_line", encounter.enemy_front_line) or encounter.enemy_front_line),
            default_player_front_line=int(data.get("default_player_front_line", encounter.player_front_line) or encounter.player_front_line),
            default_enemy_front_line=int(data.get("default_enemy_front_line", encounter.enemy_front_line) or encounter.enemy_front_line),
            player_recenter_pressure=float(data.get("player_recenter_pressure", 0.0) or 0.0),
            enemy_recenter_pressure=float(data.get("enemy_recenter_pressure", 0.0) or 0.0),
            exchange_count=max(0, int(data.get("exchange_count", 0) or 0)),
            battle_time_seconds=max(0.0, float(data.get("battle_time_seconds", 0.0) or 0.0)),
            ally_units=[
                CombatUnitState.from_dict(item)
                for item in data.get("ally_units", []) or []
                if isinstance(item, dict)
            ],
            enemy_units=[
                CombatUnitState.from_dict(item)
                for item in data.get("enemy_units", []) or []
                if isinstance(item, dict)
            ],
            enemy_stacks=[
                EnemyStackState.from_dict(item)
                for item in data.get("enemy_stacks", []) or []
                if isinstance(item, dict)
            ],
            orders=CommanderOrders.from_dict(data.get("orders")),
            recent_summaries=[
                BattleExchangeSummary.from_dict(item)
                for item in data.get("recent_summaries", []) or []
                if isinstance(item, dict)
            ],
            pending_triggers=[
                BattleTrigger.from_dict(item)
                for item in data.get("pending_triggers", []) or []
                if isinstance(item, dict)
            ],
            active_tab=str(data.get("active_tab", "Orders") or "Orders"),
            cached_victory_odds=data.get("cached_victory_odds"),
            cached_orders_signature=str(data.get("cached_orders_signature", "") or ""),
            mission_menu_name=str(data.get("mission_menu_name", "") or ""),
            mission_id=str(data.get("mission_id", "") or ""),
            mission_name=str(data.get("mission_name", "") or ""),
            mission_objective=MissionObjective.from_dict(
                data.get("mission_objective", {"objectiveType": "ELIMINATION"})
            ),
            mission_statistics=MissionStatistics.from_dict(data.get("mission_statistics", {})),
            mission_objective_status=enum_from_name(
                MissionObjectiveStatus,
                data.get("mission_objective_status"),
                MissionObjectiveStatus.IN_PROGRESS,
            ),
        )
