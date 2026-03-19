from __future__ import annotations

import copy
import random
from dataclasses import dataclass

from src.config.tuning import battle_factor, character_stat_factor, misc_factor, misc_factor_int
from src.domain.character import Character
from src.domain.character_util import (
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
from src.domain.items import Armor, Consumable, Gear, Item, Weapon
from src.domain.spells import Spell
from src.domain.combat_timing import (
    CombatRuntimeState,
    accuracy_bonus_for_exertion,
    baseline_turn_seconds,
    can_take_offensive_action,
    damage_multiplier_for_exertion,
    default_offensive_action_stamina_cost,
    defense_stat_penalty_for_exertion,
    schedule_next_action,
    spend_stamina,
    stamina_damage_from_hit,
    sync_stamina,
)
from src.services.combat_duel_shared import (
    build_runtime_state,
    character_max_health,
    character_speed,
    character_stamina_limit,
    character_stamina_regen,
    initialize_duel_timeline,
    max_duel_battle_time,
    parse_numeric_value as shared_parse_numeric_value,
    roll_hit_location,
    round_number_for_time,
    scaled_weapon_for_damage_multiplier,
    select_next_duel_side,
)
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
    runtime: CombatRuntimeState | None = None


class PowerRatingService:
    DEFAULT_SAMPLE_COUNT = 300
    MAX_DUEL_ROUNDS = 30
    SIMULATION_HEALTH = 100.0
    PERFORMANCE_MARGIN_WEIGHT = 0.25
    RECOMMENDED_SIMULATION_WEIGHT = 0.80
    RECOMMENDED_HEURISTIC_WEIGHT = 0.20
    NEUTRAL_AFFINITY = 0.5

    def __init__(
        self,
        spell_service=None,
        item_service=None,
        race_service=None,
        sample_count: int = DEFAULT_SAMPLE_COUNT,
        seed: int = 1337,
    ):
        self.spell_service = spell_service
        self.item_service = item_service
        self.race_service = race_service
        self.sample_count = max(25, int(sample_count or self.DEFAULT_SAMPLE_COUNT))
        self.seed = int(seed)

    @classmethod
    def parse_numeric_value(cls, value, default: float = 0.0) -> float:
        return shared_parse_numeric_value(value, default=default, allow_dice_average=True)

    @classmethod
    def normalize_affinity_fraction(cls, value) -> float:
        numeric = cls.parse_numeric_value(value, misc_factor("neutral_affinity", cls.NEUTRAL_AFFINITY))
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
        return misc_factor("affinity_power_min_multiplier", 0.8) + (
            fraction * misc_factor("affinity_power_bonus_range", 0.4)
        )

    def affinity_multiplier_for_spell(self, character: Character | None, spell: Spell | None) -> float:
        if character is None or spell is None:
            return 1.0
        if hasattr(character, "CalculateBonus"):
            character.CalculateBonus()
        affinities = getattr(character, "finalAffinities", None) or getattr(character, "affinities", None)
        if affinities is None:
            return 1.0
        affinity_name = getattr(
            getattr(spell, "affinity", None), "name", str(getattr(spell, "affinity", "MANA"))
        ).upper()
        return self.affinity_power_multiplier(
            getattr(affinities, affinity_name.lower(), misc_factor("neutral_affinity", self.NEUTRAL_AFFINITY))
        )

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
            return character_stat_factor("primary_stat_baseline", 5.0)
        attributes = getattr(character, "attributes", None)
        mapping = {
            Attribute.PHYSICAL_POWER: float(
                getattr(attributes, "physicalPower", character_stat_factor("primary_stat_baseline", 5.0))
            ),
            Attribute.PHYSICAL_STAMINA: float(
                getattr(attributes, "physicalStamina", character_stat_factor("primary_stat_baseline", 5.0))
            ),
            Attribute.PHYSICAL_RESISTANCE: float(
                getattr(attributes, "physicalResistance", character_stat_factor("primary_stat_baseline", 5.0))
            ),
            Attribute.MAGIC_POWER: float(
                getattr(attributes, "magicPower", character_stat_factor("primary_stat_baseline", 5.0))
            ),
            Attribute.MAGIC_STAMINA: float(
                getattr(attributes, "magicStamina", character_stat_factor("primary_stat_baseline", 5.0))
            ),
            Attribute.MAGIC_RESISTANCE: float(
                getattr(attributes, "magicResistance", character_stat_factor("primary_stat_baseline", 5.0))
            ),
        }
        return mapping.get(attribute, character_stat_factor("primary_stat_baseline", 5.0))

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
                total += (
                    amount * misc_factor("all_attributes_flat_bonus_weight", 6.0)
                    if attribute == Attribute.ALL_ATTRIBUTES
                    else amount
                )
            else:
                if attribute == Attribute.ALL_ATTRIBUTES:
                    total += self._sum_attributes(getattr(character, "attributes", None) or Attributes()) * (
                        amount / 100.0
                    )
                else:
                    total += self._attribute_baseline(character, attribute) * (amount / 100.0)
        return total

    def heuristic_spell_power_level(self, spell: Spell) -> float:
        base_power = self.parse_numeric_value(getattr(spell, "power", 0.0), 0.0)
        level_bonus = max(0.0, float(getattr(spell, "level", 0) or 0)) * misc_factor(
            "spell_heuristic_level_bonus_per_level", 0.5
        )
        range_bonus = min(
            misc_factor("spell_heuristic_range_cap", 25.0), self.parse_numeric_value(getattr(spell, "range", 0.0), 0.0)
        ) * misc_factor("spell_heuristic_range_bonus_per_unit", 0.03)
        duration_bonus = min(
            misc_factor("spell_heuristic_duration_cap", 12.0),
            self.parse_numeric_value(getattr(spell, "duration", 0.0), 0.0),
        ) * misc_factor("spell_heuristic_duration_bonus_per_unit", 0.05)
        casting_penalty = min(
            misc_factor("spell_heuristic_casting_penalty_cap", 0.5),
            self.parse_numeric_value(getattr(spell, "casting_time", 0.0), 0.0)
            * misc_factor("spell_heuristic_casting_penalty_per_unit", 0.03),
        )
        components = getattr(spell, "components", {}) if isinstance(getattr(spell, "components", {}), dict) else {}
        component_bonus = misc_factor("spell_heuristic_component_bonus_per_component", 0.1) * sum(
            1 for key in ("verbal", "somatic", "material") if components.get(key)
        )
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
            return misc_factor("neutral_affinity", self.NEUTRAL_AFFINITY)
        affinity_name = getattr(
            getattr(spell, "affinity", None), "name", str(getattr(spell, "affinity", "MANA"))
        ).lower()
        return getattr(affinities, affinity_name, misc_factor("neutral_affinity", self.NEUTRAL_AFFINITY))

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
            )[: max(0, misc_factor_int("inventory_consumable_slots_considered", 3))]
        ) * misc_factor("inventory_consumable_power_weight", 0.5)
        spell_power = 0.0
        for spell in getattr(character, "spells", []) or []:
            spell_power += self.spell_power_level(spell, self._character_affinity_value(character, spell))
        return max(0.0, base_attributes + non_item_bonus + equipped_power + consumable_power + spell_power)

    def simulate_spell_power_level(self, spell: Spell, sample_count: int | None = None) -> SimulationSummary:
        heuristic = self.heuristic_spell_power_level(spell)
        count = self._resolve_sample_count(sample_count)
        candidate = self._run_series(
            count, lambda idx: self._build_spell_scenario(spell=spell, mirrored=False, stat_bonus=0.0, seed_offset=idx)
        )
        reference = self._run_series(
            count, lambda idx: self._build_spell_scenario(spell=spell, mirrored=True, stat_bonus=1.0, seed_offset=idx)
        )
        return self._finalize_simulation_summary(candidate, reference, heuristic)

    def simulate_item_power_level(self, item: Item, sample_count: int | None = None) -> SimulationSummary:
        heuristic = self.heuristic_item_power_level(item)
        count = self._resolve_sample_count(sample_count)
        if isinstance(item, Weapon):
            candidate = self._run_series(
                count,
                lambda idx: self._build_weapon_scenario(item=item, mirrored=False, stat_bonus=0.0, seed_offset=idx),
            )
            reference = self._run_series(
                count,
                lambda idx: self._build_weapon_scenario(item=item, mirrored=True, stat_bonus=1.0, seed_offset=idx),
            )
        elif isinstance(item, Armor):
            candidate = self._run_series(
                count,
                lambda idx: self._build_armor_scenario(item=item, mirrored=False, stat_bonus=0.0, seed_offset=idx),
            )
            reference = self._run_series(
                count, lambda idx: self._build_armor_scenario(item=item, mirrored=True, stat_bonus=1.0, seed_offset=idx)
            )
        elif isinstance(item, Consumable):
            candidate = self._run_series(
                count,
                lambda idx: self._build_consumable_scenario(item=item, mirrored=False, stat_bonus=0.0, seed_offset=idx),
            )
            reference = self._run_series(
                count,
                lambda idx: self._build_consumable_scenario(item=item, mirrored=True, stat_bonus=1.0, seed_offset=idx),
            )
        else:
            candidate = self._run_series(
                count,
                lambda idx: self._build_generic_item_scenario(
                    item=item, mirrored=False, stat_bonus=0.0, seed_offset=idx
                ),
            )
            reference = self._run_series(
                count,
                lambda idx: self._build_generic_item_scenario(
                    item=item, mirrored=True, stat_bonus=1.0, seed_offset=idx
                ),
            )
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
        baseline = character_stat_factor("primary_stat_baseline", 5.0)
        return Attributes(
            physicalPower=baseline + stat_bonus,
            physicalStamina=baseline + stat_bonus,
            physicalResistance=baseline + stat_bonus,
            magicPower=baseline + stat_bonus,
            magicStamina=baseline + stat_bonus,
            magicResistance=baseline + stat_bonus,
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
        character.CalculateBonus()
        character.health = character.GetMaxHealth()
        character.RefreshHealthState()
        return character

    @staticmethod
    def _character_max_health(character: Character) -> float:
        return character_max_health(character)

    @staticmethod
    def _character_speed(character: Character) -> float:
        return character_speed(character)

    @classmethod
    def _action_interval(cls, character: Character) -> float:
        return baseline_turn_seconds() / cls._character_speed(character)

    @staticmethod
    def _character_stamina_limit(character: Character) -> float:
        return character_stamina_limit(character)

    @staticmethod
    def _character_stamina_regen(character: Character) -> float:
        return character_stamina_regen(character)

    def _build_runtime_state(self, character: Character) -> CombatRuntimeState:
        return build_runtime_state(character)

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
        right = self._build_character(
            name=f"Weapon B {seed_offset}", stat_bonus=0.0, primary_weapon=item if mirrored else None
        )
        return _Combatant(left, runtime=self._build_runtime_state(left)), _Combatant(
            right, runtime=self._build_runtime_state(right)
        )

    def _build_spell_scenario(self, spell: Spell, mirrored: bool, stat_bonus: float, seed_offset: int):
        left = self._build_character(name=f"Spell A {seed_offset}", stat_bonus=stat_bonus, spell=spell)
        right = self._build_character(name=f"Spell B {seed_offset}", stat_bonus=0.0, spell=spell if mirrored else None)
        return _Combatant(left, runtime=self._build_runtime_state(left)), _Combatant(
            right, runtime=self._build_runtime_state(right)
        )

    def _build_armor_scenario(self, item: Armor, mirrored: bool, stat_bonus: float, seed_offset: int):
        left = self._build_character(
            name=f"Armor A {seed_offset}", stat_bonus=stat_bonus, primary_weapon=self._training_weapon(), armor=item
        )
        right = self._build_character(
            name=f"Armor B {seed_offset}",
            stat_bonus=0.0,
            primary_weapon=self._training_weapon(),
            armor=item if mirrored else None,
        )
        return _Combatant(left, runtime=self._build_runtime_state(left)), _Combatant(
            right, runtime=self._build_runtime_state(right)
        )

    def _build_consumable_scenario(self, item: Consumable, mirrored: bool, stat_bonus: float, seed_offset: int):
        left = self._build_character(
            name=f"Consumable A {seed_offset}",
            stat_bonus=stat_bonus,
            primary_weapon=self._training_weapon(),
            consumable=item,
        )
        right = self._build_character(
            name=f"Consumable B {seed_offset}",
            stat_bonus=0.0,
            primary_weapon=self._training_weapon(),
            consumable=item if mirrored else None,
        )
        return (
            _Combatant(left, consumable=self._clone_item(item), runtime=self._build_runtime_state(left)),
            _Combatant(
                right, consumable=self._clone_item(item) if mirrored else None, runtime=self._build_runtime_state(right)
            ),
        )

    def _build_generic_item_scenario(self, item: Item, mirrored: bool, stat_bonus: float, seed_offset: int):
        left = self._build_character(name=f"Item A {seed_offset}", stat_bonus=stat_bonus, generic_item=item)
        right = self._build_character(
            name=f"Item B {seed_offset}", stat_bonus=0.0, generic_item=item if mirrored else None
        )
        return _Combatant(left, runtime=self._build_runtime_state(left)), _Combatant(
            right, runtime=self._build_runtime_state(right)
        )

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
            margin_scale = max(
                1.0,
                (self._character_max_health(left.character) + self._character_max_health(right.character)) / 2.0,
            )
            margin = (health_a - health_b) / margin_scale
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
            total_performance += outcome_score + (
                misc_factor("performance_margin_weight", self.PERFORMANCE_MARGIN_WEIGHT) * margin
            )
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

    def _finalize_simulation_summary(
        self, candidate: dict[str, float], reference: dict[str, float], heuristic: float
    ) -> SimulationSummary:
        reference_advantage = max(0.0, float(reference.get("advantage", 0.0) or 0.0))
        candidate_advantage = max(0.0, float(candidate.get("advantage", 0.0) or 0.0))
        simulated_equivalent = 0.0
        if reference_advantage > 0.00001:
            simulated_equivalent = max(
                0.0, candidate_advantage / (reference_advantage / misc_factor("simulated_power_reference_bonus", 6.0))
            )
            recommended = (
                misc_factor("recommended_simulation_weight", self.RECOMMENDED_SIMULATION_WEIGHT) * simulated_equivalent
            ) + (misc_factor("recommended_heuristic_weight", self.RECOMMENDED_HEURISTIC_WEIGHT) * heuristic)
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
        timeline = initialize_duel_timeline(rng)
        left.runtime = left.runtime or self._build_runtime_state(left.character)
        right.runtime = right.runtime or self._build_runtime_state(right.character)
        left.runtime.next_action_time = float(timeline.next_action_times.get("left", timeline.turn_gap))
        right.runtime.next_action_time = float(timeline.next_action_times.get("right", timeline.turn_gap))
        next_action_times = dict(timeline.next_action_times)
        tie_break_order = list(timeline.tie_break_order)
        rounds = 1

        while rounds <= self.MAX_DUEL_ROUNDS:
            alive_sides = []
            if left.character.health > 0:
                alive_sides.append("left")
            if right.character.health > 0:
                alive_sides.append("right")
            if len(alive_sides) < 2:
                break

            side = select_next_duel_side(alive_sides, next_action_times, tie_break_order)
            if side is None:
                break
            turn_start_time = float(next_action_times.get(side, 0.0))
            if turn_start_time > max_duel_battle_time(self.MAX_DUEL_ROUNDS):
                break
            attacker, defender = (left, right) if side == "left" else (right, left)
            sync_stamina(attacker.runtime, turn_start_time)
            sync_stamina(defender.runtime, turn_start_time)
            rounds = max(rounds, round_number_for_time(turn_start_time))
            self._take_turn(attacker, defender, rng, rounds, turn_start_time)
            next_action_times[side] = schedule_next_action(
                attacker.runtime, self._character_speed(attacker.character), turn_start_time
            )
            tie_break_order = [entry for entry in tie_break_order if entry != side] + [side]
            if defender.character.health <= 0:
                break
        return rounds

    def _take_turn(
        self, attacker: _Combatant, defender: _Combatant, rng: random.Random, round_index: int, turn_start_time: float
    ):
        if not can_take_offensive_action(attacker.runtime.exertion_level):
            return
        if self._try_use_consumable(attacker, defender, rng, round_index, turn_start_time):
            return
        character = attacker.character
        weapon = self._active_weapon(character)
        spell = self._best_spell(character)
        adjusted_spell_power = self._adjusted_spell_power(character, spell)
        weapon_ceiling = (
            float(getattr(weapon, "damageMax", getattr(weapon, "damageMin", 0.0)) or 0.0) if weapon is not None else 0.0
        )
        if spell is not None and adjusted_spell_power >= max(weapon_ceiling, 0.1):
            self._resolve_spell_attack(attacker, defender, spell, rng, turn_start_time)
            return
        self._resolve_weapon_attack(attacker, defender, weapon or self._default_unarmed_weapon(), rng, turn_start_time)

    def _try_use_consumable(
        self, attacker: _Combatant, defender: _Combatant, rng: random.Random, round_index: int, turn_start_time: float
    ) -> bool:
        item = attacker.consumable
        if item is None or attacker.consumable_used:
            return False
        health_ratio = float(attacker.character.health) / self._character_max_health(attacker.character)
        if item.isOffensive or item.consumableKind == ConsumableKind.BOMB:
            if round_index > battle_factor("combat_sim_offensive_consumable_round_limit", 1):
                return False
            damage = self._consumable_damage(attacker, item, rng, defender, turn_start_time)
            defender.character.health = max(0.0, float(defender.character.health) - damage)
            if damage > 0.0:
                spend_stamina(defender.runtime, stamina_damage_from_hit(damage), turn_start_time)
            spend_stamina(attacker.runtime, default_offensive_action_stamina_cost(), turn_start_time)
            attacker.consumable_used = True
            return True
        if health_ratio <= battle_factor("combat_sim_supportive_consumable_health_ratio_threshold", 0.6):
            healing = self._consumable_healing(attacker.character, item)
            attacker.character.health = min(
                self._character_max_health(attacker.character), float(attacker.character.health) + healing
            )
            attacker.consumable_used = True
            return True
        return False

    def _resolve_weapon_attack(
        self, attacker: _Combatant, defender: _Combatant, weapon: Weapon, rng: random.Random, turn_start_time: float
    ):
        calculator = DamageCalculator(rng=rng)
        hit, _chance = calculator.roll_hit(
            attacker_stat=float(getattr(attacker.character.finalAttributes, "physicalPower", 5.0)),
            defender_stat=max(
                0.0,
                float(getattr(defender.character.finalAttributes, "physicalResistance", 5.0))
                - defense_stat_penalty_for_exertion(defender.runtime.exertion_level),
            ),
            bonus=accuracy_bonus_for_exertion(attacker.runtime.exertion_level),
        )
        spend_stamina(
            attacker.runtime,
            max(
                0.0,
                float(
                    getattr(weapon, "staminaCost", default_offensive_action_stamina_cost())
                    or default_offensive_action_stamina_cost()
                ),
            ),
            turn_start_time,
        )
        if not hit:
            return
        location = self._roll_hit_location(rng)
        scaled_weapon = self._scaled_weapon_for_damage_multiplier(
            weapon,
            damage_multiplier_for_exertion(attacker.runtime.exertion_level),
        )
        result = calculator.calculate_physical_hit_to_location(
            attacker=attacker.character,
            defender=defender.character,
            weapon=scaled_weapon,
            location=location,
            applyArmorDamageToGear=True,
        )
        damage = max(0.0, result.hpFinal)
        defender.character.health = max(0.0, float(defender.character.health) - damage)
        if damage > 0.0:
            spend_stamina(defender.runtime, stamina_damage_from_hit(damage), turn_start_time)

    def _resolve_spell_attack(
        self, attacker: _Combatant, defender: _Combatant, spell: Spell, rng: random.Random, turn_start_time: float
    ):
        calculator = DamageCalculator(rng=rng)
        spell_power = self._adjusted_spell_power(attacker.character, spell) * damage_multiplier_for_exertion(
            attacker.runtime.exertion_level
        )
        breakdown = calculator.calculate_magic_hit(
            attacker=attacker.character,
            defender=defender.character,
            spell_power=spell_power,
            hit_chance=calculator.calculate_hit_chance(
                float(getattr(attacker.character.finalAttributes, "magicPower", 5.0)),
                max(
                    0.0,
                    float(getattr(defender.character.finalAttributes, "magicResistance", 5.0))
                    - defense_stat_penalty_for_exertion(defender.runtime.exertion_level),
                ),
                bonus=accuracy_bonus_for_exertion(attacker.runtime.exertion_level),
            ),
        )
        spend_stamina(attacker.runtime, default_offensive_action_stamina_cost(), turn_start_time)
        damage = max(0.0, breakdown.hpFinal)
        defender.character.health = max(0.0, float(defender.character.health) - damage)
        if damage > 0.0:
            spend_stamina(defender.runtime, stamina_damage_from_hit(damage), turn_start_time)

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
        base_power = max(
            self.parse_numeric_value(getattr(spell, "power", 0.0), 0.0), self.heuristic_spell_power_level(spell)
        )
        return max(0.0, base_power * self.affinity_multiplier_for_spell(character, spell))

    @staticmethod
    def _roll_hit_location(rng: random.Random) -> HitLocation:
        return roll_hit_location(rng)

    @staticmethod
    def _scaled_weapon_for_damage_multiplier(weapon: Weapon, damage_multiplier: float) -> Weapon:
        return scaled_weapon_for_damage_multiplier(weapon, damage_multiplier)

    def _consumable_damage(
        self, attacker: _Combatant, item: Consumable, rng: random.Random, defender: _Combatant, turn_start_time: float
    ) -> float:
        if item.spellName and self.spell_service is not None:
            referenced_spell = self.spell_service.get_spell(item.spellName)
            if referenced_spell is not None:
                calculator = DamageCalculator(rng=rng)
                breakdown = calculator.calculate_magic_hit(
                    attacker=attacker.character,
                    defender=defender.character,
                    spell_power=self._adjusted_spell_power(attacker.character, referenced_spell)
                    * damage_multiplier_for_exertion(attacker.runtime.exertion_level),
                    hit_chance=calculator.calculate_hit_chance(
                        float(getattr(attacker.character.finalAttributes, "magicPower", 5.0)),
                        max(
                            0.0,
                            float(getattr(defender.character.finalAttributes, "magicResistance", 5.0))
                            - defense_stat_penalty_for_exertion(defender.runtime.exertion_level),
                        ),
                        bonus=accuracy_bonus_for_exertion(attacker.runtime.exertion_level),
                    ),
                )
                return max(0.0, breakdown.hpFinal)
        calculator = DamageCalculator(rng=rng)
        breakdown = calculator.calculate_magic_hit(
            attacker=attacker.character,
            defender=defender.character,
            spell_power=max(0.0, float(getattr(item, "effectPower", 0.0) or 0.0))
            * damage_multiplier_for_exertion(attacker.runtime.exertion_level),
            hit_chance=calculator.calculate_hit_chance(
                float(getattr(attacker.character.finalAttributes, "magicPower", 5.0)),
                max(
                    0.0,
                    float(getattr(defender.character.finalAttributes, "magicResistance", 5.0))
                    - defense_stat_penalty_for_exertion(defender.runtime.exertion_level),
                ),
                bonus=accuracy_bonus_for_exertion(attacker.runtime.exertion_level),
            ),
        )
        return max(0.0, breakdown.hpFinal)

    def _consumable_healing(self, attacker: Character, item: Consumable) -> float:
        if item.spellName and self.spell_service is not None:
            referenced_spell = self.spell_service.get_spell(item.spellName)
            if referenced_spell is not None:
                return self._adjusted_spell_power(attacker, referenced_spell)
        base = max(0.0, float(getattr(item, "effectPower", 0.0) or 0.0))
        if item.consumableKind == ConsumableKind.FOOD:
            return base * battle_factor("food_healing_multiplier", 0.8)
        return base

    def _heuristic_weapon_impact(self, weapon: Weapon) -> float:
        attacker = self._build_character(name="Weapon Rater Attacker", primary_weapon=weapon)
        defender = self._build_character(name="Weapon Rater Defender")
        total = 0.0
        sample_count = max(1, misc_factor_int("weapon_heuristic_sample_count", 40))
        for index in range(sample_count):
            calculator = DamageCalculator(rng=random.Random(self.seed + index + 101))
            result = calculator.calculate_physical_hit(
                attacker=attacker,
                defender=defender,
                weapon=weapon,
                targetArmor=misc_factor("weapon_heuristic_target_armor", 10.0),
            )
            total += result.hpFinal + (result.armorDamage * misc_factor("weapon_heuristic_armor_damage_weight", 0.35))
        return total / float(sample_count)

    def _heuristic_armor_impact(self, armor: Armor) -> float:
        training_weapon = self._training_weapon()
        prevented = 0.0
        sample_count = max(1, misc_factor_int("armor_heuristic_sample_count", 30))
        for index in range(sample_count):
            baseline_defender = self._build_character(name="Armor Baseline", primary_weapon=self._training_weapon())
            armored_defender = self._build_character(
                name="Armor Defender", primary_weapon=self._training_weapon(), armor=armor
            )
            attacker = self._build_character(name="Armor Attacker", primary_weapon=training_weapon)
            calculator_a = DamageCalculator(rng=random.Random(self.seed + index + 301))
            calculator_b = DamageCalculator(rng=random.Random(self.seed + index + 301))
            location = self._location_for_armor(armor)
            baseline = calculator_a.calculate_physical_hit_to_location(
                attacker=attacker,
                defender=baseline_defender,
                weapon=training_weapon,
                location=location,
                applyArmorDamageToGear=True,
            )
            armored = calculator_b.calculate_physical_hit_to_location(
                attacker=attacker,
                defender=armored_defender,
                weapon=training_weapon,
                location=location,
                applyArmorDamageToGear=True,
            )
            prevented += max(0.0, baseline.hpFinal - armored.hpFinal) + (
                baseline.armorDamage - armored.armorDamage
            ) * misc_factor("armor_heuristic_damage_prevent_weight", 0.15)
        base = prevented / float(sample_count)
        if armor.slot == EquipSlot.OFFHAND:
            base += max(0.0, float(getattr(armor, "maxArmor", 0.0) or 0.0)) * misc_factor(
                "armor_heuristic_offhand_max_armor_weight", 0.15
            )
        return base

    def _heuristic_consumable_impact(self, item: Consumable) -> float:
        if item.isOffensive or item.consumableKind == ConsumableKind.BOMB:
            return max(
                0.0,
                float(getattr(item, "effectPower", 0.0) or 0.0)
                * misc_factor("offensive_consumable_impact_multiplier", 0.9),
            )
        if item.consumableKind == ConsumableKind.FOOD:
            return max(
                0.0,
                float(getattr(item, "effectPower", 0.0) or 0.0) * misc_factor("food_consumable_impact_multiplier", 0.5),
            )
        return max(
            0.0,
            float(getattr(item, "effectPower", 0.0) or 0.0) * misc_factor("default_consumable_impact_multiplier", 0.7),
        )

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
            staminaCost=default_offensive_action_stamina_cost(),
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
            staminaCost=default_offensive_action_stamina_cost(),
            powerLevel=0.0,
        )
