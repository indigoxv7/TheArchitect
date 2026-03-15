import unittest

from src.domain.Character import Character
from src.domain.Items import Weapon
from src.domain.Spells import AffinityTypes, Spell
from src.services.power_rating_service import PowerRatingService


class TestPowerRatingService(unittest.TestCase):
    def setUp(self):
        self.service = PowerRatingService(sample_count=40, seed=42)

    def test_base_character_power_level_is_30(self):
        character = Character(name="Baseline")
        self.assertEqual(self.service.character_power_level(character), 30.0)

    def test_affinity_multiplier_supports_fraction_and_percentage_inputs(self):
        self.assertAlmostEqual(self.service.affinity_power_multiplier(0.5), 1.0, places=3)
        self.assertAlmostEqual(self.service.affinity_power_multiplier(50), 1.0, places=3)
        self.assertAlmostEqual(self.service.affinity_power_multiplier(1), 0.804, places=3)
        self.assertAlmostEqual(self.service.affinity_power_multiplier(99), 1.196, places=3)

    def test_character_power_level_counts_equipped_item_and_spell_power(self):
        weapon = Weapon(name="Practice Sword", powerLevel=10.0, damageMin=6.0, damageMax=8.0)
        spell = Spell(name="Spark", level=0, power=8.0, affinity=AffinityTypes.MANA, powerLevel=8.0)
        character = Character(name="Mage Knight", gear=None, spells=[spell])
        character.gear.primaryWeapon = weapon
        character.CalculateBonus()
        self.assertAlmostEqual(self.service.character_power_level(character), 48.0, places=3)

    def test_simulated_weapon_power_is_positive(self):
        weapon = Weapon(
            name="Balanced Sword",
            damageMin=8.0,
            damageMax=10.0,
            penetrationBase=3.0,
            powerLevel=0.0,
        )
        result = self.service.simulate_item_power_level(weapon, sample_count=30)
        self.assertGreater(result.recommendedPowerLevel, 0.0)
        self.assertGreaterEqual(result.winRate, 0.0)

    def test_simulated_spell_power_is_positive(self):
        spell = Spell(name="Arc Bolt", level=1, power=10.0, affinity=AffinityTypes.MANA, powerLevel=0.0)
        result = self.service.simulate_spell_power_level(spell, sample_count=30)
        self.assertGreater(result.recommendedPowerLevel, 0.0)
        self.assertGreaterEqual(result.winRate, 0.0)


if __name__ == "__main__":
    unittest.main()
