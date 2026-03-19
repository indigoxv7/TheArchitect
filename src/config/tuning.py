from __future__ import annotations

import copy
import os
import threading
from typing import Any

from src.persistence.tuning_store import TuningStore


BATTLE_FACTORS_CATEGORY = "battle_factors"
CHARACTER_STAT_FACTORS_CATEGORY = "character_stat_factors"
FACTION_STAT_FACTORS_CATEGORY = "faction_stat_factors"
MISC_CATEGORY = "misc"


def _field(key: str, label: str, default, description: str, value_type: str = "float") -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "default": default,
        "description": description,
        "type": value_type,
    }


TUNING_SCHEMA: dict[str, dict[str, Any]] = {
    BATTLE_FACTORS_CATEGORY: {
        "title": "Battle Factors",
        "description": "Live combat timing, accuracy, damage, stamina, and battle-flow tuning values.",
        "filename": "battle_factors.json",
        "fields": [
            _field("base_hit_chance", "Base Hit Chance", 0.65, "Starting hit chance before stat deltas and situational modifiers."),
            _field("stat_delta_hit_scale", "Stat Delta Hit Scale", 0.03, "Hit chance added or removed for each point between attacker and defender stats."),
            _field("min_hit_chance", "Min Hit Chance", 0.35, "Lower clamp on hit chance."),
            _field("max_hit_chance", "Max Hit Chance", 0.90, "Upper clamp on hit chance."),
            _field("penetration_power_scale", "Penetration Power Scale", 0.50, "Extra penetration gained per point of physical power above baseline."),
            _field("resistance_deficit_floor", "Resistance Deficit Floor", 5.0, "Minimum penetration shortfall window before physical damage fully falls off."),
            _field("resistance_deficit_scale", "Resistance Deficit Scale", 0.20, "Resistance-based scaling for the penetration shortfall window."),
            _field("resistance_falloff_sharpness", "Resistance Falloff Sharpness", 5.0, "Exponential sharpness for penetration falling below resistance."),
            _field("armor_soak_coeff", "Armor Soak Coefficient", 0.10, "Residual armor soak applied to HP damage that bypasses armor."),
            _field("magic_resistance_min_multiplier", "Magic Resistance Min Mult", 0.05, "Minimum damage multiplier after magic resistance."),
            _field("magic_resistance_softness", "Magic Resistance Softness", 12.0, "Softness constant for magic resistance reduction."),
            _field("baseline_turn_seconds", "Baseline Turn Seconds", 6.0, "Battle-time seconds between turns for a baseline-speed actor."),
            _field("exchange_duration_seconds", "Exchange Duration Seconds", 12.0, "Battle-time seconds simulated in one mission battle exchange."),
            _field("hours_per_exchange", "Hours Per Exchange", 0.25, "Mission-time hours consumed by one battle exchange."),
            _field("default_offensive_action_stamina_cost", "Default Offensive Stamina Cost", 10.0, "Fallback stamina cost for offensive actions without a weapon-specific cost."),
            _field("hit_stamina_damage_base", "Hit Stamina Drain Base", 5.0, "Base stamina loss from taking a hit."),
            _field("hit_stamina_damage_scale", "Hit Stamina Drain Scale", 0.20, "Extra stamina loss from taking damage."),
            _field("hit_stamina_damage_cap", "Hit Stamina Drain Cap", 5.0, "Cap on the damage-scaled portion of hit stamina loss."),
            _field("overcharged_damage_multiplier", "Overcharged Damage Mult", 1.10, "Damage multiplier while overcharged."),
            _field("tired_damage_multiplier", "Tired Damage Mult", 0.85, "Damage multiplier while tired."),
            _field("overcharged_accuracy_bonus", "Overcharged Accuracy Bonus", 0.05, "Accuracy bonus while overcharged."),
            _field("tired_accuracy_bonus", "Tired Accuracy Bonus", -0.05, "Accuracy penalty while tired."),
            _field("overcharged_speed_multiplier", "Overcharged Speed Mult", 1.10, "Speed multiplier while overcharged."),
            _field("fresh_speed_multiplier", "Fresh Speed Mult", 1.00, "Speed multiplier while fresh."),
            _field("tired_speed_multiplier", "Tired Speed Mult", 0.80, "Speed multiplier while tired."),
            _field("exhausted_speed_multiplier", "Exhausted Speed Mult", 0.50, "Speed multiplier while exhausted."),
            _field("exhausted_defense_stat_penalty", "Exhausted Defense Penalty", 3.0, "Defense stat penalty applied to exhausted defenders."),
            _field("stance_advance_attack_bonus", "Advance Attack Bonus", 0.03, "Attack bonus from the Advance stance."),
            _field("stance_aggressive_attack_bonus", "Aggressive Attack Bonus", 0.05, "Attack bonus from the Aggressive stance."),
            _field("stance_defensive_attack_bonus", "Defensive Attack Bonus", -0.03, "Attack penalty from the Defensive stance."),
            _field("ranged_congestion_penalty", "Ranged Congestion Penalty", 0.05, "Penalty applied to wide attackers firing through their occupied lane."),
            _field("ranged_range_penalty_per_line", "Range Penalty Per Line", 0.05, "Penalty per extra line of distance for ranged attacks."),
            _field("ranged_firing_through_engagement_penalty", "Firing Through Engagement Penalty", 0.10, "Penalty for ranged units firing through an engaged frontline."),
            _field("front_line_attack_count_weight", "Front Line Attack Count Weight", 0.10, "Extra front-line strength weight per attack profile."),
            _field("line_progress_advantage_multiplier", "Line Progress Advantage Mult", 1.25, "Front-line strength advantage needed to push the opposing line."),
            _field("defensive_line_hold_multiplier", "Defensive Line Hold Mult", 1.40, "Extra enemy advantage needed to push a Defensive line."),
            _field("recentering_threshold_base", "Recentering Threshold Base", 3, "Base pressure threshold before lines snap back toward center.", value_type="int"),
            _field("retreat_opportunity_health_ratio_threshold", "Retreat Opportunity HP Ratio", 0.35, "Allied team health ratio threshold for surfacing retreat opportunities."),
            _field("strategy_low_score_max", "Strategy Low Score Max", 3, "Highest strategy score treated as poor.", value_type="int"),
            _field("strategy_mid_score_max", "Strategy Mid Score Max", 6, "Highest strategy score treated as average.", value_type="int"),
            _field("strategy_high_score_max", "Strategy High Score Max", 8, "Highest strategy score treated as strong.", value_type="int"),
            _field("strategy_low_lane_discipline_modifier", "Poor Strategy Lane Discipline", -0.05, "Lane discipline modifier for poor strategy scores."),
            _field("strategy_low_resource_efficiency_modifier", "Poor Strategy Resource Efficiency", -0.10, "Resource efficiency modifier for poor strategy scores."),
            _field("strategy_mid_lane_discipline_modifier", "Average Strategy Lane Discipline", 0.0, "Lane discipline modifier for average strategy scores."),
            _field("strategy_mid_resource_efficiency_modifier", "Average Strategy Resource Efficiency", 0.0, "Resource efficiency modifier for average strategy scores."),
            _field("strategy_high_lane_discipline_modifier", "Strong Strategy Lane Discipline", 0.05, "Lane discipline modifier for strong strategy scores."),
            _field("strategy_high_resource_efficiency_modifier", "Strong Strategy Resource Efficiency", 0.05, "Resource efficiency modifier for strong strategy scores."),
            _field("strategy_top_lane_discipline_modifier", "Elite Strategy Lane Discipline", 0.10, "Lane discipline modifier for elite strategy scores."),
            _field("strategy_top_resource_efficiency_modifier", "Elite Strategy Resource Efficiency", 0.10, "Resource efficiency modifier for elite strategy scores."),
            _field("strategy_top_width_control_bonus", "Elite Strategy Width Bonus", 1, "Width control bonus for elite strategy scores.", value_type="int"),
            _field("minimum_resource_efficiency_multiplier", "Min Resource Efficiency Mult", 0.50, "Lower clamp on healing/resource efficiency after strategy modifiers."),
            _field("combat_sim_head_hit_weight", "Head Hit Weight", 0.15, "Combat simulator weight for head hit selection."),
            _field("combat_sim_body_hit_weight", "Body Hit Weight", 0.45, "Combat simulator weight for body hit selection."),
            _field("combat_sim_arms_hit_weight", "Arms Hit Weight", 0.20, "Combat simulator weight for arms hit selection."),
            _field("combat_sim_legs_hit_weight", "Legs Hit Weight", 0.20, "Combat simulator weight for legs hit selection."),
            _field("combat_sim_offensive_consumable_round_limit", "Offensive Consumable Round Limit", 1, "Latest round where the simulator will freely prefer offensive consumables.", value_type="int"),
            _field("combat_sim_supportive_consumable_health_ratio_threshold", "Supportive Consumable HP Ratio", 0.60, "Health ratio below which the simulator prefers a supportive consumable."),
            _field("food_healing_multiplier", "Food Healing Multiplier", 0.80, "Healing multiplier applied to food-based recovery effects in combat calculations."),
        ],
    },
    CHARACTER_STAT_FACTORS_CATEGORY: {
        "title": "Character Stat Factors",
        "description": "Derived stat scaling values for health, speed, stamina, and health-state thresholds.",
        "filename": "character_stat_factors.json",
        "fields": [
            _field("primary_stat_baseline", "Primary Stat Baseline", 5.0, "Baseline primary-stat value used by derived stat scaling formulas."),
            _field("derived_stat_alpha", "Derived Stat Alpha", 0.80, "Shared exponent for primary-stat-derived scaling curves."),
            _field("base_health_at_baseline", "Base Health At Baseline", 55.0, "Max health for a baseline resistance character."),
            _field("speed_physical_power_weight", "Speed Physical Weight", 2.0, "Weight of physical power in speed calculations."),
            _field("speed_magic_power_weight", "Speed Magic Weight", 1.0, "Weight of magic power in speed calculations."),
            _field("speed_normalization_divisor", "Speed Normalization Divisor", 15.0, "Divisor that normalizes weighted power into a speed factor."),
            _field("minimum_speed_factor", "Minimum Speed Factor", 0.10, "Lower clamp on derived speed."),
            _field("baseline_stamina_limit", "Baseline Stamina Limit", 75.0, "Stamina pool size at baseline physical stamina."),
            _field("stamina_limit_per_level", "Stamina Limit Per Level", 10.0, "Stamina pool gained per point of physical stamina."),
            _field("baseline_stamina_regen_per_turn", "Baseline Stamina Regen Per Turn", 15.0, "Stamina regenerated per baseline turn at baseline physical stamina."),
            _field("stamina_regen_per_level", "Stamina Regen Per Level", 3.0, "Additional stamina regen per baseline turn for each point of physical stamina."),
            _field("healthy_health_ratio_threshold", "Healthy HP Ratio", 0.76, "Minimum health ratio for the Healthy state."),
            _field("injured_health_ratio_threshold", "Injured HP Ratio", 0.51, "Minimum health ratio for the Injured state."),
            _field("heavily_injured_health_ratio_threshold", "Heavily Injured HP Ratio", 0.26, "Minimum health ratio for the Heavily Injured state."),
        ],
    },
    FACTION_STAT_FACTORS_CATEGORY: {
        "title": "Faction Stat Factors",
        "description": "Reserved for faction-level tuning values. Empty for now.",
        "filename": "faction_stat_factors.json",
        "fields": [],
    },
    MISC_CATEGORY: {
        "title": "Misc",
        "description": "Heuristic and non-core balancing values used by support systems like power rating.",
        "filename": "misc.json",
        "fields": [
            _field("neutral_affinity", "Neutral Affinity", 0.5, "Default affinity fraction when no better value is available."),
            _field("affinity_power_min_multiplier", "Affinity Power Min Mult", 0.80, "Minimum multiplier at zero affinity."),
            _field("affinity_power_bonus_range", "Affinity Power Bonus Range", 0.40, "Extra multiplier span gained as affinity rises from zero to one."),
            _field("all_attributes_flat_bonus_weight", "All Attributes Flat Weight", 6.0, "Power-rating weight for a flat all-attributes bonus."),
            _field("simulated_power_reference_bonus", "Simulated Power Reference Bonus", 6.0, "Reference bonus used when converting simulated advantage back into a power equivalent."),
            _field("inventory_consumable_power_weight", "Inventory Consumable Weight", 0.50, "Weight applied to the top consumables when estimating character power."),
            _field("inventory_consumable_slots_considered", "Inventory Consumables Counted", 3, "How many top consumables count toward heuristic inventory power.", value_type="int"),
            _field("spell_heuristic_level_bonus_per_level", "Spell Level Bonus Per Level", 0.50, "Heuristic spell power gain per spell level."),
            _field("spell_heuristic_range_cap", "Spell Range Bonus Cap", 25.0, "Maximum range value counted by spell power heuristics."),
            _field("spell_heuristic_range_bonus_per_unit", "Spell Range Bonus Per Unit", 0.03, "Heuristic spell power gain per unit of range."),
            _field("spell_heuristic_duration_cap", "Spell Duration Bonus Cap", 12.0, "Maximum duration value counted by spell power heuristics."),
            _field("spell_heuristic_duration_bonus_per_unit", "Spell Duration Bonus Per Unit", 0.05, "Heuristic spell power gain per unit of duration."),
            _field("spell_heuristic_casting_penalty_cap", "Spell Casting Penalty Cap", 0.50, "Maximum casting-time penalty in spell power heuristics."),
            _field("spell_heuristic_casting_penalty_per_unit", "Spell Casting Penalty Per Unit", 0.03, "Heuristic spell power penalty per unit of casting time."),
            _field("spell_heuristic_component_bonus_per_component", "Spell Component Bonus Per Component", 0.10, "Heuristic spell power bonus per required spell component."),
            _field("performance_margin_weight", "Performance Margin Weight", 0.25, "Weight of remaining-health margin in simulated power scoring."),
            _field("recommended_simulation_weight", "Recommended Simulation Weight", 0.80, "Blend weight for simulated power recommendations."),
            _field("recommended_heuristic_weight", "Recommended Heuristic Weight", 0.20, "Blend weight for heuristic power recommendations."),
            _field("offensive_consumable_impact_multiplier", "Offensive Consumable Impact Mult", 0.90, "Power-rating multiplier for offensive consumables."),
            _field("food_consumable_impact_multiplier", "Food Consumable Impact Mult", 0.50, "Power-rating multiplier for food consumables."),
            _field("default_consumable_impact_multiplier", "Default Consumable Impact Mult", 0.70, "Power-rating multiplier for non-offensive, non-food consumables."),
            _field("weapon_heuristic_sample_count", "Weapon Heuristic Samples", 40, "Sample count for weapon power-rating simulations.", value_type="int"),
            _field("weapon_heuristic_target_armor", "Weapon Heuristic Target Armor", 10.0, "Target armor value used by weapon power-rating simulations."),
            _field("weapon_heuristic_armor_damage_weight", "Weapon Heuristic Armor Damage Weight", 0.35, "Armor damage weight in weapon power heuristics."),
            _field("armor_heuristic_sample_count", "Armor Heuristic Samples", 30, "Sample count for armor power-rating simulations.", value_type="int"),
            _field("armor_heuristic_damage_prevent_weight", "Armor Damage Prevent Weight", 0.15, "Armor prevented-damage weight in armor power heuristics."),
            _field("armor_heuristic_offhand_max_armor_weight", "Offhand Max Armor Weight", 0.15, "Additional shield max-armor weight in armor power heuristics."),
        ],
    },
}


def _default_values_for_category(category: str) -> dict[str, Any]:
    schema = TUNING_SCHEMA.get(category, {})
    fields = schema.get("fields", [])
    return {field["key"]: copy.deepcopy(field["default"]) for field in fields}


DEFAULT_TUNING_VALUES = {
    category: _default_values_for_category(category)
    for category in TUNING_SCHEMA
}


class TuningRegistry:
    def __init__(self, directory: str):
        self._lock = threading.RLock()
        self._directory = str(directory or os.path.join(".", "GameData", "Tuning"))
        self._cache: dict[str, dict[str, Any]] = {}
        self._mtimes: dict[str, float | None] = {}

    @property
    def directory(self) -> str:
        return self._directory

    def configure(self, directory: str):
        with self._lock:
            self._directory = str(directory or os.path.join(".", "GameData", "Tuning"))
            self._cache.clear()
            self._mtimes.clear()

    def ensure_files(self):
        for category in TUNING_SCHEMA:
            self._ensure_category_file(category)

    def list_categories(self) -> list[str]:
        return list(TUNING_SCHEMA.keys())

    def get_category_schema(self, category: str) -> dict[str, Any]:
        return copy.deepcopy(TUNING_SCHEMA.get(category, {}))

    def get_category_path(self, category: str) -> str:
        return self._category_path(category)

    def export_all(self) -> dict[str, dict[str, Any]]:
        return {
            category: self.get_section(category)
            for category in TUNING_SCHEMA
        }

    def get_section(self, category: str) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._load_category(category))

    def reload_section(self, category: str) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._load_category(category, force_reload=True))

    def reload_all(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {
                category: copy.deepcopy(self._load_category(category, force_reload=True))
                for category in TUNING_SCHEMA
            }

    def get_value(self, category: str, key: str, default=None):
        with self._lock:
            section = self._load_category(category)
            if key in section:
                return copy.deepcopy(section[key])
            if default is not None:
                return default
            return copy.deepcopy(DEFAULT_TUNING_VALUES.get(category, {}).get(key))

    def get_float(self, category: str, key: str, default: float = 0.0) -> float:
        try:
            with self._lock:
                section = self._load_category(category)
                if key in section:
                    return float(section[key])
                if default is not None:
                    return float(default)
                return float(copy.deepcopy(DEFAULT_TUNING_VALUES.get(category, {}).get(key, 0.0)))
        except Exception:
            return float(default)

    def get_int(self, category: str, key: str, default: int = 0) -> int:
        try:
            with self._lock:
                section = self._load_category(category)
                if key in section:
                    return int(section[key])
                if default is not None:
                    return int(default)
                return int(copy.deepcopy(DEFAULT_TUNING_VALUES.get(category, {}).get(key, 0)))
        except Exception:
            return int(default)

    def save_section(self, category: str, values: dict[str, Any] | None):
        with self._lock:
            raw_values = values if isinstance(values, dict) else {}
            existing = copy.deepcopy(self._load_category(category))
            existing.update(raw_values)
            merged = self._normalize_loaded_section(category, existing)
            store = self._store_for(category)
            store.save(merged)
            self._cache[category] = copy.deepcopy(merged)
            self._mtimes[category] = self._get_mtime(category)

    def reset_section(self, category: str):
        self.save_section(category, DEFAULT_TUNING_VALUES.get(category, {}))

    def _category_path(self, category: str) -> str:
        filename = TUNING_SCHEMA.get(category, {}).get("filename", f"{category}.json")
        return os.path.join(self._directory, filename)

    def _store_for(self, category: str) -> TuningStore:
        return TuningStore(self._category_path(category))

    def _get_mtime(self, category: str) -> float | None:
        path = self._category_path(category)
        if not os.path.exists(path):
            return None
        try:
            return os.path.getmtime(path)
        except OSError:
            return None

    def _ensure_category_file(self, category: str):
        store = self._store_for(category)
        path = self._category_path(category)
        if not os.path.exists(path):
            store.save(copy.deepcopy(DEFAULT_TUNING_VALUES.get(category, {})))

    def _load_category(self, category: str, force_reload: bool = False) -> dict[str, Any]:
        if not force_reload and category in self._cache:
            return self._cache[category]
        self._ensure_category_file(category)
        if force_reload or category not in self._cache:
            raw = self._store_for(category).load()
            normalized = self._normalize_loaded_section(category, raw)
            self._cache[category] = normalized
            self._mtimes[category] = self._get_mtime(category)
        return self._cache[category]

    def _normalize_loaded_section(self, category: str, raw: dict[str, Any]) -> dict[str, Any]:
        raw = raw if isinstance(raw, dict) else {}
        defaults = copy.deepcopy(DEFAULT_TUNING_VALUES.get(category, {}))
        normalized = copy.deepcopy(defaults)
        fields = {field["key"]: field for field in TUNING_SCHEMA.get(category, {}).get("fields", [])}

        for key, value in raw.items():
            field = fields.get(key)
            if field is None:
                normalized[key] = copy.deepcopy(value)
                continue
            normalized[key] = self._coerce_value(field, value)
        return normalized

    @staticmethod
    def _coerce_value(field: dict[str, Any], value: Any):
        value_type = field.get("type", "float")
        default = field.get("default")
        try:
            if value_type == "int":
                return int(value)
            if value_type == "float":
                return float(value)
        except Exception:
            return copy.deepcopy(default)
        return copy.deepcopy(value)


_registry = TuningRegistry(os.path.join(".", "GameData", "Tuning"))


def configure_tuning_directory(directory: str):
    _registry.configure(directory)


def get_tuning_registry() -> TuningRegistry:
    return _registry


def battle_factor(key: str, default: float = 0.0) -> float:
    return _registry.get_float(BATTLE_FACTORS_CATEGORY, key, default)


def battle_factor_int(key: str, default: int = 0) -> int:
    return _registry.get_int(BATTLE_FACTORS_CATEGORY, key, default)


def character_stat_factor(key: str, default: float = 0.0) -> float:
    return _registry.get_float(CHARACTER_STAT_FACTORS_CATEGORY, key, default)


def character_stat_factor_int(key: str, default: int = 0) -> int:
    return _registry.get_int(CHARACTER_STAT_FACTORS_CATEGORY, key, default)


def misc_factor(key: str, default: float = 0.0) -> float:
    return _registry.get_float(MISC_CATEGORY, key, default)


def misc_factor_int(key: str, default: int = 0) -> int:
    return _registry.get_int(MISC_CATEGORY, key, default)
