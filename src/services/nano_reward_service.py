from __future__ import annotations

from dataclasses import dataclass

from src.config.tuning import nano_reward_factor, nano_reward_factor_int


@dataclass(frozen=True)
class NanoRewardBreakdown:
    powerLevel: float
    defeatedCount: int
    nanoPerPowerPoint: float
    baseNano: int
    teamHighestLevel: int
    enemyLevel: int
    levelDifference: int
    levelMultiplier: float
    penalizedEquipmentApplied: bool
    penaltyMultiplier: float
    totalNano: int


class NanoRewardCalculator:
    def __init__(self, power_rating_service):
        self.power_rating_service = power_rating_service

    def enemy_power_level(self, character) -> float:
        if character is None or self.power_rating_service is None:
            return 0.0
        return max(0.0, float(self.power_rating_service.character_power_level(character) or 0.0))

    @staticmethod
    def level_difference(enemy_level: int, team_highest_level: int) -> int:
        return max(0, int(enemy_level or 0) - int(team_highest_level or 0))

    def level_multiplier(self, enemy_level: int, team_highest_level: int) -> float:
        difference = self.level_difference(enemy_level, team_highest_level)
        if difference <= 0:
            return 1.0
        return max(1.0, float(difference) * nano_reward_factor("level_difference_multiplier", 5.0))

    @staticmethod
    def penalty_multiplier(penalized_equipment: bool) -> float:
        if not penalized_equipment:
            return 1.0
        return max(0.0, nano_reward_factor("modern_weapon_penalty_multiplier", 0.05))

    def calculate_reward(
        self,
        *,
        power_level: float,
        enemy_level: int,
        team_highest_level: int,
        penalized_equipment: bool = False,
        defeated_count: int = 1,
    ) -> NanoRewardBreakdown:
        count = max(1, int(defeated_count or 1))
        resolved_power = max(0.0, float(power_level or 0.0))
        nano_per_power = max(0.0, nano_reward_factor("nano_per_power_point", 4000.0))
        base_nano = int(round(resolved_power * nano_per_power * count))
        level_difference = self.level_difference(enemy_level, team_highest_level)
        level_multiplier = self.level_multiplier(enemy_level, team_highest_level)
        penalty_multiplier = self.penalty_multiplier(penalized_equipment)
        total_nano = int(round(base_nano * level_multiplier * penalty_multiplier))
        total_nano = max(nano_reward_factor_int("minimum_nano_reward", 0), total_nano)
        return NanoRewardBreakdown(
            powerLevel=resolved_power,
            defeatedCount=count,
            nanoPerPowerPoint=nano_per_power,
            baseNano=base_nano,
            teamHighestLevel=max(0, int(team_highest_level or 0)),
            enemyLevel=max(0, int(enemy_level or 0)),
            levelDifference=level_difference,
            levelMultiplier=level_multiplier,
            penalizedEquipmentApplied=bool(penalized_equipment),
            penaltyMultiplier=penalty_multiplier,
            totalNano=total_nano,
        )

    def calculate_for_character(
        self,
        character,
        *,
        enemy_level: int,
        team_highest_level: int,
        penalized_equipment: bool = False,
        defeated_count: int = 1,
    ) -> NanoRewardBreakdown:
        return self.calculate_reward(
            power_level=self.enemy_power_level(character),
            enemy_level=enemy_level,
            team_highest_level=team_highest_level,
            penalized_equipment=penalized_equipment,
            defeated_count=defeated_count,
        )
