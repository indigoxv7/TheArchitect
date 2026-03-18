from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.config.tuning import battle_factor, character_stat_factor

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


def baseline_turn_seconds() -> float:
    return battle_factor("baseline_turn_seconds", BASELINE_TURN_SECONDS)


def exchange_duration_seconds() -> float:
    return battle_factor("exchange_duration_seconds", EXCHANGE_DURATION_SECONDS)


def default_offensive_action_stamina_cost() -> float:
    return battle_factor("default_offensive_action_stamina_cost", DEFAULT_OFFENSIVE_ACTION_STAMINA_COST)


def exhausted_defense_stat_penalty() -> float:
    return battle_factor("exhausted_defense_stat_penalty", EXHAUSTED_DEFENSE_STAT_PENALTY)


def minimum_speed_factor() -> float:
    return character_stat_factor("minimum_speed_factor", 0.10)


def baseline_stamina_limit() -> float:
    return character_stat_factor("baseline_stamina_limit", BASELINE_STAMINA_LIMIT)


def speed_factor_from_attributes(physical_power: float, magic_power: float) -> float:
    physical_weight = character_stat_factor("speed_physical_power_weight", 2.0)
    magic_weight = character_stat_factor("speed_magic_power_weight", 1.0)
    divisor = max(0.0001, character_stat_factor("speed_normalization_divisor", 15.0))
    normalized = ((physical_weight * _safe_float(physical_power, 5.0)) + (magic_weight * _safe_float(magic_power, 5.0))) / divisor
    return max(minimum_speed_factor(), normalized)


def stamina_limit_from_physical_stamina(physical_stamina: float) -> float:
    primary_baseline = character_stat_factor("primary_stat_baseline", 5.0)
    stamina_limit = baseline_stamina_limit() + (
        character_stat_factor("stamina_limit_per_level", STAMINA_LIMIT_PER_LEVEL)
        * (_safe_float(physical_stamina, primary_baseline) - primary_baseline)
    )
    return max(1.0, stamina_limit)


def stamina_regen_per_second_from_physical_stamina(physical_stamina: float) -> float:
    primary_baseline = character_stat_factor("primary_stat_baseline", 5.0)
    regen_per_turn = character_stat_factor("baseline_stamina_regen_per_turn", BASELINE_STAMINA_REGEN_PER_TURN) + (
        character_stat_factor("stamina_regen_per_level", STAMINA_REGEN_PER_LEVEL)
        * (_safe_float(physical_stamina, primary_baseline) - primary_baseline)
    )
    return max(0.0, regen_per_turn / max(0.0001, baseline_turn_seconds()))


def coerce_exertion_level(value: Any) -> ExertionLevel:
    if isinstance(value, ExertionLevel):
        return value
    text = str(value or ExertionLevel.FRESH.name).strip().upper()
    if text in ExertionLevel.__members__:
        return ExertionLevel[text]
    return ExertionLevel.FRESH


def compute_exertion_level(stamina_current: float, stamina_limit: float) -> ExertionLevel:
    stamina_limit = max(1.0, _safe_float(stamina_limit, baseline_stamina_limit()))
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
        return battle_factor("overcharged_damage_multiplier", OVERCHARGED_DAMAGE_MULTIPLIER)
    if exertion == ExertionLevel.TIRED:
        return battle_factor("tired_damage_multiplier", TIRED_DAMAGE_MULTIPLIER)
    return 1.0


def accuracy_bonus_for_exertion(exertion_level: Any) -> float:
    exertion = coerce_exertion_level(exertion_level)
    if exertion == ExertionLevel.OVERCHARGED:
        return battle_factor("overcharged_accuracy_bonus", OVERCHARGED_ACCURACY_BONUS)
    if exertion == ExertionLevel.TIRED:
        return battle_factor("tired_accuracy_bonus", TIRED_ACCURACY_BONUS)
    return 0.0


def speed_multiplier_for_exertion(exertion_level: Any) -> float:
    exertion = coerce_exertion_level(exertion_level)
    if exertion == ExertionLevel.OVERCHARGED:
        return battle_factor("overcharged_speed_multiplier", OVERCHARGED_SPEED_MULTIPLIER)
    if exertion == ExertionLevel.TIRED:
        return battle_factor("tired_speed_multiplier", TIRED_SPEED_MULTIPLIER)
    if exertion == ExertionLevel.EXHAUSTED:
        return battle_factor("exhausted_speed_multiplier", EXHAUSTED_SPEED_MULTIPLIER)
    return battle_factor("fresh_speed_multiplier", FRESH_SPEED_MULTIPLIER)


def defense_stat_penalty_for_exertion(exertion_level: Any) -> float:
    if coerce_exertion_level(exertion_level) == ExertionLevel.EXHAUSTED:
        return exhausted_defense_stat_penalty()
    return 0.0


def can_take_offensive_action(exertion_level: Any) -> bool:
    return coerce_exertion_level(exertion_level) != ExertionLevel.EXHAUSTED


def effective_speed_factor(base_speed: float, exertion_level: Any) -> float:
    return max(minimum_speed_factor(), _safe_float(base_speed, BASELINE_SPEED_FACTOR) * speed_multiplier_for_exertion(exertion_level))


def action_interval_seconds(base_speed: float, exertion_level: Any) -> float:
    return baseline_turn_seconds() / effective_speed_factor(base_speed, exertion_level)


def start_time_gap_seconds(participant_count: int) -> float:
    return baseline_turn_seconds() / max(1, int(participant_count or 1))


def update_exertion_state(state_like) -> ExertionLevel:
    exertion = compute_exertion_level(
        getattr(state_like, "stamina_current", baseline_stamina_limit()),
        getattr(state_like, "stamina_limit", baseline_stamina_limit()),
    )
    setattr(state_like, "exertion_level", exertion.name)
    return exertion


def sync_stamina(state_like, current_time: float) -> float:
    current_time = max(0.0, _safe_float(current_time, 0.0))
    last_time = max(0.0, _safe_float(getattr(state_like, "stamina_last_update_time", current_time), current_time))
    elapsed = max(0.0, current_time - last_time)
    stamina_current = _safe_float(getattr(state_like, "stamina_current", baseline_stamina_limit()), baseline_stamina_limit())
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
    limit = max(1.0, _safe_float(stamina_limit, baseline_stamina_limit()))
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
    return battle_factor("hit_stamina_damage_base", 5.0) + min(
        battle_factor("hit_stamina_damage_cap", 5.0),
        max(0.0, _safe_float(damage, 0.0)) * battle_factor("hit_stamina_damage_scale", 0.20),
    )


def next_window_start(current_time: float) -> float:
    current_time = max(0.0, _safe_float(current_time, 0.0))
    if current_time <= 0.0:
        return 0.0
    turn_seconds = max(0.0001, baseline_turn_seconds())
    return math.ceil(current_time / turn_seconds) * turn_seconds
