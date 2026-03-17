from __future__ import annotations

from dataclasses import dataclass
import random

from src.domain.Character import Character
from src.domain.CharacterUtil import HitLocation
from src.domain.Items import Weapon


@dataclass(frozen=True)
class DamageCalculatorConfig:
    alpha: float = 0.80
    penetrationPowerScale: float = 0.50
    couplingGamma: float = 3.0
    couplingFloor: float = 0.02
    armorSoakCoeff: float = 0.10
    bodyC: float = 30.0
    bodyDelta: float = 1.5
    bodyK: float = 5.0
    baseHitChance: float = 0.65
    statDeltaHitScale: float = 0.03
    minHitChance: float = 0.35
    maxHitChance: float = 0.90


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
    couplingFraction: float

    hpCoupled: float
    bodyArmorRating: float
    bodyDamageReduction: float

    hpFinal: float


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
        self._config = config if config is not None else DamageCalculatorConfig()
        self._rng = rng if rng is not None else random.Random()

    def calculate_hit_chance(
        self,
        attacker_stat: float,
        defender_stat: float,
        congestion_penalty: float = 0.0,
        firing_through_engagement_penalty: float = 0.0,
        range_penalty: float = 0.0,
        bonus: float = 0.0,
    ) -> float:
        chance = self._config.baseHitChance
        chance += (float(attacker_stat) - float(defender_stat)) * self._config.statDeltaHitScale
        chance -= float(congestion_penalty)
        chance -= float(firing_through_engagement_penalty)
        chance -= float(range_penalty)
        chance += float(bonus)
        return max(self._config.minHitChance, min(self._config.maxHitChance, chance))

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
            armor_after * self._config.armorSoakCoeff
        )
        hp_through_armor = max(0.0, hp_through_armor_raw)

        hp_spill = 0.0
        if armor_after <= 0.0:
            hp_spill_raw = (roll_hp * power_multiplier * (1.0 - ignore_armor_fraction)) - armor_damage
            hp_spill = max(0.0, hp_spill_raw)

        hp_pre_resistance = hp_through_armor + hp_spill

        penetration = self._compute_penetration(weapon=weapon, attacker_physical_power=attacker_physical_power)
        coupling_fraction = self._compute_coupling_fraction(
            penetration=penetration,
            defender_physical_resistance=defender_physical_resistance,
        )

        hp_coupled = hp_pre_resistance * coupling_fraction

        body_armor_rating = self._compute_body_armor_rating(defender_physical_resistance)
        body_damage_reduction = self._compute_body_damage_reduction(
            body_armor_rating=body_armor_rating,
            incoming_hp=hp_coupled,
        )

        hp_final = hp_coupled * (1.0 - body_damage_reduction)

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
            couplingFraction=coupling_fraction,
            hpCoupled=hp_coupled,
            bodyArmorRating=body_armor_rating,
            bodyDamageReduction=body_damage_reduction,
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
        attacker_magic_power = max(0.0001, float(getattr(attacker.finalAttributes, "magicPower", 5.0)))
        defender_magic_resistance = max(0.0, float(getattr(defender.finalAttributes, "magicResistance", 5.0)))
        if hit_chance is None:
            hit_chance = self.calculate_hit_chance(attacker_magic_power, defender_magic_resistance)
        if did_hit is None:
            did_hit = self._rng.random() <= hit_chance
        power_multiplier = (attacker_magic_power / 5.0) ** self._config.alpha
        resistance_multiplier = max(0.05, 1.0 - (defender_magic_resistance / (defender_magic_resistance + 12.0)))
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
        baseline_power = 5.0
        ratio = attacker_physical_power / baseline_power
        ratio = max(0.0001, ratio)
        return ratio ** self._config.alpha

    def _compute_penetration(self, weapon: Weapon, attacker_physical_power: float) -> float:
        baseline_power = 5.0
        bonus_power = max(0.0, attacker_physical_power - baseline_power)
        penetration_base = float(getattr(weapon, "penetrationBase", 0.0))
        penetration = penetration_base + (self._config.penetrationPowerScale * bonus_power)
        return max(0.0, penetration)

    def _compute_coupling_fraction(self, penetration: float, defender_physical_resistance: float) -> float:
        denominator = penetration + defender_physical_resistance
        if denominator <= 0.0:
            return 1.0

        ratio = penetration / denominator
        ratio = self._clamp_01(ratio)

        coupling = ratio ** self._config.couplingGamma
        return max(self._config.couplingFloor, coupling)

    def _compute_body_armor_rating(self, defender_physical_resistance: float) -> float:
        baseline_resistance = 5.0
        ratio = defender_physical_resistance / baseline_resistance
        ratio = max(0.0, ratio)

        body_armor = self._config.bodyC * (ratio ** self._config.bodyDelta)
        return max(0.0, body_armor)

    def _compute_body_damage_reduction(self, body_armor_rating: float, incoming_hp: float) -> float:
        incoming_hp = max(0.0, incoming_hp)
        if incoming_hp <= 0.0:
            return 0.0

        denominator = body_armor_rating + (self._config.bodyK * incoming_hp)
        if denominator <= 0.0:
            return 0.0

        reduction = body_armor_rating / denominator
        return self._clamp_01(reduction)

    @staticmethod
    def _clamp_01(value: float) -> float:
        if value < 0.0:
            return 0.0
        if value > 1.0:
            return 1.0
        return value
