from __future__ import annotations

from enum import Enum

from src.domain.race import CreatureSize


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


def enum_from_name(enum_type, value, default):
    if isinstance(value, enum_type):
        return value

    text = str(value or "").strip().upper()
    if text in enum_type.__members__:
        return enum_type[text]
    return default
