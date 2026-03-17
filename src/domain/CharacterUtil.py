

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
    PRIMARY_WEAPON = 8
    OFFHAND = 9


class HitLocation(Enum):
    HEAD = 1
    BODY = 2
    ARMS = 3
    LEGS = 4


class BodyPart(Enum):
    HEAD = 0
    FACE = 1
    NECK = 2
    SHOULDER = 3
    ARM = 4
    HAND = 5
    CHEST = 6
    BACK = 7
    ABDOMEN = 8
    HIP = 9
    LEG = 10
    FOOT = 11


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

class ConsumableKind(Enum):
    NONE = 0
    POTION = 1
    BOMB = 2
    FOOD = 3

class TitlePreference(Enum):
    Masculine = True
    Feminine = False


class FriendlyFireTolerance(Enum):
    NO_FRIENDLY_FIRE = "No friendly fire"
    AVOID_INTENTIONAL_ALLOW_RISK = "Avoid intentional but allow risk"
    FRIENDLY_FIRE_IF_CAN_HIT_ENEMY_TOO = "Friendly fire if can hit enemy too"
    FRIENDLY_FIRE_FOR_FUN = "Friendly fire for fun"


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
    def __init__(self, powerType: PowerType, power: int, spellName: str = ""):
        self.powerType = powerType
        self.power = power
        self.spellName = spellName


class AttributeBonus:
    def __init__(self, attribute: Attribute, bonus: int):
        self.attribute = attribute
        self.bonus = bonus


class Attributes:
    def __init__(self, physicalPower: float = 5, physicalStamina: float = 5, physicalResistance: float = 5, magicPower: float = 5, magicStamina: float = 5, magicResistance: float = 5):
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


def _percentage_points_to_multiplier(value: float) -> float:
    # Percentage bonuses are stored as whole percentage points, e.g. 10 means +10%.
    return float(value) / 100.0

# each value is a percentage, from 0.01 at the lowest to 0.9 at the highest.
class Affinities:
    def __init__(self, chi: float = 0.5, mana: float = 0.5, psi: float = 0.5, aether: float = 0.5):
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
                if bonus.permanent:
                    self.flatInherentAttributes.IncreaseAttribute(bonus.attributeBonus.attribute, bonus.attributeBonus.bonus)
                else:
                    self.flatBonusAttributes.IncreaseAttribute(bonus.attributeBonus.attribute, bonus.attributeBonus.bonus)
            if bonus.affinities is not None:
                self.flatAffinities.AddAffinities(bonus.affinities)

        if bonus.bonusType == BonusType.PERCENTAGE:
            if bonus.attributeBonus is not None:
                multiplier_value = _percentage_points_to_multiplier(bonus.attributeBonus.bonus)
                self.percentAttributes.IncreaseAttribute(bonus.attributeBonus.attribute, multiplier_value)
                if bonus.attributeBonus.attribute == Attribute.ALL_ATTRIBUTES:
                    self.allStatBonusUIAmount += multiplier_value
            if bonus.affinities is not None:
                self.percentAffinities.AddAffinities(bonus.affinities)

        if bonus.nanoMultiplier > 0:
            self.nanoMultiplier += bonus.nanoMultiplier

    def ApplyAllBonuses(self, bonuses: list[Bonus]):
        for bonus in bonuses:
            if bonus is not None:
                self.ApplyBonus(bonus)


class Achievement:
    def __init__(self, name: str, bonus: Bonus = None, title: str = "", description:str = "", bonuses: list[Bonus] = None):
        self.name = name
        self.title = title
        self.description = description
        if bonuses is not None:
            self.bonuses = [entry for entry in bonuses if entry is not None]
        elif bonus is not None:
            self.bonuses = [bonus]
        else:
            self.bonuses = []

    @property
    def bonus(self) -> Bonus | None:
        return self.bonuses[0] if self.bonuses else None

    @bonus.setter
    def bonus(self, value: Bonus | None):
        self.bonuses = [value] if value is not None else []

class CharacterStatistics:
    def __init__(
        self,
        kills: int = 0,
        damageTaken: float = 0.0,
        missionCount: int = 0,
        damageDone: float = 0.0,
        spellsCast: int = 0,
        injuriesTaken: int = 0,
        alliesProtected: int = 0,
        bossesKilled: int = 0,
        elitesKilled: int = 0,
        unitsKilled: dict[str, int] | None = None,
    ):
        self.kills = max(0, int(kills or 0))
        self.damageTaken = max(0.0, float(damageTaken or 0.0))
        self.missionCount = max(0, int(missionCount or 0))
        self.damageDone = max(0.0, float(damageDone or 0.0))
        self.spellsCast = max(0, int(spellsCast or 0))
        self.injuriesTaken = max(0, int(injuriesTaken or 0))
        self.alliesProtected = max(0, int(alliesProtected or 0))
        self.bossesKilled = max(0, int(bossesKilled or 0))
        self.elitesKilled = max(0, int(elitesKilled or 0))
        normalized_units_killed: dict[str, int] = {}
        if isinstance(unitsKilled, dict):
            for key, value in unitsKilled.items():
                name = str(key or '').strip()
                if not name:
                    continue
                try:
                    count = int(value)
                except Exception:
                    count = 0
                if count > 0:
                    normalized_units_killed[name] = count
        self.unitsKilled = normalized_units_killed

    def record_damage_done(self, amount: float):
        amount = max(0.0, float(amount or 0.0))
        if amount <= 0.0:
            return
        self.damageDone += amount

    def record_damage_taken(self, amount: float):
        amount = max(0.0, float(amount or 0.0))
        if amount <= 0.0:
            return
        self.damageTaken += amount
        self.injuriesTaken += 1

    def record_spell_cast(self):
        self.spellsCast += 1

    def record_ally_protected(self, count: int = 1):
        self.alliesProtected += max(0, int(count or 0))

    def record_kill(self, unit_name: str, count: int = 1, is_boss: bool = False, is_elite: bool = False):
        count = max(0, int(count or 0))
        if count <= 0:
            return
        self.kills += count
        name = str(unit_name or '').strip() or 'Unknown Unit'
        self.unitsKilled[name] = self.unitsKilled.get(name, 0) + count
        if is_boss:
            self.bossesKilled += count
        if is_elite:
            self.elitesKilled += count

