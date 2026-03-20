import unittest

from src.domain.Character import Character
from src.domain.character_util import Achievement, Attribute, AttributeBonus, Attributes, Bonus, BonusType


def _uniform_attributes(value: float) -> Attributes:
    return Attributes(
        physicalPower=value,
        physicalStamina=value,
        physicalResistance=value,
        magicPower=value,
        magicStamina=value,
        magicResistance=value,
    )


class TestCharacterBonusCalculation(unittest.TestCase):
    def test_percentage_bonus_uses_percentage_points(self):
        ten_percent_all = Bonus(
            bonusType=BonusType.PERCENTAGE,
            attributeBonus=AttributeBonus(attribute=Attribute.ALL_ATTRIBUTES, bonus=10),
            permanent=True,
        )
        character = Character(
            name="Percent Tester",
            attributes=_uniform_attributes(100),
            achievements=[Achievement(name="Ten Percent", bonuses=[ten_percent_all])],
        )

        self.assertAlmostEqual(character.finalAttributes.physicalPower, 110.0)
        self.assertAlmostEqual(character.finalAttributes.magicResistance, 110.0)

        details = character.GetAttributesString()
        self.assertIn("Increased by 10%", details)
        self.assertNotIn("(+1000%)", details)
        self.assertNotIn("1000%", details)

    def test_permanent_flat_bonus_is_applied_before_percentage(self):
        bonuses = [
            Bonus(
                bonusType=BonusType.FLAT,
                attributeBonus=AttributeBonus(attribute=Attribute.PHYSICAL_POWER, bonus=10),
                permanent=True,
            ),
            Bonus(
                bonusType=BonusType.FLAT,
                attributeBonus=AttributeBonus(attribute=Attribute.PHYSICAL_POWER, bonus=5),
                permanent=False,
            ),
            Bonus(
                bonusType=BonusType.PERCENTAGE,
                attributeBonus=AttributeBonus(attribute=Attribute.PHYSICAL_POWER, bonus=10),
                permanent=False,
            ),
        ]
        character = Character(
            name="Order Tester",
            attributes=_uniform_attributes(100),
            achievements=[Achievement(name="Stacking", bonuses=bonuses)],
        )

        # Expected order: (base + permanent flat) * (1 + percent) + temporary flat
        self.assertAlmostEqual(character.finalAttributes.physicalPower, 126.0)

    def test_calculate_bonus_does_not_stack_when_called_multiple_times(self):
        ten_percent = Bonus(
            bonusType=BonusType.PERCENTAGE,
            attributeBonus=AttributeBonus(attribute=Attribute.PHYSICAL_POWER, bonus=10),
            permanent=True,
        )
        character = Character(
            name="Recalc Tester",
            attributes=_uniform_attributes(100),
            achievements=[Achievement(name="Single Buff", bonuses=[ten_percent])],
        )

        first_value = character.finalAttributes.physicalPower
        character.CalculateBonus()
        second_value = character.finalAttributes.physicalPower

        self.assertAlmostEqual(first_value, 110.0)
        self.assertAlmostEqual(second_value, 110.0)

    def test_max_health_scales_from_physical_resistance(self):
        baseline = Character(name="Baseline Health", attributes=_uniform_attributes(5))
        durable = Character(name="Durable", attributes=_uniform_attributes(20))

        self.assertAlmostEqual(baseline.GetMaxHealth(), 55.0)
        self.assertAlmostEqual(durable.GetMaxHealth(), 55.0 * ((20.0 / 5.0) ** 0.80))

    def test_speed_uses_weighted_physical_and_magic_power(self):
        swift = Character(
            name="Swift",
            attributes=Attributes(
                physicalPower=12,
                physicalStamina=5,
                physicalResistance=5,
                magicPower=9,
                magicStamina=5,
                magicResistance=5,
            ),
        )

        self.assertAlmostEqual(swift.GetSpeed(), ((12.0 * 2.0) + 9.0) / 15.0)

    def test_speed_baseline_is_one_for_five_and_five_power(self):
        baseline = Character(name="Baseline Speed", attributes=_uniform_attributes(5))

        self.assertAlmostEqual(baseline.GetSpeed(), 1.0)

    def test_stamina_limit_and_regen_scale_from_physical_stamina(self):
        baseline = Character(name="Baseline Stamina", attributes=_uniform_attributes(5))
        durable = Character(name="Durable Stamina", attributes=_uniform_attributes(8))

        self.assertAlmostEqual(baseline.GetStaminaLimit(), 75.0)
        self.assertAlmostEqual(baseline.GetStaminaRegenPerSecond(), 15.0 / 6.0)
        self.assertAlmostEqual(durable.GetStaminaLimit(), 105.0)
        self.assertAlmostEqual(durable.GetStaminaRegenPerSecond(), 24.0 / 6.0)


if __name__ == "__main__":
    unittest.main()
