

from enum import Enum
DEFAULT_DURABILITY = 100


class EquipSlot(Enum):
    NOT_EQUIPABLE = 0
    HEAD = 1
    NECK = 2
    BODY = 3
    HANDS = 4
    RING = 5
    LEGS = 6
    FEET = 7


class Attribute(Enum):
    PHYSICAL_POWER = 0
    PHYSICAL_STAMINA = 1
    PHYSICAL_RESISTANCE = 2
    MAGIC_POWER = 3
    MAGIC_STAMINA = 4
    MAGIC_RESISTANCE = 5
    ALL_ATTRIBUTES = 6


class PowerType(Enum):
    PHYSICAL_ATTACK = 0
    MAGIC_ATTACK = 1
    CONSUMABLE_POWER = 3


class DamageType(Enum):
    PIERCING = 0
    BLUDGEONING = 1
    SLASHING = 2
    COLD = 3
    FIRE = 4
    LIGHTNING = 5
    THUNDER = 6
    POISON = 7
    ACID = 8
    RADIANT = 9
    NECROTIC = 10
    FORCE = 11
    PSYCHIC = 12


class ItemType(Enum):
    DEFAULT = 0
    CONSUMABLE = 1
    MELEE_WEAPON = 2
    MELEE_THROWABLE = 3
    RANGED_WEAPON = 4
    ARMOR = 5


class TitlePreference(Enum):
    Masculine = True
    Feminine = False


def AffinityFormula(affinity: float, factor: float):
    return affinity * (1+factor*(1-(affinity/100)))


def AbbreviateNumber(number: int) -> str:
    if abs(number) >= 1_000_000_000_000:
        return f"{number / 1_000_000_000_000:.1f}T"
    elif abs(number) >= 1_000_000_000:
        return f"{number / 1_000_000_000:.1f}B"
    elif abs(number) >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    else:
        return str(number)


class ItemPower:
    def __init__(self, powerType: PowerType, power: int):
        self.powerType = powerType
        self.power = power


class AttributeBonus:
    def __init__(self, attribute: Attribute, bonus: int):
        self.attribute = attribute
        self.bonus = bonus


class Attributes:
    def __init__(self, physicalPower: float, physicalStamina: float, physicalResistance: float, magicPower: float, magicStamina: float, magicResistance: float):
        self.physicalPower = physicalPower
        self.physicalStamina = physicalStamina
        self.physicalResistance = physicalResistance
        self.magicPower = magicPower
        self.magicStamina = magicStamina
        self.magicResistance = magicResistance

    def IncreaseAttribute(self, a: Attribute, value: float):
        if a == Attribute.PHYSICAL_POWER:
            self.physicalPower += value
        elif a == Attribute.PHYSICAL_STAMINA:
            self.physicalStamina += value
        elif a == Attribute.PHYSICAL_RESISTANCE:
            self.physicalResistance += value
        elif a == Attribute.MAGIC_POWER:
            self.magicPower += value
        elif a == Attribute.MAGIC_STAMINA:
            self.magicStamina += value
        elif a == Attribute.MAGIC_RESISTANCE:
            self.magicResistance += value
        elif a == Attribute.ALL_ATTRIBUTES:
            self.physicalPower += value
            self.physicalStamina += value
            self.physicalResistance += value
            self.magicPower += value
            self.magicStamina += value
            self.magicResistance += value

    def AddAttributes(self, otherAttributes: 'Attributes'):
        self.physicalPower += otherAttributes.physicalPower
        self.physicalStamina += otherAttributes.physicalStamina
        self.physicalResistance += otherAttributes.physicalResistance
        self.magicPower += otherAttributes.magicPower
        self.magicStamina += otherAttributes.magicStamina
        self.magicResistance += otherAttributes.magicResistance

    def MultiplyAttributes(self, otherAttributes: 'Attributes'):
        self.physicalPower *= (1 + otherAttributes.physicalPower)
        self.physicalStamina *= (1 + otherAttributes.physicalStamina)
        self.physicalResistance *= (1 + otherAttributes.physicalResistance)
        self.magicPower *= (1 + otherAttributes.magicPower)
        self.magicStamina *= (1 + otherAttributes.magicStamina)
        self.magicResistance *= (1 + otherAttributes.magicResistance)

# each value is a percentage, from 0.01 at the lowest to 0.9 at the highest.
class Affinities:
    def __init__(self, chi: float, mana: float, psi: float, aether: float):
        self.chi = chi
        self.mana = mana
        self.psi = psi
        self.aether = aether

    def AddAffinities(self, otherAffinities: 'Affinities'):
        self.chi += otherAffinities.chi
        self.mana += otherAffinities.mana
        self.psi += otherAffinities.psi
        self.aether += otherAffinities.aether

    def MultiplyAffinities(self, otherAffinities: 'Affinities'):
        self.chi = AffinityFormula(self.chi, otherAffinities.chi)
        self.mana = AffinityFormula(self.mana, otherAffinities.mana)
        self.psi = AffinityFormula(self.psi, otherAffinities.psi)
        self.aether = AffinityFormula(self.aether, otherAffinities.aether)

class BonusType(Enum):
    FLAT = 0,
    PERCENTAGE = 1


# This class is presumed to work by holding only the appropriate type of bonuses. A bonus of None or 0 should be ignored.
# Flat bonus's should be applied first, then multipliers.
# if the bonus type is flat, add it. if the bonus is percentage, multiply.
class Bonus:
    def __init__(self, bonusType: BonusType, attributeBonus: AttributeBonus = None, affinities: Affinities = None, nanoMultiplier: float = 0, reason: str = "", permanent: bool = False):
        self.bonusType = bonusType
        self.attributeBonus = attributeBonus
        self.affinities = affinities
        self.nanoMultiplier = nanoMultiplier
        self.reason = reason
        self.permanent = permanent # this tells us if the stat should be treated as a base stat, E.G. an achievement that gives you +1 to all stats.


class TotalBonus:
    def __init__(self, allBonuses: list[Bonus] = None):
        self.flatInherentAttributes = Attributes(0, 0, 0, 0, 0, 0)
        self.flatBonusAttributes = Attributes(0, 0, 0, 0, 0, 0)
        self.percentAttributes = Attributes(0, 0, 0, 0, 0, 0)
        self.flatAffinities = Affinities(0, 0, 0, 0)
        self.percentAffinities = Affinities(0, 0, 0, 0)
        self.allStatBonusUIAmount = 0.0 # This is just so that we can keep track of the total increase for regular
        # attributes like shown in the lore. Not to be applied again on top of stats, as they are individually correct already.
        self.nanoMultiplier = 0.0
        if allBonuses is not None:
            self.ApplyAllBonuses(allBonuses)

    def ApplyBonus(self, bonus: Bonus):
        if bonus.bonusType == BonusType.FLAT:
            if bonus.attributeBonus is not None:
                if not bonus.permanent:
                    self.flatInherentAttributes.IncreaseAttribute(bonus.attributeBonus.attribute, bonus.attributeBonus.bonus)
                else:
                    self.flatBonusAttributes.IncreaseAttribute(bonus.attributeBonus.attribute, bonus.attributeBonus.bonus)
            if bonus.affinities is not None:
                self.flatAffinities.AddAffinities(bonus.affinities)

        if bonus.bonusType == BonusType.PERCENTAGE:
            if bonus.attributeBonus is not None:
                self.percentAttributes.IncreaseAttribute(bonus.attributeBonus.attribute, bonus.attributeBonus.bonus)
                if bonus.attributeBonus.attribute == Attribute.ALL_ATTRIBUTES:
                    self.allStatBonusUIAmount += bonus.attributeBonus.bonus
            if bonus.affinities is not None:
                self.percentAffinities.AddAffinities(bonus.affinities)

        if bonus.nanoMultiplier > 0:
            self.nanoMultiplier += bonus.nanoMultiplier

    def ApplyAllBonuses(self, bonuses: list[Bonus]):
        for bonus in bonuses:
            if bonus is not None:
                self.ApplyBonus(bonus)


class Achievement:
    def __init__(self, name: str, bonus: Bonus = None, title: str = ""):
        self.name = name
        self.bonus = bonus
        self.title = title

