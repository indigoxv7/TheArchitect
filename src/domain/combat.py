from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.domain.Mission import EliminationObjective, MissionObjective, MissionObjectiveStatus, MissionStatistics
from src.domain.Race import CreatureSize


class CommanderStance(Enum):
    HOLD = "HOLD"
    ADVANCE = "ADVANCE"
    DEFENSIVE = "DEFENSIVE"
    AGGRESSIVE = "AGGRESSIVE"


class TargetPriority(Enum):
    FRONTLINE = "FRONTLINE"
    WEAKEST = "WEAKEST"
    STRONGEST = "STRONGEST"
    SUPPORT = "SUPPORT"
    RANGED = "RANGED"


class TokenPolicy(Enum):
    CONSERVE = "CONSERVE"
    NORMAL = "NORMAL"
    SPEND = "SPEND"


class BattlePhase(Enum):
    ORDERS = "ORDERS"
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"


class BattleTriggerType(Enum):
    HERO_DOWN = "HERO_DOWN"
    LANE_BREAK = "LANE_BREAK"
    REINFORCEMENT = "REINFORCEMENT"
    OBJECTIVE_THREATENED = "OBJECTIVE_THREATENED"
    RETREAT_OPPORTUNITY = "RETREAT_OPPORTUNITY"
    FORCED_RETREAT = "FORCED_RETREAT"
    MORALE_BREAK = "MORALE_BREAK"


class EncounterType(Enum):
    SCAVENGING = "SCAVENGING"
    PORTAL = "PORTAL"


class CombatRole(Enum):
    FRONTLINE = "FRONTLINE"
    RANGED = "RANGED"
    SUPPORT = "SUPPORT"


class BattleTeam(Enum):
    ALLY = "ALLY"
    ENEMY = "ENEMY"


class BattleOutcome(Enum):
    ONGOING = "ONGOING"
    VICTORY = "VICTORY"
    DEFEAT = "DEFEAT"
    RETREAT = "RETREAT"


def lane_width_for_size(size: CreatureSize) -> int:
    if size == CreatureSize.LARGE:
        return 2
    if size == CreatureSize.GIANT:
        return 3
    return 1


def _enum_from_name(enum_type, value, default):
    if isinstance(value, enum_type):
        return value
    text = str(value or "").strip().upper()
    if text in enum_type.__members__:
        return enum_type[text]
    return default


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
            stance=_enum_from_name(CommanderStance, data.get("stance"), CommanderStance.HOLD),
            target_priority=_enum_from_name(TargetPriority, data.get("target_priority"), TargetPriority.FRONTLINE),
            token_policy=_enum_from_name(TokenPolicy, data.get("token_policy"), TokenPolicy.NORMAL),
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
class EncounterEnemyEntry:
    kind: str
    identifier: str
    count: int = 1
    use_stack: bool = True
    notable: bool = False
    name_override: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "identifier": self.identifier,
            "count": int(self.count),
            "use_stack": bool(self.use_stack),
            "notable": bool(self.notable),
            "name_override": self.name_override,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EncounterEnemyEntry":
        data = data if isinstance(data, dict) else {}
        return cls(
            kind=str(data.get("kind", "race") or "race"),
            identifier=str(data.get("identifier", "") or ""),
            count=max(1, int(data.get("count", 1) or 1)),
            use_stack=bool(data.get("use_stack", True)),
            notable=bool(data.get("notable", False)),
            name_override=str(data.get("name_override", "") or ""),
        )


@dataclass
class ReinforcementEntry:
    exchange_number: int
    team: BattleTeam = BattleTeam.ENEMY
    entries: list[EncounterEnemyEntry] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "exchange_number": int(self.exchange_number),
            "team": self.team.name,
            "entries": [entry.to_dict() for entry in self.entries],
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ReinforcementEntry":
        data = data if isinstance(data, dict) else {}
        return cls(
            exchange_number=max(1, int(data.get("exchange_number", 1) or 1)),
            team=_enum_from_name(BattleTeam, data.get("team"), BattleTeam.ENEMY),
            entries=[
                EncounterEnemyEntry.from_dict(entry)
                for entry in data.get("entries", []) or []
                if isinstance(entry, dict)
            ],
            message=str(data.get("message", "") or ""),
        )


@dataclass
class EncounterDefinition:
    encounter_id: str
    encounter_type: EncounterType
    name: str
    terrain: str
    width: int
    total_lines: int
    objective_text: str
    allow_retreat: bool = True
    enemy_entries: list[EncounterEnemyEntry] = field(default_factory=list)
    reinforcements: list[ReinforcementEntry] = field(default_factory=list)
    player_front_line: int = 0
    enemy_front_line: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "encounter_id": self.encounter_id,
            "encounter_type": self.encounter_type.name,
            "name": self.name,
            "terrain": self.terrain,
            "width": int(self.width),
            "total_lines": int(self.total_lines),
            "objective_text": self.objective_text,
            "allow_retreat": bool(self.allow_retreat),
            "enemy_entries": [entry.to_dict() for entry in self.enemy_entries],
            "reinforcements": [entry.to_dict() for entry in self.reinforcements],
            "player_front_line": int(self.player_front_line),
            "enemy_front_line": int(self.enemy_front_line),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EncounterDefinition":
        data = data if isinstance(data, dict) else {}
        total_lines = max(4, int(data.get("total_lines", 6) or 6))
        default_player_front = total_lines // 2
        default_enemy_front = default_player_front + 1
        return cls(
            encounter_id=str(data.get("encounter_id", "") or ""),
            encounter_type=_enum_from_name(EncounterType, data.get("encounter_type"), EncounterType.SCAVENGING),
            name=str(data.get("name", "Encounter") or "Encounter"),
            terrain=str(data.get("terrain", "Open Ground") or "Open Ground"),
            width=max(1, int(data.get("width", 3) or 3)),
            total_lines=total_lines,
            objective_text=str(data.get("objective_text", "") or ""),
            allow_retreat=bool(data.get("allow_retreat", True)),
            enemy_entries=[
                EncounterEnemyEntry.from_dict(entry)
                for entry in data.get("enemy_entries", []) or []
                if isinstance(entry, dict)
            ],
            reinforcements=[
                ReinforcementEntry.from_dict(entry)
                for entry in data.get("reinforcements", []) or []
                if isinstance(entry, dict)
            ],
            player_front_line=int(data.get("player_front_line", default_player_front) or default_player_front),
            enemy_front_line=int(data.get("enemy_front_line", default_enemy_front) or default_enemy_front),
        )


@dataclass
class CombatUnitState:
    unit_id: str
    name: str
    team: BattleTeam
    role: CombatRole
    size: CreatureSize
    level: int
    health: float
    max_health: float
    health_state: str
    line: int = 0
    lane_start: int = 0
    lane_width: int = 1
    starting_line: int = 0
    character_instance_id: str = ""
    is_player_owned: bool = False
    is_boss: bool = False
    is_elite: bool = False
    template_character_id: str = ""
    race_id: str = "Human1"
    physical_power: float = 5.0
    physical_stamina: float = 5.0
    physical_resistance: float = 5.0
    magic_power: float = 5.0
    magic_stamina: float = 5.0
    magic_resistance: float = 5.0
    speed: float = 5.0
    primary_weapon_item_id: str = ""
    offhand_item_id: str = ""
    inventory_item_ids: list[str] = field(default_factory=list)
    spell_names: list[str] = field(default_factory=list)
    status_tokens: list[str] = field(default_factory=list)
    notable: bool = True

    @property
    def alive(self) -> bool:
        return float(self.health) > 0.0 and self.health_state != "DEAD"

    def to_dict(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "name": self.name,
            "team": self.team.name,
            "role": self.role.name,
            "size": self.size.name,
            "level": int(self.level),
            "health": float(self.health),
            "max_health": float(self.max_health),
            "health_state": self.health_state,
            "line": int(self.line),
            "lane_start": int(self.lane_start),
            "lane_width": int(self.lane_width),
            "starting_line": int(self.starting_line),
            "character_instance_id": self.character_instance_id,
            "is_player_owned": bool(self.is_player_owned),
            "is_boss": bool(self.is_boss),
            "is_elite": bool(self.is_elite),
            "template_character_id": self.template_character_id,
            "race_id": self.race_id,
            "physical_power": float(self.physical_power),
            "physical_stamina": float(self.physical_stamina),
            "physical_resistance": float(self.physical_resistance),
            "magic_power": float(self.magic_power),
            "magic_stamina": float(self.magic_stamina),
            "magic_resistance": float(self.magic_resistance),
            "speed": float(self.speed),
            "primary_weapon_item_id": self.primary_weapon_item_id,
            "offhand_item_id": self.offhand_item_id,
            "inventory_item_ids": list(self.inventory_item_ids),
            "spell_names": list(self.spell_names),
            "status_tokens": list(self.status_tokens),
            "notable": bool(self.notable),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "CombatUnitState":
        data = data if isinstance(data, dict) else {}
        size = _enum_from_name(CreatureSize, data.get("size"), CreatureSize.STANDARD)
        return cls(
            unit_id=str(data.get("unit_id", "") or ""),
            name=str(data.get("name", "Unit") or "Unit"),
            team=_enum_from_name(BattleTeam, data.get("team"), BattleTeam.ALLY),
            role=_enum_from_name(CombatRole, data.get("role"), CombatRole.FRONTLINE),
            size=size,
            level=int(data.get("level", 0) or 0),
            health=float(data.get("health", 100.0) or 100.0),
            max_health=max(1.0, float(data.get("max_health", 100.0) or 100.0)),
            health_state=str(data.get("health_state", "HEALTHY") or "HEALTHY"),
            line=int(data.get("line", 0) or 0),
            lane_start=int(data.get("lane_start", 0) or 0),
            lane_width=max(1, int(data.get("lane_width", lane_width_for_size(size)) or lane_width_for_size(size))),
            starting_line=int(data.get("starting_line", data.get("line", 0)) or 0),
            character_instance_id=str(data.get("character_instance_id", "") or ""),
            is_player_owned=bool(data.get("is_player_owned", False)),
            is_boss=bool(data.get("is_boss", False)),
            is_elite=bool(data.get("is_elite", False)),
            template_character_id=str(data.get("template_character_id", "") or ""),
            race_id=str(data.get("race_id", "Human1") or "Human1"),
            physical_power=float(data.get("physical_power", 5.0) or 5.0),
            physical_stamina=float(data.get("physical_stamina", 5.0) or 5.0),
            physical_resistance=float(data.get("physical_resistance", 5.0) or 5.0),
            magic_power=float(data.get("magic_power", 5.0) or 5.0),
            magic_stamina=float(data.get("magic_stamina", 5.0) or 5.0),
            magic_resistance=float(data.get("magic_resistance", 5.0) or 5.0),
            speed=float(data.get("speed", 5.0) or 5.0),
            primary_weapon_item_id=str(data.get("primary_weapon_item_id", "") or ""),
            offhand_item_id=str(data.get("offhand_item_id", "") or ""),
            inventory_item_ids=[str(item) for item in data.get("inventory_item_ids", []) or []],
            spell_names=[str(item) for item in data.get("spell_names", []) or []],
            status_tokens=[str(item) for item in data.get("status_tokens", []) or []],
            notable=bool(data.get("notable", True)),
        )


@dataclass
class EnemyStackState:
    stack_id: str
    name: str
    team: BattleTeam
    role: CombatRole
    size: CreatureSize
    count: int
    max_count: int
    unit_health: float
    total_health: float
    health_state: str
    line: int = 0
    lane_start: int = 0
    lane_width: int = 1
    starting_line: int = 0
    template_character_id: str = ""
    is_boss: bool = False
    is_elite: bool = False
    race_id: str = ""
    level: int = 0
    physical_power: float = 5.0
    physical_stamina: float = 5.0
    physical_resistance: float = 5.0
    magic_power: float = 5.0
    magic_stamina: float = 5.0
    magic_resistance: float = 5.0
    speed: float = 5.0
    primary_weapon_item_id: str = ""
    offhand_item_id: str = ""
    spell_names: list[str] = field(default_factory=list)
    status_tokens: list[str] = field(default_factory=list)

    @property
    def current_count(self) -> int:
        if self.total_health <= 0.0 or self.unit_health <= 0.0:
            return 0
        return max(0, min(self.max_count, int((self.total_health + self.unit_health - 1) // self.unit_health)))

    @property
    def alive(self) -> bool:
        return self.current_count > 0 and self.health_state != "DEAD"

    @property
    def health(self) -> float:
        return float(self.total_health)

    @property
    def max_health(self) -> float:
        return float(self.max_count) * float(self.unit_health)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stack_id": self.stack_id,
            "name": self.name,
            "team": self.team.name,
            "role": self.role.name,
            "size": self.size.name,
            "count": int(self.count),
            "max_count": int(self.max_count),
            "unit_health": float(self.unit_health),
            "total_health": float(self.total_health),
            "health_state": self.health_state,
            "line": int(self.line),
            "lane_start": int(self.lane_start),
            "lane_width": int(self.lane_width),
            "starting_line": int(self.starting_line),
            "template_character_id": self.template_character_id,
            "is_boss": bool(self.is_boss),
            "is_elite": bool(self.is_elite),
            "race_id": self.race_id,
            "level": int(self.level),
            "physical_power": float(self.physical_power),
            "physical_stamina": float(self.physical_stamina),
            "physical_resistance": float(self.physical_resistance),
            "magic_power": float(self.magic_power),
            "magic_stamina": float(self.magic_stamina),
            "magic_resistance": float(self.magic_resistance),
            "speed": float(self.speed),
            "primary_weapon_item_id": self.primary_weapon_item_id,
            "offhand_item_id": self.offhand_item_id,
            "spell_names": list(self.spell_names),
            "status_tokens": list(self.status_tokens),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EnemyStackState":
        data = data if isinstance(data, dict) else {}
        size = _enum_from_name(CreatureSize, data.get("size"), CreatureSize.STANDARD)
        return cls(
            stack_id=str(data.get("stack_id", "") or ""),
            name=str(data.get("name", "Enemy Stack") or "Enemy Stack"),
            team=_enum_from_name(BattleTeam, data.get("team"), BattleTeam.ENEMY),
            role=_enum_from_name(CombatRole, data.get("role"), CombatRole.FRONTLINE),
            size=size,
            count=max(1, int(data.get("count", 1) or 1)),
            max_count=max(1, int(data.get("max_count", 1) or 1)),
            unit_health=max(1.0, float(data.get("unit_health", 100.0) or 100.0)),
            total_health=max(0.0, float(data.get("total_health", 100.0) or 100.0)),
            health_state=str(data.get("health_state", "HEALTHY") or "HEALTHY"),
            line=int(data.get("line", 0) or 0),
            lane_start=int(data.get("lane_start", 0) or 0),
            lane_width=max(1, int(data.get("lane_width", lane_width_for_size(size)) or lane_width_for_size(size))),
            starting_line=int(data.get("starting_line", data.get("line", 0)) or 0),
            template_character_id=str(data.get("template_character_id", "") or ""),
            is_boss=bool(data.get("is_boss", False)),
            is_elite=bool(data.get("is_elite", False)),
            race_id=str(data.get("race_id", "") or ""),
            level=int(data.get("level", 0) or 0),
            physical_power=float(data.get("physical_power", 5.0) or 5.0),
            physical_stamina=float(data.get("physical_stamina", 5.0) or 5.0),
            physical_resistance=float(data.get("physical_resistance", 5.0) or 5.0),
            magic_power=float(data.get("magic_power", 5.0) or 5.0),
            magic_stamina=float(data.get("magic_stamina", 5.0) or 5.0),
            magic_resistance=float(data.get("magic_resistance", 5.0) or 5.0),
            speed=float(data.get("speed", 5.0) or 5.0),
            primary_weapon_item_id=str(data.get("primary_weapon_item_id", "") or ""),
            offhand_item_id=str(data.get("offhand_item_id", "") or ""),
            spell_names=[str(item) for item in data.get("spell_names", []) or []],
            status_tokens=[str(item) for item in data.get("status_tokens", []) or []],
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
            trigger_type=_enum_from_name(BattleTriggerType, data.get("trigger_type"), BattleTriggerType.LANE_BREAK),
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
            phase=_enum_from_name(BattlePhase, data.get("phase"), BattlePhase.ORDERS),
            outcome=_enum_from_name(BattleOutcome, data.get("outcome"), BattleOutcome.ONGOING),
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
            mission_objective=MissionObjective.from_dict(data.get("mission_objective", {"objectiveType": "ELIMINATION"})),
            mission_statistics=MissionStatistics.from_dict(data.get("mission_statistics", {})),
            mission_objective_status=_enum_from_name(MissionObjectiveStatus, data.get("mission_objective_status"), MissionObjectiveStatus.IN_PROGRESS),
        )
