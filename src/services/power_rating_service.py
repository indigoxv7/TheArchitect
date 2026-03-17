from __future__ import annotations

import copy
import random
import re
from dataclasses import dataclass

from src.domain.Character import Character
from src.domain.CharacterUtil import (
    Attribute,
    Attributes,
    Bonus,
    BonusType,
    ConsumableKind,
    DamageType,
    EquipSlot,
    HitLocation,
    ItemType,
)
from src.domain.Items import Armor, Consumable, Gear, Item, Weapon
from src.domain.Spells import Spell
from src.services.combat_loadout_service import select_active_character_weapon
from src.services.damage_calculator import DamageCalculator


@dataclass(frozen=True)
class SimulationSummary:
    sampleCount: int
    wins: int
    losses: int
    draws: int
    winRate: float
    averageRounds: float
    averageRemainingHealth: float
    averageOpponentRemainingHealth: float
    averageHealthMargin: float
    candidateAdvantage: float
    referenceAdvantage: float
    simulatedPowerEquivalent: float
    recommendedPowerLevel: float


@dataclass
class _Combatant:
    character: Character
    consumable: Consumable | None = None
    consumable_used: bool = False


class PowerRatingService:
    DEFAULT_SAMPLE_COUNT = 300
    MAX_DUEL_ROUNDS = 30
    SIMULATION_HEALTH = 100.0
    PERFORMANCE_MARGIN_WEIGHT = 0.25
    RECOMMENDED_SIMULATION_WEIGHT = 0.80
    RECOMMENDED_HEURISTIC_WEIGHT = 0.20
    NEUTRAL_AFFINITY = 0.5

    _DICE_PATTERN = re.compile(r"^\s*(\d+)\s*d\s*(\d+)(?:\s*([+-])\s*(\d+(?:\.\d+)?))?\s*$", re.IGNORECASE)
    _LEADING_NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")

    def __init__(self, spell_service=None, item_service=None, race_service=None, sample_count: int = DEFAULT_SAMPLE_COUNT, seed: int = 1337):
        self.spell_service = spell_service
        self.item_service = item_service
        self.race_service = race_service
        self.sample_count = max(25, int(sample_count or self.DEFAULT_SAMPLE_COUNT))
        self.seed = int(seed)

    @classmethod
    def parse_numeric_value(cls, value, default: float = 0.0) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value or "").strip()
        if not text:
            return float(default)
        try:
            return float(text)
        except ValueError:
            pass

        dice_match = cls._DICE_PATTERN.match(text)
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

        match = cls._LEADING_NUMBER_PATTERN.search(text)
        if match:
            try:
                return float(match.group(0))
            except ValueError:
                return float(default)
        return float(default)

    @classmethod
    def normalize_affinity_fraction(cls, value) -> float:
        numeric = cls.parse_numeric_value(value, cls.NEUTRAL_AFFINITY)
        if isinstance(value, int):
            numeric /= 100.0
        elif isinstance(value, float):
            if numeric >= 1.0:
                numeric /= 100.0
        else:
            text = str(value or "").strip()
            if text and ("." not in text and numeric <= 100.0):
                numeric /= 100.0
            elif numeric > 1.0:
                numeric /= 100.0
        return max(0.0, min(1.0, numeric))

    @classmethod
    def affinity_power_multiplier(cls, value) -> float:
        fraction = cls.normalize_affinity_fraction(value)
        return 0.8 + (fraction * 0.4)

    def affinity_multiplier_for_spell(self, character: Character | None, spell: Spell | None) -> float:
        if character is None or spell is None:
            return 1.0
        if hasattr(character, "CalculateBonus"):
            character.CalculateBonus()
        affinities = getattr(character, "finalAffinities", None) or getattr(character, "affinities", None)
        if affinities is None:
            return 1.0
        affinity_name = getattr(getattr(spell, "affinity", None), "name", str(getattr(spell, "affinity", "MANA"))).upper()
        return self.affinity_power_multiplier(getattr(affinities, affinity_name.lower(), self.NEUTRAL_AFFINITY))

    @staticmethod
    def _sum_attributes(attributes: Attributes | None) -> float:
        if attributes is None:
            return 0.0
        return float(
            getattr(attributes, "physicalPower", 0.0)
            + getattr(attributes, "physicalStamina", 0.0)
            + getattr(attributes, "physicalResistance", 0.0)
            + getattr(attributes, "magicPower", 0.0)
            + getattr(attributes, "magicStamina", 0.0)
            + getattr(attributes, "magicResistance", 0.0)
        )

    def _attribute_baseline(self, character: Character | None, attribute: Attribute) -> float:
        if character is None:
            return 5.0
        attributes = getattr(character, "attributes", None)
        mapping = {
            Attribute.PHYSICAL_POWER: float(getattr(attributes, "physicalPower", 5.0)),
            Attribute.PHYSICAL_STAMINA: float(getattr(attributes, "physicalStamina", 5.0)),
            Attribute.PHYSICAL_RESISTANCE: float(getattr(attributes, "physicalResistance", 5.0)),
            Attribute.MAGIC_POWER: float(getattr(attributes, "magicPower", 5.0)),
            Attribute.MAGIC_STAMINA: float(getattr(attributes, "magicStamina", 5.0)),
            Attribute.MAGIC_RESISTANCE: float(getattr(attributes, "magicResistance", 5.0)),
        }
        return mapping.get(attribute, 5.0)

    def bonus_power_points(self, bonuses: list[Bonus] | None, character: Character | None = None) -> float:
        total = 0.0
        if not isinstance(bonuses, list):
            return total
        for bonus in bonuses:
            if not isinstance(bonus, Bonus):
                continue
            attribute_bonus = getattr(bonus, "attributeBonus", None)
            if attribute_bonus is None:
                continue
            attribute = getattr(attribute_bonus, "attribute", None)
            amount = float(getattr(attribute_bonus, "bonus", 0.0) or 0.0)
            if attribute is None or amount == 0.0:
                continue
            if bonus.bonusType == BonusType.FLAT:
                total += amount * 6.0 if attribute == Attribute.ALL_ATTRIBUTES else amount
            else:
                if attribute == Attribute.ALL_ATTRIBUTES:
                    total += self._sum_attributes(getattr(character, "attributes", None) or Attributes()) * (amount / 100.0)
                else:
                    total += self._attribute_baseline(character, attribute) * (amount / 100.0)
        return total

    def heuristic_spell_power_level(self, spell: Spell) -> float:
        base_power = self.parse_numeric_value(getattr(spell, "power", 0.0), 0.0)
        level_bonus = max(0.0, float(getattr(spell, "level", 0) or 0)) * 0.5
        range_bonus = min(25.0, self.parse_numeric_value(getattr(spell, "range", 0.0), 0.0)) * 0.03
        duration_bonus = min(12.0, self.parse_numeric_value(getattr(spell, "duration", 0.0), 0.0)) * 0.05
        casting_penalty = min(0.5, self.parse_numeric_value(getattr(spell, "casting_time", 0.0), 0.0) * 0.03)
        components = getattr(spell, "components", {}) if isinstance(getattr(spell, "components", {}), dict) else {}
        component_bonus = 0.1 * sum(1 for key in ("verbal", "somatic", "material") if components.get(key))
        return max(0.0, base_power + level_bonus + range_bonus + duration_bonus + component_bonus - casting_penalty)

    def spell_power_level(self, spell: Spell, affinity_value=None) -> float:
        base = float(getattr(spell, "powerLevel", 0.0) or 0.0)
        if base <= 0.0:
            base = self.heuristic_spell_power_level(spell)
        multiplier = 1.0 if affinity_value is None else self.affinity_power_multiplier(affinity_value)
        return max(0.0, base * multiplier)
    def heuristic_item_power_level(self, item: Item) -> float:
        stat_power = self.bonus_power_points(getattr(item, "statBonuses", []))
        if isinstance(item, Weapon):
            return max(0.0, stat_power + self._heuristic_weapon_impact(item))
        if isinstance(item, Armor):
            return max(0.0, stat_power + self._heuristic_armor_impact(item))
        if isinstance(item, Consumable):
            return max(0.0, stat_power + self._heuristic_consumable_impact(item))
        return max(0.0, stat_power)

    def item_power_level(self, item: Item) -> float:
        base = float(getattr(item, "powerLevel", 0.0) or 0.0)
        if base > 0.0:
            return base
        return self.heuristic_item_power_level(item)

    def _character_affinity_value(self, character: Character, spell: Spell) -> float:
        affinities = getattr(character, "finalAffinities", None) or getattr(character, "affinities", None)
        if affinities is None:
            return self.NEUTRAL_AFFINITY
        affinity_name = getattr(getattr(spell, "affinity", None), "name", str(getattr(spell, "affinity", "MANA"))).lower()
        return getattr(affinities, affinity_name, self.NEUTRAL_AFFINITY)

    def _character_non_item_bonus_power(self, character: Character) -> float:
        bonuses: list[Bonus] = []
        for achievement in getattr(character, "achievements", []) or []:
            bonuses.extend([entry for entry in getattr(achievement, "bonuses", []) if entry is not None])
        for buff in getattr(character, "buffs", []) or []:
            bonus = getattr(buff, "bonus", None)
            if bonus is not None:
                bonuses.append(bonus)
        return self.bonus_power_points(bonuses, character=character)

    def character_power_level(self, character: Character) -> float:
        if hasattr(character, "CalculateBonus"):
            character.CalculateBonus()
        base_attributes = self._sum_attributes(getattr(character, "attributes", None))
        non_item_bonus = self._character_non_item_bonus_power(character)
        gear = getattr(character, "gear", None)
        equipped_items = list(getattr(gear, "GetAllEquipped", lambda: [])()) if gear is not None else []
        equipped_power = sum(self.item_power_level(item) for item in equipped_items if item is not None)
        active_weapon = self._active_weapon(character)
        if active_weapon is not None and all(active_weapon is not item for item in equipped_items):
            equipped_power += self.item_power_level(active_weapon)
        inventory = list(getattr(gear, "inventory", []) or []) if gear is not None else []
        consumable_power = sum(
            sorted(
                [self.item_power_level(item) for item in inventory if isinstance(item, Consumable)],
                reverse=True,
            )[:3]
        ) * 0.5
        spell_power = 0.0
        for spell in getattr(character, "spells", []) or []:
            spell_power += self.spell_power_level(spell, self._character_affinity_value(character, spell))
        return max(0.0, base_attributes + non_item_bonus + equipped_power + consumable_power + spell_power)

    def simulate_spell_power_level(self, spell: Spell, sample_count: int | None = None) -> SimulationSummary:
        heuristic = self.heuristic_spell_power_level(spell)
        count = self._resolve_sample_count(sample_count)
        candidate = self._run_series(count, lambda idx: self._build_spell_scenario(spell=spell, mirrored=False, stat_bonus=0.0, seed_offset=idx))
        reference = self._run_series(count, lambda idx: self._build_spell_scenario(spell=spell, mirrored=True, stat_bonus=1.0, seed_offset=idx))
        return self._finalize_simulation_summary(candidate, reference, heuristic)

    def simulate_item_power_level(self, item: Item, sample_count: int | None = None) -> SimulationSummary:
        heuristic = self.heuristic_item_power_level(item)
        count = self._resolve_sample_count(sample_count)
        if isinstance(item, Weapon):
            candidate = self._run_series(count, lambda idx: self._build_weapon_scenario(item=item, mirrored=False, stat_bonus=0.0, seed_offset=idx))
            reference = self._run_series(count, lambda idx: self._build_weapon_scenario(item=item, mirrored=True, stat_bonus=1.0, seed_offset=idx))
        elif isinstance(item, Armor):
            candidate = self._run_series(count, lambda idx: self._build_armor_scenario(item=item, mirrored=False, stat_bonus=0.0, seed_offset=idx))
            reference = self._run_series(count, lambda idx: self._build_armor_scenario(item=item, mirrored=True, stat_bonus=1.0, seed_offset=idx))
        elif isinstance(item, Consumable):
            candidate = self._run_series(count, lambda idx: self._build_consumable_scenario(item=item, mirrored=False, stat_bonus=0.0, seed_offset=idx))
            reference = self._run_series(count, lambda idx: self._build_consumable_scenario(item=item, mirrored=True, stat_bonus=1.0, seed_offset=idx))
        else:
            candidate = self._run_series(count, lambda idx: self._build_generic_item_scenario(item=item, mirrored=False, stat_bonus=0.0, seed_offset=idx))
            reference = self._run_series(count, lambda idx: self._build_generic_item_scenario(item=item, mirrored=True, stat_bonus=1.0, seed_offset=idx))
        return self._finalize_simulation_summary(candidate, reference, heuristic)

    def recalculate_spellbook_power_levels(self, sample_count: int | None = None):
        if self.spell_service is None:
            raise ValueError("Spell service is not configured.")
        for spell in self.spell_service.list_spells():
            spell.powerLevel = self.simulate_spell_power_level(spell, sample_count=sample_count).recommendedPowerLevel
        self.spell_service.save_spellbook()

    def recalculate_itembook_power_levels(self, sample_count: int | None = None):
        if self.item_service is None:
            raise ValueError("Item service is not configured.")
        for item in self.item_service.list_items():
            item.powerLevel = self.simulate_item_power_level(item, sample_count=sample_count).recommendedPowerLevel
        self.item_service.save_itembook()

    def _resolve_sample_count(self, sample_count: int | None) -> int:
        return max(25, int(sample_count or self.sample_count))

    def _build_attributes(self, stat_bonus: float = 0.0) -> Attributes:
        return Attributes(
            physicalPower=5.0 + stat_bonus,
            physicalStamina=5.0 + stat_bonus,
            physicalResistance=5.0 + stat_bonus,
            magicPower=5.0 + stat_bonus,
            magicStamina=5.0 + stat_bonus,
            magicResistance=5.0 + stat_bonus,
        )

    def _clone_item(self, item: Item | None):
        return copy.deepcopy(item) if item is not None else None

    def _build_character(
        self,
        name: str,
        stat_bonus: float = 0.0,
        primary_weapon: Weapon | None = None,
        offhand: Item | None = None,
        armor: Armor | None = None,
        generic_item: Item | None = None,
        spell: Spell | None = None,
        consumable: Consumable | None = None,
    ) -> Character:
        gear = Gear(inventory=[])
        if primary_weapon is not None:
            if primary_weapon.slot == EquipSlot.OFFHAND:
                gear.offhand = self._clone_item(primary_weapon)
            else:
                gear.primaryWeapon = self._clone_item(primary_weapon)
        if offhand is not None:
            gear.offhand = self._clone_item(offhand)
        if armor is not None:
            self._equip_item_by_slot(gear, self._clone_item(armor))
        if generic_item is not None:
            self._equip_item_by_slot(gear, self._clone_item(generic_item))
        if consumable is not None:
            gear.inventory = [self._clone_item(consumable)]
        spells = [copy.deepcopy(spell)] if spell is not None else []
        character = Character(name=name, attributes=self._build_attributes(stat_bonus), gear=gear, spells=spells)
        character.health = self.SIMULATION_HEALTH
        character.CalculateBonus()
        return character

    @staticmethod
    def _equip_item_by_slot(gear: Gear, item: Item | None):
        if item is None or not item.isEquippable:
            return
        slot_map = {
            EquipSlot.HEAD: "head",
            EquipSlot.NECK: "neck",
            EquipSlot.BODY: "body",
            EquipSlot.HANDS: "hands",
            EquipSlot.RING: "ring",
            EquipSlot.LEGS: "legs",
            EquipSlot.FEET: "feet",
            EquipSlot.PRIMARY_WEAPON: "primaryWeapon",
            EquipSlot.OFFHAND: "offhand",
        }
        attr_name = slot_map.get(item.slot)
        if attr_name:
            setattr(gear, attr_name, item)
    def _build_weapon_scenario(self, item: Weapon, mirrored: bool, stat_bonus: float, seed_offset: int):
        left = self._build_character(name=f"Weapon A {seed_offset}", stat_bonus=stat_bonus, primary_weapon=item)
        right = self._build_character(name=f"Weapon B {seed_offset}", stat_bonus=0.0, primary_weapon=item if mirrored else None)
        return _Combatant(left), _Combatant(right)

    def _build_spell_scenario(self, spell: Spell, mirrored: bool, stat_bonus: float, seed_offset: int):
        left = self._build_character(name=f"Spell A {seed_offset}", stat_bonus=stat_bonus, spell=spell)
        right = self._build_character(name=f"Spell B {seed_offset}", stat_bonus=0.0, spell=spell if mirrored else None)
        return _Combatant(left), _Combatant(right)

    def _build_armor_scenario(self, item: Armor, mirrored: bool, stat_bonus: float, seed_offset: int):
        left = self._build_character(name=f"Armor A {seed_offset}", stat_bonus=stat_bonus, primary_weapon=self._training_weapon(), armor=item)
        right = self._build_character(name=f"Armor B {seed_offset}", stat_bonus=0.0, primary_weapon=self._training_weapon(), armor=item if mirrored else None)
        return _Combatant(left), _Combatant(right)

    def _build_consumable_scenario(self, item: Consumable, mirrored: bool, stat_bonus: float, seed_offset: int):
        left = self._build_character(name=f"Consumable A {seed_offset}", stat_bonus=stat_bonus, primary_weapon=self._training_weapon(), consumable=item)
        right = self._build_character(name=f"Consumable B {seed_offset}", stat_bonus=0.0, primary_weapon=self._training_weapon(), consumable=item if mirrored else None)
        return _Combatant(left, consumable=self._clone_item(item)), _Combatant(right, consumable=self._clone_item(item) if mirrored else None)

    def _build_generic_item_scenario(self, item: Item, mirrored: bool, stat_bonus: float, seed_offset: int):
        left = self._build_character(name=f"Item A {seed_offset}", stat_bonus=stat_bonus, generic_item=item)
        right = self._build_character(name=f"Item B {seed_offset}", stat_bonus=0.0, generic_item=item if mirrored else None)
        return _Combatant(left), _Combatant(right)

    def _run_series(self, sample_count: int, builder) -> dict[str, float]:
        wins = losses = draws = 0
        total_rounds = 0.0
        total_health_a = 0.0
        total_health_b = 0.0
        total_margin = 0.0
        total_performance = 0.0
        for index in range(sample_count):
            left, right = builder(index)
            rng = random.Random(self.seed + (index * 7919))
            rounds = self._run_duel(left, right, rng)
            health_a = max(0.0, float(getattr(left.character, "health", 0.0) or 0.0))
            health_b = max(0.0, float(getattr(right.character, "health", 0.0) or 0.0))
            margin = (health_a - health_b) / self.SIMULATION_HEALTH
            if health_a > 0.0 and health_b <= 0.0:
                wins += 1
                outcome_score = 1.0
            elif health_b > 0.0 and health_a <= 0.0:
                losses += 1
                outcome_score = 0.0
            else:
                draws += 1
                outcome_score = 0.5
            total_rounds += rounds
            total_health_a += health_a
            total_health_b += health_b
            total_margin += margin
            total_performance += outcome_score + (self.PERFORMANCE_MARGIN_WEIGHT * margin)
        average_performance = total_performance / float(sample_count)
        return {
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "winRate": wins / float(sample_count),
            "averageRounds": total_rounds / float(sample_count),
            "averageRemainingHealth": total_health_a / float(sample_count),
            "averageOpponentRemainingHealth": total_health_b / float(sample_count),
            "averageHealthMargin": total_margin / float(sample_count),
            "advantage": average_performance - 0.5,
            "sampleCount": sample_count,
        }

    def _finalize_simulation_summary(self, candidate: dict[str, float], reference: dict[str, float], heuristic: float) -> SimulationSummary:
        reference_advantage = max(0.0, float(reference.get("advantage", 0.0) or 0.0))
        candidate_advantage = max(0.0, float(candidate.get("advantage", 0.0) or 0.0))
        simulated_equivalent = 0.0
        if reference_advantage > 0.00001:
            simulated_equivalent = max(0.0, candidate_advantage / (reference_advantage / 6.0))
            recommended = (self.RECOMMENDED_SIMULATION_WEIGHT * simulated_equivalent) + (self.RECOMMENDED_HEURISTIC_WEIGHT * heuristic)
        else:
            recommended = heuristic
        recommended = max(0.0, round(recommended, 2))
        return SimulationSummary(
            sampleCount=int(candidate.get("sampleCount", 0) or 0),
            wins=int(candidate.get("wins", 0) or 0),
            losses=int(candidate.get("losses", 0) or 0),
            draws=int(candidate.get("draws", 0) or 0),
            winRate=float(candidate.get("winRate", 0.0) or 0.0),
            averageRounds=float(candidate.get("averageRounds", 0.0) or 0.0),
            averageRemainingHealth=float(candidate.get("averageRemainingHealth", 0.0) or 0.0),
            averageOpponentRemainingHealth=float(candidate.get("averageOpponentRemainingHealth", 0.0) or 0.0),
            averageHealthMargin=float(candidate.get("averageHealthMargin", 0.0) or 0.0),
            candidateAdvantage=candidate_advantage,
            referenceAdvantage=reference_advantage,
            simulatedPowerEquivalent=max(0.0, round(simulated_equivalent, 2)),
            recommendedPowerLevel=recommended,
        )

    def _run_duel(self, left: _Combatant, right: _Combatant, rng: random.Random) -> int:
        rounds = 0
        for round_index in range(1, self.MAX_DUEL_ROUNDS + 1):
            rounds = round_index
            if rng.random() < 0.5:
                acting_order = ((left, right), (right, left))
            else:
                acting_order = ((right, left), (left, right))
            for attacker, defender in acting_order:
                if attacker.character.health <= 0 or defender.character.health <= 0:
                    continue
                self._take_turn(attacker, defender, rng, round_index)
                if defender.character.health <= 0:
                    break
            if left.character.health <= 0 or right.character.health <= 0:
                break
        return rounds

    def _take_turn(self, attacker: _Combatant, defender: _Combatant, rng: random.Random, round_index: int):
        if self._try_use_consumable(attacker, defender, rng, round_index):
            return
        character = attacker.character
        weapon = self._active_weapon(character)
        spell = self._best_spell(character)
        adjusted_spell_power = self._adjusted_spell_power(character, spell)
        weapon_ceiling = float(getattr(weapon, "damageMax", getattr(weapon, "damageMin", 0.0)) or 0.0) if weapon is not None else 0.0
        if spell is not None and adjusted_spell_power >= max(weapon_ceiling, 0.1):
            self._resolve_spell_attack(attacker.character, defender.character, spell, rng)
            return
        self._resolve_weapon_attack(attacker.character, defender.character, weapon or self._default_unarmed_weapon(), rng)

    def _try_use_consumable(self, attacker: _Combatant, defender: _Combatant, rng: random.Random, round_index: int) -> bool:
        item = attacker.consumable
        if item is None or attacker.consumable_used:
            return False
        health_ratio = float(attacker.character.health) / max(1.0, self.SIMULATION_HEALTH)
        if item.isOffensive or item.consumableKind == ConsumableKind.BOMB:
            if round_index > 1:
                return False
            damage = self._consumable_damage(attacker.character, item, rng, defender.character)
            defender.character.health = max(0.0, float(defender.character.health) - damage)
            attacker.consumable_used = True
            return True
        if health_ratio <= 0.6:
            healing = self._consumable_healing(attacker.character, item)
            attacker.character.health = min(self.SIMULATION_HEALTH, float(attacker.character.health) + healing)
            attacker.consumable_used = True
            return True
        return False
    def _resolve_weapon_attack(self, attacker: Character, defender: Character, weapon: Weapon, rng: random.Random):
        calculator = DamageCalculator(rng=rng)
        hit, _chance = calculator.roll_hit(
            attacker_stat=float(getattr(attacker.finalAttributes, "physicalPower", 5.0)),
            defender_stat=float(getattr(defender.finalAttributes, "physicalResistance", 5.0)),
        )
        if not hit:
            return
        location = self._roll_hit_location(rng)
        result = calculator.calculate_physical_hit_to_location(
            attacker=attacker,
            defender=defender,
            weapon=weapon,
            location=location,
            applyArmorDamageToGear=True,
        )
        defender.health = max(0.0, float(defender.health) - max(0.0, result.hpFinal))

    def _resolve_spell_attack(self, attacker: Character, defender: Character, spell: Spell, rng: random.Random):
        calculator = DamageCalculator(rng=rng)
        spell_power = self._adjusted_spell_power(attacker, spell)
        breakdown = calculator.calculate_magic_hit(attacker=attacker, defender=defender, spell_power=spell_power)
        defender.health = max(0.0, float(defender.health) - max(0.0, breakdown.hpFinal))

    def _race_lookup(self, race_id: str):
        if self.race_service is None:
            return None
        return self.race_service.get_race(race_id)

    def _active_weapon(self, character: Character) -> Weapon | None:
        return select_active_character_weapon(character, race_lookup=self._race_lookup)

    def _best_spell(self, character: Character) -> Spell | None:
        best_spell = None
        best_power = 0.0
        for spell in getattr(character, "spells", []) or []:
            adjusted = self._adjusted_spell_power(character, spell)
            if adjusted > best_power:
                best_power = adjusted
                best_spell = spell
        return best_spell

    def _adjusted_spell_power(self, character: Character, spell: Spell | None) -> float:
        if spell is None:
            return 0.0
        base_power = max(self.parse_numeric_value(getattr(spell, "power", 0.0), 0.0), self.heuristic_spell_power_level(spell))
        return max(0.0, base_power * self.affinity_multiplier_for_spell(character, spell))

    @staticmethod
    def _roll_hit_location(rng: random.Random) -> HitLocation:
        weights = [
            (HitLocation.HEAD, 0.15),
            (HitLocation.BODY, 0.45),
            (HitLocation.ARMS, 0.20),
            (HitLocation.LEGS, 0.20),
        ]
        roll = rng.random()
        cursor = 0.0
        for location, weight in weights:
            cursor += weight
            if roll <= cursor:
                return location
        return HitLocation.BODY

    def _consumable_damage(self, attacker: Character, item: Consumable, rng: random.Random, defender: Character) -> float:
        if item.spellName and self.spell_service is not None:
            referenced_spell = self.spell_service.get_spell(item.spellName)
            if referenced_spell is not None:
                calculator = DamageCalculator(rng=rng)
                breakdown = calculator.calculate_magic_hit(
                    attacker=attacker,
                    defender=defender,
                    spell_power=self._adjusted_spell_power(attacker, referenced_spell),
                )
                return max(0.0, breakdown.hpFinal)
        calculator = DamageCalculator(rng=rng)
        breakdown = calculator.calculate_magic_hit(
            attacker=attacker,
            defender=defender,
            spell_power=max(0.0, float(getattr(item, "effectPower", 0.0) or 0.0)),
        )
        return max(0.0, breakdown.hpFinal)

    def _consumable_healing(self, attacker: Character, item: Consumable) -> float:
        if item.spellName and self.spell_service is not None:
            referenced_spell = self.spell_service.get_spell(item.spellName)
            if referenced_spell is not None:
                return self._adjusted_spell_power(attacker, referenced_spell)
        base = max(0.0, float(getattr(item, "effectPower", 0.0) or 0.0))
        if item.consumableKind == ConsumableKind.FOOD:
            return base * 0.8
        return base

    def _heuristic_weapon_impact(self, weapon: Weapon) -> float:
        attacker = self._build_character(name="Weapon Rater Attacker", primary_weapon=weapon)
        defender = self._build_character(name="Weapon Rater Defender")
        total = 0.0
        for index in range(40):
            calculator = DamageCalculator(rng=random.Random(self.seed + index + 101))
            result = calculator.calculate_physical_hit(attacker=attacker, defender=defender, weapon=weapon, targetArmor=10.0)
            total += result.hpFinal + (result.armorDamage * 0.35)
        return total / 40.0

    def _heuristic_armor_impact(self, armor: Armor) -> float:
        training_weapon = self._training_weapon()
        prevented = 0.0
        for index in range(30):
            baseline_defender = self._build_character(name="Armor Baseline", primary_weapon=self._training_weapon())
            armored_defender = self._build_character(name="Armor Defender", primary_weapon=self._training_weapon(), armor=armor)
            attacker = self._build_character(name="Armor Attacker", primary_weapon=training_weapon)
            calculator_a = DamageCalculator(rng=random.Random(self.seed + index + 301))
            calculator_b = DamageCalculator(rng=random.Random(self.seed + index + 301))
            location = self._location_for_armor(armor)
            baseline = calculator_a.calculate_physical_hit_to_location(attacker=attacker, defender=baseline_defender, weapon=training_weapon, location=location, applyArmorDamageToGear=True)
            armored = calculator_b.calculate_physical_hit_to_location(attacker=attacker, defender=armored_defender, weapon=training_weapon, location=location, applyArmorDamageToGear=True)
            prevented += max(0.0, baseline.hpFinal - armored.hpFinal) + (baseline.armorDamage - armored.armorDamage) * 0.15
        base = prevented / 30.0
        if armor.slot == EquipSlot.OFFHAND:
            base += max(0.0, float(getattr(armor, "maxArmor", 0.0) or 0.0)) * 0.15
        return base

    def _heuristic_consumable_impact(self, item: Consumable) -> float:
        if item.isOffensive or item.consumableKind == ConsumableKind.BOMB:
            return max(0.0, float(getattr(item, "effectPower", 0.0) or 0.0) * 0.9)
        if item.consumableKind == ConsumableKind.FOOD:
            return max(0.0, float(getattr(item, "effectPower", 0.0) or 0.0) * 0.5)
        return max(0.0, float(getattr(item, "effectPower", 0.0) or 0.0) * 0.7)

    @staticmethod
    def _location_for_armor(armor: Armor) -> HitLocation:
        slot = getattr(armor, "slot", EquipSlot.BODY)
        if slot == EquipSlot.HEAD:
            return HitLocation.HEAD
        if slot in {EquipSlot.HANDS, EquipSlot.OFFHAND}:
            return HitLocation.ARMS
        if slot in {EquipSlot.LEGS, EquipSlot.FEET}:
            return HitLocation.LEGS
        return HitLocation.BODY

    @staticmethod
    def _training_weapon() -> Weapon:
        return Weapon(
            name="Training Blade",
            slot=EquipSlot.PRIMARY_WEAPON,
            tier=0,
            durability=100.0,
            itemType=ItemType.MELEE_WEAPON,
            damageType=[DamageType.SLASHING],
            damageMin=7.0,
            damageMax=9.0,
            armorMultiplier=1.0,
            ignoreArmorFraction=0.0,
            penetrationBase=3.0,
            powerLevel=0.0,
        )

    @staticmethod
    def _default_unarmed_weapon() -> Weapon:
        return Weapon(
            name="Unarmed Strike",
            slot=EquipSlot.PRIMARY_WEAPON,
            tier=0,
            durability=100.0,
            itemType=ItemType.MELEE_WEAPON,
            damageType=[],
            damageMin=4.0,
            damageMax=6.0,
            armorMultiplier=0.7,
            ignoreArmorFraction=0.0,
            penetrationBase=2.0,
            powerLevel=0.0,
        )
