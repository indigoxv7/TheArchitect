import random
import unittest

from src.domain.Character import Character
from src.domain.character_util import Attributes, EquipSlot, HitLocation, ItemType
from src.domain.items import Armor, Gear, Weapon
from src.services.damage_calculator import DamageCalculator


class TestDamageCalculator(unittest.TestCase):
    def _build_attacker(self) -> Character:
        return Character(
            name="Attacker",
            attributes=Attributes(
                physicalPower=41,
                physicalStamina=5,
                physicalResistance=5,
                magicPower=18,
                magicStamina=5,
                magicResistance=5,
            ),
        )

    def _build_defender(self) -> Character:
        body_armor = Armor(name="Body Armor", slot=EquipSlot.BODY, maxArmor=120, currentArmor=120)
        return Character(
            name="Defender",
            attributes=Attributes(
                physicalPower=5,
                physicalStamina=5,
                physicalResistance=41,
                magicPower=5,
                magicStamina=5,
                magicResistance=12,
            ),
            gear=Gear(body=body_armor),
        )

    def _build_unarmored_defender(self, physical_resistance: float = 41) -> Character:
        return Character(
            name="Unarmored Defender",
            attributes=Attributes(
                physicalPower=5,
                physicalStamina=5,
                physicalResistance=physical_resistance,
                magicPower=5,
                magicStamina=5,
                magicResistance=12,
            ),
            gear=Gear(),
        )

    def _build_weapon(self, **overrides) -> Weapon:
        data = {
            "name": "Nano Longsword",
            "slot": EquipSlot.PRIMARY_WEAPON,
            "itemType": ItemType.MELEE_WEAPON,
            "damageType": [],
            "damageMin": 25,
            "damageMax": 35,
            "armorMultiplier": 1.2,
            "ignoreArmorFraction": 0.25,
            "penetrationBase": 110.0,
        }
        data.update(overrides)
        return Weapon(**data)

    def test_calculate_physical_hit_to_location_updates_armor(self):
        calculator = DamageCalculator(rng=random.Random(1337))
        attacker = self._build_attacker()
        defender = self._build_defender()
        weapon = self._build_weapon()

        result = calculator.calculate_physical_hit_to_location(
            attacker=attacker,
            defender=defender,
            weapon=weapon,
            location=HitLocation.BODY,
            applyArmorDamageToGear=True,
        )

        self.assertAlmostEqual(result.armorBefore, 120.0)
        self.assertAlmostEqual(result.armorAfter, 0.0)
        self.assertAlmostEqual(result.hpFinal, 43.29072525891453)
        self.assertAlmostEqual(defender.gear.get_armor(HitLocation.BODY), 0.0)

    def test_unarmored_target_has_no_hidden_armor_reduction(self):
        calculator = DamageCalculator(rng=random.Random(1337))
        attacker = self._build_attacker()
        defender = self._build_unarmored_defender()
        weapon = self._build_weapon()

        result = calculator.calculate_physical_hit(
            attacker=attacker,
            defender=defender,
            weapon=weapon,
            targetArmor=0.0,
        )

        self.assertAlmostEqual(result.armorBefore, 0.0)
        self.assertAlmostEqual(result.armorDamage, 0.0)
        self.assertAlmostEqual(result.armorAfter, 0.0)
        self.assertAlmostEqual(result.penetrationEffectiveness, 1.0)
        self.assertAlmostEqual(result.penetrationDamageReduction, 0.0)
        self.assertAlmostEqual(result.hpFinal, result.hpPreResistance)
        self.assertAlmostEqual(result.bodyArmorRating, 0.0)
        self.assertAlmostEqual(result.bodyDamageReduction, 0.0)

    def test_calculate_physical_hit_to_location_without_armor_writeback(self):
        calculator = DamageCalculator(rng=random.Random(1337))
        attacker = self._build_attacker()
        defender = self._build_defender()
        weapon = self._build_weapon()

        result = calculator.calculate_physical_hit_to_location(
            attacker=attacker,
            defender=defender,
            weapon=weapon,
            location=HitLocation.BODY,
            applyArmorDamageToGear=False,
        )

        self.assertAlmostEqual(result.armorAfter, 0.0)
        self.assertAlmostEqual(defender.gear.get_armor(HitLocation.BODY), 120.0)

    def test_invalid_damage_range_raises(self):
        calculator = DamageCalculator(rng=random.Random(7))
        attacker = self._build_attacker()
        defender = self._build_defender()
        weapon = self._build_weapon(damageMin=20, damageMax=10)

        with self.assertRaises(ValueError):
            calculator.calculate_physical_hit(attacker=attacker, defender=defender, weapon=weapon, targetArmor=100)

    def test_weapon_damage_fields_round_trip(self):
        payload = {
            "name": "Test Weapon",
            "itemClass": "Weapon",
            "slot": "PRIMARY_WEAPON",
            "tier": 1,
            "durability": 80,
            "statBonuses": [],
            "itemType": "MELEE_WEAPON",
            "damageType": ["SLASHING"],
            "damageMin": 10,
            "damageMax": 20,
            "armorMultiplier": 1.3,
            "ignoreArmorFraction": 0.2,
            "penetrationBase": 45,
            "staminaCost": 13,
        }

        item = Weapon.from_dict(payload)
        self.assertAlmostEqual(item.damageMin, 10.0)
        self.assertAlmostEqual(item.damageMax, 20.0)
        self.assertAlmostEqual(item.armorMultiplier, 1.3)
        self.assertAlmostEqual(item.ignoreArmorFraction, 0.2)
        self.assertAlmostEqual(item.penetrationBase, 45.0)
        self.assertAlmostEqual(item.staminaCost, 13.0)
        self.assertEqual(item.slot.name, "PRIMARY_WEAPON")

        serialized = item.to_dict()
        self.assertEqual(serialized["damageMin"], 10)
        self.assertEqual(serialized["damageMax"], 20)
        self.assertEqual(serialized["armorMultiplier"], 1.3)
        self.assertEqual(serialized["ignoreArmorFraction"], 0.2)
        self.assertEqual(serialized["penetrationBase"], 45.0)
        self.assertEqual(serialized["staminaCost"], 13.0)

    def test_weapon_stamina_cost_defaults_when_missing(self):
        item = Weapon.from_dict(
            {
                "name": "Fallback Weapon",
                "itemClass": "Weapon",
                "slot": "PRIMARY_WEAPON",
                "itemType": "MELEE_WEAPON",
                "damageMin": 8,
                "damageMax": 9,
            }
        )

        self.assertAlmostEqual(item.staminaCost, 10.0)

    def test_hit_chance_is_clamped(self):
        calculator = DamageCalculator(rng=random.Random(1))
        low = calculator.calculate_hit_chance(attacker_stat=1, defender_stat=100)
        high = calculator.calculate_hit_chance(attacker_stat=100, defender_stat=1)

        self.assertEqual(low, 0.35)
        self.assertEqual(high, 0.9)

    def test_magic_hit_returns_damage_breakdown(self):
        calculator = DamageCalculator(rng=random.Random(2))
        attacker = self._build_attacker()
        defender = self._build_defender()

        result = calculator.calculate_magic_hit(attacker=attacker, defender=defender, spell_power=12, hit_chance=1.0)

        self.assertTrue(result.didHit)
        self.assertGreater(result.hpFinal, 0.0)
        self.assertLessEqual(result.hitChance, 1.0)

    def test_penetration_matching_resistance_keeps_full_effectiveness(self):
        calculator = DamageCalculator()

        self.assertEqual(calculator._compute_coupling_fraction(10.0, 10.0), 1.0)
        self.assertEqual(calculator._compute_coupling_fraction(14.0, 10.0), 1.0)

    def test_penetration_shortfall_reaches_zero_at_baseline_window(self):
        calculator = DamageCalculator()

        self.assertEqual(calculator._compute_coupling_fraction(5.0, 10.0), 0.0)
        self.assertGreater(calculator._compute_coupling_fraction(7.5, 10.0), 0.0)

    def test_penetration_shortfall_scales_with_higher_resistance(self):
        calculator = DamageCalculator()

        self.assertGreater(calculator._compute_coupling_fraction(45.0, 50.0), 0.0)
        self.assertEqual(calculator._compute_coupling_fraction(40.0, 50.0), 0.0)


if __name__ == "__main__":
    unittest.main()
