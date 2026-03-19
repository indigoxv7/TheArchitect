from __future__ import annotations

import copy
import random
import re
from dataclasses import dataclass
from typing import Any

from src.config.tuning import battle_factor, character_stat_factor
from src.domain.character import Character, HealthState
from src.domain.character_util import HitLocation
from src.domain.items import Weapon
from src.domain.combat_timing import (
    CombatRuntimeState,
    baseline_turn_seconds,
    initialize_runtime_fields,
    speed_factor_from_attributes,
    start_time_gap_seconds,
    stamina_limit_from_physical_stamina,
    stamina_regen_per_second_from_physical_stamina,
)


_DICE_PATTERN = re.compile(r"^\s*(\d+)\s*d\s*(\d+)(?:\s*([+-])\s*(\d+(?:\.\d+)?))?\s*$", re.IGNORECASE)
_LEADING_NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")


@dataclass(frozen=True)
class DuelTimeline:
    first_side: str
    second_side: str
    turn_gap: float
    next_action_times: dict[str, float]
    tie_break_order: list[str]


def parse_numeric_value(value: Any, default: float = 0.0, *, allow_dice_average: bool = False) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip()
    if not text:
        return float(default)
    try:
        return float(text)
    except ValueError:
        pass

    if allow_dice_average:
        dice_match = _DICE_PATTERN.match(text)
        if dice_match:
            count = int(dice_match.group(1))
            faces = int(dice_match.group(2))
            sign = dice_match.group(3)
            modifier = float(dice_match.group(4) or 0.0)
            average = count * ((faces + 1.0) / 2.0)
            if sign == "-":
                average -= modifier
            else:
                average += modifier
            return max(0.0, average)

    match = _LEADING_NUMBER_PATTERN.search(text)
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return float(default)
    return float(default)


def character_speed(character: Character) -> float:
    get_speed = getattr(character, "GetSpeed", None)
    if callable(get_speed):
        return max(character_stat_factor("minimum_speed_factor", 0.1), float(get_speed()))
    attrs = getattr(character, "finalAttributes", getattr(character, "attributes", None))
    physical_power = float(getattr(attrs, "physicalPower", 5.0))
    magic_power = float(getattr(attrs, "magicPower", 5.0))
    return speed_factor_from_attributes(physical_power, magic_power)


def character_stamina_limit(character: Character) -> float:
    get_stamina_limit = getattr(character, "GetStaminaLimit", None)
    if callable(get_stamina_limit):
        return max(1.0, float(get_stamina_limit()))
    attrs = getattr(character, "finalAttributes", getattr(character, "attributes", None))
    return stamina_limit_from_physical_stamina(float(getattr(attrs, "physicalStamina", 5.0)))


def character_stamina_regen(character: Character) -> float:
    get_regen = getattr(character, "GetStaminaRegenPerSecond", None)
    if callable(get_regen):
        return max(0.0, float(get_regen()))
    attrs = getattr(character, "finalAttributes", getattr(character, "attributes", None))
    return stamina_regen_per_second_from_physical_stamina(float(getattr(attrs, "physicalStamina", 5.0)))


def build_runtime_state(character: Character) -> CombatRuntimeState:
    stamina_limit = character_stamina_limit(character)
    runtime = CombatRuntimeState(
        stamina_current=stamina_limit,
        stamina_limit=stamina_limit,
        stamina_regen_per_second=character_stamina_regen(character),
    )
    initialize_runtime_fields(
        runtime,
        stamina_limit=runtime.stamina_limit,
        stamina_regen_per_second=runtime.stamina_regen_per_second,
        stamina_current=runtime.stamina_limit,
        stamina_last_update_time=0.0,
        next_action_time=0.0,
    )
    return runtime


def initialize_duel_timeline(rng: random.Random) -> DuelTimeline:
    first_side = "left" if rng.random() < 0.5 else "right"
    second_side = "right" if first_side == "left" else "left"
    turn_gap = start_time_gap_seconds(2)
    return DuelTimeline(
        first_side=first_side,
        second_side=second_side,
        turn_gap=turn_gap,
        next_action_times={
            first_side: 0.0,
            second_side: turn_gap,
        },
        tie_break_order=[first_side, second_side],
    )


def select_next_duel_side(
    alive_sides: list[str], next_action_times: dict[str, float], tie_break_order: list[str]
) -> str | None:
    if not alive_sides:
        return None
    if len(alive_sides) == 1:
        return alive_sides[0]
    priority = {side: index for index, side in enumerate(tie_break_order)}
    return min(
        alive_sides,
        key=lambda side: (
            float(next_action_times.get(side, 0.0)),
            priority.get(side, len(priority)),
        ),
    )


def round_number_for_time(turn_start_time: float) -> int:
    return int(turn_start_time // baseline_turn_seconds()) + 1


def max_duel_battle_time(max_rounds: int) -> float:
    return max_rounds * baseline_turn_seconds()


def roll_hit_location(rng: random.Random) -> HitLocation:
    weights = [
        (HitLocation.HEAD, battle_factor("combat_sim_head_hit_weight", 0.15)),
        (HitLocation.BODY, battle_factor("combat_sim_body_hit_weight", 0.45)),
        (HitLocation.ARMS, battle_factor("combat_sim_arms_hit_weight", 0.20)),
        (HitLocation.LEGS, battle_factor("combat_sim_legs_hit_weight", 0.20)),
    ]
    roll = rng.random()
    cursor = 0.0
    for location, weight in weights:
        cursor += weight
        if roll <= cursor:
            return location
    return HitLocation.BODY


def scaled_weapon_for_damage_multiplier(weapon: Weapon, damage_multiplier: float) -> Weapon:
    if abs(float(damage_multiplier) - 1.0) < 0.0001:
        return weapon
    scaled_weapon = copy.deepcopy(weapon)
    scaled_weapon.damageMin = max(0.0, float(getattr(weapon, "damageMin", 0.0) or 0.0) * float(damage_multiplier))
    scaled_weapon.damageMax = max(
        scaled_weapon.damageMin,
        float(getattr(weapon, "damageMax", scaled_weapon.damageMin) or scaled_weapon.damageMin)
        * float(damage_multiplier),
    )
    return scaled_weapon


def character_max_health(character: Character) -> float:
    get_max_health = getattr(character, "GetMaxHealth", None)
    if callable(get_max_health):
        return max(1.0, float(get_max_health()))
    return 100.0


def health_state_for_character(character: Character) -> HealthState:
    health = max(0.0, float(getattr(character, "health", 0.0) or 0.0))
    if health <= 0.0:
        return HealthState.UNCONSCIOUS
    percent = health / character_max_health(character)
    if percent >= character_stat_factor("healthy_health_ratio_threshold", 0.76):
        return HealthState.HEALTHY
    if percent >= character_stat_factor("injured_health_ratio_threshold", 0.51):
        return HealthState.INJURED
    if percent >= character_stat_factor("heavily_injured_health_ratio_threshold", 0.26):
        return HealthState.HEAVILY_INJURED
    return HealthState.DYING
