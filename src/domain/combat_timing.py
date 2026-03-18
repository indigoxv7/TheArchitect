from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any


BASELINE_TURN_SECONDS = 6.0
EXCHANGE_DURATION_SECONDS = 12.0
DEFAULT_OFFENSIVE_ACTION_STAMINA_COST = 10.0
EXHAUSTED_DEFENSE_STAT_PENALTY = 3.0

BASELINE_SPEED_FACTOR = 1.0
BASELINE_STAMINA_LIMIT = 75.0
STAMINA_LIMIT_PER_LEVEL = 10.0
BASELINE_STAMINA_REGEN_PER_TURN = 15.0
STAMINA_REGEN_PER_LEVEL = 3.0

OVERCHARGED_DAMAGE_MULTIPLIER = 1.10
TIRED_DAMAGE_MULTIPLIER = 0.85
OVERCHARGED_ACCURACY_BONUS = 0.05
TIRED_ACCURACY_BONUS = -0.05
OVERCHARGED_SPEED_MULTIPLIER = 1.10
FRESH_SPEED_MULTIPLIER = 1.00
TIRED_SPEED_MULTIPLIER = 0.80
EXHAUSTED_SPEED_MULTIPLIER = 0.50


class ExertionLevel(Enum):
    OVERCHARGED = "OVERCHARGED"
    FRESH = "FRESH"
    TIRED = "TIRED"
    EXHAUSTED = "EXHAUSTED"


@dataclass
class CombatRuntimeState:
    stamina_current: float
    stamina_limit: float
    stamina_regen_per_second: float
    stamina_last_update_time: float = 0.0
    next_action_time: float = 0.0
    exertion_level: str = ExertionLevel.FRESH.name


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def speed_factor_from_attributes(physical_power: float, magic_power: float) -> float:
    normalized = ((2.0 * _safe_float(physical_power, 5.0)) + _safe_float(magic_power, 5.0)) / 15.0
    return max(0.1, normalized)


def stamina_limit_from_physical_stamina(physical_stamina: float) -> float:
    stamina_limit = BASELINE_STAMINA_LIMIT + (STAMINA_LIMIT_PER_LEVEL * (_safe_float(physical_stamina, 5.0) - 5.0))
    return max(1.0, stamina_limit)


def stamina_regen_per_second_from_physical_stamina(physical_stamina: float) -> float:
    regen_per_turn = BASELINE_STAMINA_REGEN_PER_TURN + (STAMINA_REGEN_PER_LEVEL * (_safe_float(physical_stamina, 5.0) - 5.0))
    return max(0.0, regen_per_turn / BASELINE_TURN_SECONDS)


def coerce_exertion_level(value: Any) -> ExertionLevel:
    if isinstance(value, ExertionLevel):
        return value
    text = str(value or ExertionLevel.FRESH.name).strip().upper()
    if text in ExertionLevel.__members__:
        return ExertionLevel[text]
    return ExertionLevel.FRESH


def compute_exertion_level(stamina_current: float, stamina_limit: float) -> ExertionLevel:
    stamina_limit = max(1.0, _safe_float(stamina_limit, BASELINE_STAMINA_LIMIT))
    stamina_current = _safe_float(stamina_current, stamina_limit)
    if stamina_current > stamina_limit:
        return ExertionLevel.OVERCHARGED
    if stamina_current >= 0.0:
        return ExertionLevel.FRESH
    if stamina_current >= -stamina_limit:
        return ExertionLevel.TIRED
    return ExertionLevel.EXHAUSTED


def damage_multiplier_for_exertion(exertion_level: Any) -> float:
    exertion = coerce_exertion_level(exertion_level)
    if exertion == ExertionLevel.OVERCHARGED:
        return OVERCHARGED_DAMAGE_MULTIPLIER
    if exertion == ExertionLevel.TIRED:
        return TIRED_DAMAGE_MULTIPLIER
    return 1.0


def accuracy_bonus_for_exertion(exertion_level: Any) -> float:
    exertion = coerce_exertion_level(exertion_level)
    if exertion == ExertionLevel.OVERCHARGED:
        return OVERCHARGED_ACCURACY_BONUS
    if exertion == ExertionLevel.TIRED:
        return TIRED_ACCURACY_BONUS
    return 0.0


def speed_multiplier_for_exertion(exertion_level: Any) -> float:
    exertion = coerce_exertion_level(exertion_level)
    if exertion == ExertionLevel.OVERCHARGED:
        return OVERCHARGED_SPEED_MULTIPLIER
    if exertion == ExertionLevel.TIRED:
        return TIRED_SPEED_MULTIPLIER
    if exertion == ExertionLevel.EXHAUSTED:
        return EXHAUSTED_SPEED_MULTIPLIER
    return FRESH_SPEED_MULTIPLIER


def defense_stat_penalty_for_exertion(exertion_level: Any) -> float:
    if coerce_exertion_level(exertion_level) == ExertionLevel.EXHAUSTED:
        return EXHAUSTED_DEFENSE_STAT_PENALTY
    return 0.0


def can_take_offensive_action(exertion_level: Any) -> bool:
    return coerce_exertion_level(exertion_level) != ExertionLevel.EXHAUSTED


def effective_speed_factor(base_speed: float, exertion_level: Any) -> float:
    return max(0.1, _safe_float(base_speed, BASELINE_SPEED_FACTOR) * speed_multiplier_for_exertion(exertion_level))


def action_interval_seconds(base_speed: float, exertion_level: Any) -> float:
    return BASELINE_TURN_SECONDS / effective_speed_factor(base_speed, exertion_level)


def start_time_gap_seconds(participant_count: int) -> float:
    return BASELINE_TURN_SECONDS / max(1, int(participant_count or 1))


def update_exertion_state(state_like) -> ExertionLevel:
    exertion = compute_exertion_level(
        getattr(state_like, "stamina_current", BASELINE_STAMINA_LIMIT),
        getattr(state_like, "stamina_limit", BASELINE_STAMINA_LIMIT),
    )
    setattr(state_like, "exertion_level", exertion.name)
    return exertion


def sync_stamina(state_like, current_time: float) -> float:
    current_time = max(0.0, _safe_float(current_time, 0.0))
    last_time = max(0.0, _safe_float(getattr(state_like, "stamina_last_update_time", current_time), current_time))
    elapsed = max(0.0, current_time - last_time)
    stamina_current = _safe_float(getattr(state_like, "stamina_current", BASELINE_STAMINA_LIMIT), BASELINE_STAMINA_LIMIT)
    regen_rate = max(0.0, _safe_float(getattr(state_like, "stamina_regen_per_second", 0.0), 0.0))
    stamina_current += elapsed * regen_rate
    setattr(state_like, "stamina_current", stamina_current)
    setattr(state_like, "stamina_last_update_time", current_time)
    update_exertion_state(state_like)
    return stamina_current


def spend_stamina(state_like, amount: float, current_time: float) -> float:
    sync_stamina(state_like, current_time)
    spent = max(0.0, _safe_float(amount, 0.0))
    stamina_current = _safe_float(getattr(state_like, "stamina_current", 0.0), 0.0) - spent
    setattr(state_like, "stamina_current", stamina_current)
    update_exertion_state(state_like)
    return stamina_current


def initialize_runtime_fields(
    state_like,
    *,
    stamina_limit: float,
    stamina_regen_per_second: float,
    stamina_current: float | None = None,
    stamina_last_update_time: float = 0.0,
    next_action_time: float = 0.0,
):
    limit = max(1.0, _safe_float(stamina_limit, BASELINE_STAMINA_LIMIT))
    setattr(state_like, "stamina_limit", limit)
    setattr(state_like, "stamina_regen_per_second", max(0.0, _safe_float(stamina_regen_per_second, 0.0)))
    setattr(state_like, "stamina_current", limit if stamina_current is None else _safe_float(stamina_current, limit))
    setattr(state_like, "stamina_last_update_time", max(0.0, _safe_float(stamina_last_update_time, 0.0)))
    setattr(state_like, "next_action_time", max(0.0, _safe_float(next_action_time, 0.0)))
    update_exertion_state(state_like)
    return state_like


def schedule_next_action(state_like, base_speed: float, turn_start_time: float) -> float:
    next_action_time = max(0.0, _safe_float(turn_start_time, 0.0)) + action_interval_seconds(
        base_speed,
        getattr(state_like, "exertion_level", ExertionLevel.FRESH.name),
    )
    setattr(state_like, "next_action_time", next_action_time)
    return next_action_time


def stamina_damage_from_hit(damage: float) -> float:
    return 5.0 + min(5.0, max(0.0, _safe_float(damage, 0.0)) * 0.20)


def next_window_start(current_time: float) -> float:
    current_time = max(0.0, _safe_float(current_time, 0.0))
    if current_time <= 0.0:
        return 0.0
    return math.ceil(current_time / BASELINE_TURN_SECONDS) * BASELINE_TURN_SECONDS
