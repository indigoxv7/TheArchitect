import random
import unittest

from src.domain.Character import Character
from src.domain.CharacterUtil import Attributes, HitLocation
from src.domain.Items import Gear, Item
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
        body_armor = Item(name="Body Armor", durability=120)
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

    def _build_weapon(self, **overrides) -> Item:
        data = {
            "name": "Nano Longsword",
            "damageMin": 25,
            "damageMax": 35,
            "armorMultiplier": 1.2,
            "ignoreArmorFraction": 0.25,
            "penetrationBase": 110.0,
        }
        data.update(overrides)
        return Item(**data)

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
        self.assertAlmostEqual(result.hpFinal, 2.2153095615829637)
        self.assertAlmostEqual(defender.gear.get_armor(HitLocation.BODY), 0.0)

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

    def test_item_damage_fields_round_trip(self):
        payload = {
            "name": "Test Weapon",
            "slot": "HANDS",
            "tier": 1,
            "durability": 80,
            "statBonuses": [],
            "itemType": "MELEE_WEAPON",
            "itemPower": [{"powerType": "PHYSICAL_ATTACK", "power": 11, "spellName": ""}],
            "damageType": ["SLASHING"],
            "damageMin": 10,
            "damageMax": 20,
            "armorMultiplier": 1.3,
            "ignoreArmorFraction": 0.2,
            "penetrationBase": 45,
        }

        item = Item.from_dict(payload)
        self.assertAlmostEqual(item.damageMin, 10.0)
        self.assertAlmostEqual(item.damageMax, 20.0)
        self.assertAlmostEqual(item.armorMultiplier, 1.3)
        self.assertAlmostEqual(item.ignoreArmorFraction, 0.2)
        self.assertAlmostEqual(item.penetrationBase, 45.0)

        serialized = item.to_dict()
        self.assertEqual(serialized["damageMin"], 10.0)
        self.assertEqual(serialized["damageMax"], 20.0)
        self.assertEqual(serialized["armorMultiplier"], 1.3)
        self.assertEqual(serialized["ignoreArmorFraction"], 0.2)
        self.assertEqual(serialized["penetrationBase"], 45.0)

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


if __name__ == "__main__":
    unittest.main()
