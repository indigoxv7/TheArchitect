import json
import os
import tempfile
import unittest
from unittest.mock import patch

from src.config.tuning import (
    BATTLE_FACTORS_CATEGORY,
    CHARACTER_STAT_FACTORS_CATEGORY,
    FACTION_STAT_FACTORS_CATEGORY,
    MISC_CATEGORY,
    configure_tuning_directory,
    get_tuning_registry,
)
from src.domain.Character import Character
from src.domain.character_util import Attributes
from src.domain.combat_timing import ExertionLevel, action_interval_seconds
from src.services.damage_calculator import DamageCalculator


def _uniform_attributes(value: float) -> Attributes:
    return Attributes(
        physicalPower=value,
        physicalStamina=value,
        physicalResistance=value,
        magicPower=value,
        magicStamina=value,
        magicResistance=value,
    )


class TestTuningSettings(unittest.TestCase):
    def setUp(self):
        self.registry = get_tuning_registry()
        self.original_directory = self.registry.directory
        self.temp_dir = tempfile.TemporaryDirectory()
        configure_tuning_directory(self.temp_dir.name)
        self.registry = get_tuning_registry()
        self.registry.ensure_files()

    def tearDown(self):
        configure_tuning_directory(self.original_directory)
        get_tuning_registry().ensure_files()
        self.temp_dir.cleanup()

    def test_registry_creates_category_files(self):
        expected_files = {
            BATTLE_FACTORS_CATEGORY: "battle_factors.json",
            CHARACTER_STAT_FACTORS_CATEGORY: "character_stat_factors.json",
            FACTION_STAT_FACTORS_CATEGORY: "faction_stat_factors.json",
            MISC_CATEGORY: "misc.json",
        }
        for category, filename in expected_files.items():
            self.assertTrue(os.path.exists(self.registry.get_category_path(category)), category)
            self.assertTrue(self.registry.get_category_path(category).endswith(filename))

    def test_character_derived_stats_update_after_save(self):
        baseline = Character(name="Baseline", attributes=_uniform_attributes(5))
        self.assertAlmostEqual(baseline.GetMaxHealth(), 55.0)

        section = self.registry.get_section(CHARACTER_STAT_FACTORS_CATEGORY)
        section["base_health_at_baseline"] = 70.0
        self.registry.save_section(CHARACTER_STAT_FACTORS_CATEGORY, section)

        updated = Character(name="Updated", attributes=_uniform_attributes(5))
        self.assertAlmostEqual(updated.GetMaxHealth(), 70.0)

    def test_damage_calculator_uses_live_battle_factors(self):
        calculator = DamageCalculator()
        self.assertAlmostEqual(calculator.calculate_hit_chance(5.0, 5.0), 0.65)

        section = self.registry.get_section(BATTLE_FACTORS_CATEGORY)
        section["base_hit_chance"] = 0.80
        self.registry.save_section(BATTLE_FACTORS_CATEGORY, section)

        self.assertAlmostEqual(calculator.calculate_hit_chance(5.0, 5.0), 0.80)

    def test_combat_timing_uses_live_turn_seconds(self):
        self.assertAlmostEqual(action_interval_seconds(2.0, ExertionLevel.FRESH.name), 3.0)

        section = self.registry.get_section(BATTLE_FACTORS_CATEGORY)
        section["baseline_turn_seconds"] = 8.0
        self.registry.save_section(BATTLE_FACTORS_CATEGORY, section)

        self.assertAlmostEqual(action_interval_seconds(2.0, ExertionLevel.FRESH.name), 4.0)

    def test_hot_path_getters_reuse_cached_values_without_disk_checks(self):
        self.registry.get_section(BATTLE_FACTORS_CATEGORY)

        with patch.object(self.registry, "_get_mtime", wraps=self.registry._get_mtime) as get_mtime:
            for _ in range(20):
                self.registry.get_float(BATTLE_FACTORS_CATEGORY, "base_hit_chance", 0.65)
            self.assertEqual(get_mtime.call_count, 0)

    def test_reload_section_refreshes_cache_after_external_file_change(self):
        path = self.registry.get_category_path(BATTLE_FACTORS_CATEGORY)
        payload = self.registry.get_section(BATTLE_FACTORS_CATEGORY)
        payload["base_hit_chance"] = 0.77
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=4, ensure_ascii=False)

        self.assertAlmostEqual(self.registry.get_float(BATTLE_FACTORS_CATEGORY, "base_hit_chance", 0.65), 0.65)
        self.registry.reload_section(BATTLE_FACTORS_CATEGORY)
        self.assertAlmostEqual(self.registry.get_float(BATTLE_FACTORS_CATEGORY, "base_hit_chance", 0.65), 0.77)


if __name__ == "__main__":
    unittest.main()
