import unittest

from src.domain.Character import Character
from src.domain.CharacterUtil import Achievement, Attribute, AttributeBonus, Attributes, Bonus, BonusType


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


if __name__ == "__main__":
    unittest.main()
