from __future__ import annotations

from dataclasses import dataclass
import math
import random

from src.config.tuning import battle_factor, character_stat_factor
from src.domain.Character import Character
from src.domain.CharacterUtil import HitLocation
from src.domain.Items import Weapon


@dataclass(frozen=True)
class DamageCalculatorConfig:
    alpha: float = 0.80
    penetrationPowerScale: float = 0.50
    resistanceDeficitFloor: float = 5.0
    resistanceDeficitScale: float = 0.20
    resistanceFalloffSharpness: float = 5.0
    armorSoakCoeff: float = 0.10
    bodyC: float = 30.0
    bodyDelta: float = 1.5
    bodyK: float = 5.0
    baseHitChance: float = 0.65
    statDeltaHitScale: float = 0.03
    minHitChance: float = 0.35
    maxHitChance: float = 0.90
    magicResistanceMinMultiplier: float = 0.05
    magicResistanceSoftness: float = 12.0


@dataclass(frozen=True)
class DamageBreakdown:
    rollArmor: float
    rollHp: float
    powerMultiplier: float

    armorBefore: float
    armorDamage: float
    armorAfter: float

    hpThroughArmor: float
    hpSpill: float
    hpPreResistance: float

    penetration: float
    penetrationEffectiveness: float

    hpAfterResistance: float
    penetrationDamageReduction: float

    hpFinal: float

    @property
    def couplingFraction(self) -> float:
        return self.penetrationEffectiveness

    @property
    def hpCoupled(self) -> float:
        return self.hpAfterResistance

    @property
    def bodyArmorRating(self) -> float:
        return 0.0

    @property
    def bodyDamageReduction(self) -> float:
        return 0.0


@dataclass(frozen=True)
class MagicDamageBreakdown:
    hitChance: float
    didHit: bool
    basePower: float
    powerMultiplier: float
    resistanceMultiplier: float
    hpFinal: float


class DamageCalculator:
    def __init__(self, config: DamageCalculatorConfig | None = None, rng: random.Random | None = None):
        self._static_config = config
        self._rng = rng if rng is not None else random.Random()

    def _get_config(self) -> DamageCalculatorConfig:
        if self._static_config is not None:
            return self._static_config
        return DamageCalculatorConfig(
            alpha=character_stat_factor("derived_stat_alpha", 0.80),
            penetrationPowerScale=battle_factor("penetration_power_scale", 0.50),
            resistanceDeficitFloor=battle_factor("resistance_deficit_floor", 5.0),
            resistanceDeficitScale=battle_factor("resistance_deficit_scale", 0.20),
            resistanceFalloffSharpness=battle_factor("resistance_falloff_sharpness", 5.0),
            armorSoakCoeff=battle_factor("armor_soak_coeff", 0.10),
            bodyC=30.0,
            bodyDelta=1.5,
            bodyK=5.0,
            baseHitChance=battle_factor("base_hit_chance", 0.65),
            statDeltaHitScale=battle_factor("stat_delta_hit_scale", 0.03),
            minHitChance=battle_factor("min_hit_chance", 0.35),
            maxHitChance=battle_factor("max_hit_chance", 0.90),
            magicResistanceMinMultiplier=battle_factor("magic_resistance_min_multiplier", 0.05),
            magicResistanceSoftness=battle_factor("magic_resistance_softness", 12.0),
        )

    def calculate_hit_chance(
        self,
        attacker_stat: float,
        defender_stat: float,
        congestion_penalty: float = 0.0,
        firing_through_engagement_penalty: float = 0.0,
        range_penalty: float = 0.0,
        bonus: float = 0.0,
    ) -> float:
        config = self._get_config()
        chance = config.baseHitChance
        chance += (float(attacker_stat) - float(defender_stat)) * config.statDeltaHitScale
        chance -= float(congestion_penalty)
        chance -= float(firing_through_engagement_penalty)
        chance -= float(range_penalty)
        chance += float(bonus)
        return max(config.minHitChance, min(config.maxHitChance, chance))

    def roll_hit(
        self,
        attacker_stat: float,
        defender_stat: float,
        congestion_penalty: float = 0.0,
        firing_through_engagement_penalty: float = 0.0,
        range_penalty: float = 0.0,
        bonus: float = 0.0,
    ) -> tuple[bool, float]:
        chance = self.calculate_hit_chance(
            attacker_stat=attacker_stat,
            defender_stat=defender_stat,
            congestion_penalty=congestion_penalty,
            firing_through_engagement_penalty=firing_through_engagement_penalty,
            range_penalty=range_penalty,
            bonus=bonus,
        )
        return self._rng.random() <= chance, chance

    def calculate_physical_hit(
        self,
        attacker: Character,
        defender: Character,
        weapon: Weapon,
        targetArmor: float,
    ) -> DamageBreakdown:
        config = self._get_config()
        attacker_physical_power = float(getattr(attacker.finalAttributes, "physicalPower", 5.0))
        defender_physical_resistance = float(getattr(defender.finalAttributes, "physicalResistance", 5.0))

        attacker_physical_power = max(0.0001, attacker_physical_power)
        defender_physical_resistance = max(0.0, defender_physical_resistance)

        damage_min = float(getattr(weapon, "damageMin", 0.0))
        damage_max = float(getattr(weapon, "damageMax", damage_min))
        if damage_max < damage_min:
            raise ValueError(f"weapon.damageMax ({damage_max}) must be >= weapon.damageMin ({damage_min}).")

        roll_armor = self._rng.uniform(damage_min, damage_max)
        roll_hp = self._rng.uniform(damage_min, damage_max)

        power_multiplier = self._compute_power_multiplier(attacker_physical_power)

        armor_before = max(0.0, float(targetArmor))

        armor_multiplier = float(getattr(weapon, "armorMultiplier", 1.0))
        armor_damage_unclamped = roll_armor * power_multiplier * armor_multiplier
        armor_damage = min(armor_before, max(0.0, armor_damage_unclamped))
        armor_after = max(0.0, armor_before - armor_damage)

        ignore_armor_fraction = self._clamp_01(float(getattr(weapon, "ignoreArmorFraction", 0.0)))

        hp_through_armor_raw = (roll_hp * power_multiplier * ignore_armor_fraction) - (
            armor_after * config.armorSoakCoeff
        )
        hp_through_armor = max(0.0, hp_through_armor_raw)

        hp_spill = 0.0
        if armor_after <= 0.0:
            hp_spill_raw = (roll_hp * power_multiplier * (1.0 - ignore_armor_fraction)) - armor_damage
            hp_spill = max(0.0, hp_spill_raw)

        hp_pre_resistance = hp_through_armor + hp_spill

        penetration = self._compute_penetration(weapon=weapon, attacker_physical_power=attacker_physical_power)
        penetration_effectiveness = self._compute_coupling_fraction(
            penetration=penetration,
            defender_physical_resistance=defender_physical_resistance,
        )

        hp_after_resistance = hp_pre_resistance * penetration_effectiveness
        penetration_damage_reduction = 1.0 - penetration_effectiveness
        hp_final = hp_after_resistance

        return DamageBreakdown(
            rollArmor=roll_armor,
            rollHp=roll_hp,
            powerMultiplier=power_multiplier,
            armorBefore=armor_before,
            armorDamage=armor_damage,
            armorAfter=armor_after,
            hpThroughArmor=hp_through_armor,
            hpSpill=hp_spill,
            hpPreResistance=hp_pre_resistance,
            penetration=penetration,
            penetrationEffectiveness=penetration_effectiveness,
            hpAfterResistance=hp_after_resistance,
            penetrationDamageReduction=penetration_damage_reduction,
            hpFinal=hp_final,
        )

    def calculate_magic_hit(
        self,
        attacker: Character,
        defender: Character,
        spell_power: float,
        hit_chance: float | None = None,
        did_hit: bool | None = None,
    ) -> MagicDamageBreakdown:
        config = self._get_config()
        attacker_magic_power = max(0.0001, float(getattr(attacker.finalAttributes, "magicPower", 5.0)))
        defender_magic_resistance = max(0.0, float(getattr(defender.finalAttributes, "magicResistance", 5.0)))
        if hit_chance is None:
            hit_chance = self.calculate_hit_chance(attacker_magic_power, defender_magic_resistance)
        if did_hit is None:
            did_hit = self._rng.random() <= hit_chance
        power_multiplier = (attacker_magic_power / max(0.0001, character_stat_factor("primary_stat_baseline", 5.0))) ** config.alpha
        resistance_multiplier = max(
            config.magicResistanceMinMultiplier,
            1.0 - (defender_magic_resistance / (defender_magic_resistance + max(0.0001, config.magicResistanceSoftness))),
        )
        hp_final = 0.0
        if did_hit:
            hp_final = max(0.0, float(spell_power) * power_multiplier * resistance_multiplier)
        return MagicDamageBreakdown(
            hitChance=hit_chance,
            didHit=did_hit,
            basePower=float(spell_power),
            powerMultiplier=power_multiplier,
            resistanceMultiplier=resistance_multiplier,
            hpFinal=hp_final,
        )

    def calculate_physical_hit_to_location(
        self,
        attacker: Character,
        defender: Character,
        weapon: Weapon,
        location: HitLocation,
        applyArmorDamageToGear: bool = True,
    ) -> DamageBreakdown:
        target_armor = 0.0
        if getattr(defender, "gear", None) is not None and hasattr(defender.gear, "get_armor"):
            target_armor = float(defender.gear.get_armor(location))

        result = self.calculate_physical_hit(
            attacker=attacker,
            defender=defender,
            weapon=weapon,
            targetArmor=target_armor,
        )

        if (
            applyArmorDamageToGear
            and getattr(defender, "gear", None) is not None
            and hasattr(defender.gear, "set_armor")
        ):
            defender.gear.set_armor(location, result.armorAfter)

        return result

    def _compute_power_multiplier(self, attacker_physical_power: float) -> float:
        config = self._get_config()
        baseline_power = max(0.0001, character_stat_factor("primary_stat_baseline", 5.0))
        ratio = attacker_physical_power / baseline_power
        ratio = max(0.0001, ratio)
        return ratio ** config.alpha

    def _compute_penetration(self, weapon: Weapon, attacker_physical_power: float) -> float:
        config = self._get_config()
        baseline_power = max(0.0001, character_stat_factor("primary_stat_baseline", 5.0))
        bonus_power = max(0.0, attacker_physical_power - baseline_power)
        penetration_base = float(getattr(weapon, "penetrationBase", 0.0))
        penetration = penetration_base + (config.penetrationPowerScale * bonus_power)
        return max(0.0, penetration)

    def _compute_coupling_fraction(self, penetration: float, defender_physical_resistance: float) -> float:
        config = self._get_config()
        penetration = max(0.0, float(penetration))
        defender_physical_resistance = max(0.0, float(defender_physical_resistance))

        if defender_physical_resistance <= 0.0 or penetration >= defender_physical_resistance:
            return 1.0

        deficit = defender_physical_resistance - penetration
        falloff_window = max(
            config.resistanceDeficitFloor,
            defender_physical_resistance * config.resistanceDeficitScale,
        )
        if deficit >= falloff_window:
            return 0.0

        normalized_deficit = self._clamp_01(deficit / falloff_window)
        sharpness = max(0.0001, float(config.resistanceFalloffSharpness))
        decay = math.exp(-sharpness * normalized_deficit)
        floor_decay = math.exp(-sharpness)
        scaled_decay = (decay - floor_decay) / (1.0 - floor_decay)
        return self._clamp_01(scaled_decay)

    @staticmethod
    def _clamp_01(value: float) -> float:
        if value < 0.0:
            return 0.0
        if value > 1.0:
            return 1.0
        return value
