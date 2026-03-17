import copy
from src.domain.CharacterUtil import *
from src.domain.Items import Gear, Item
from src.domain.GeneralSkills import GeneralSkills
from src.domain.Spells import Spell, SpellComponent
from src.config.Globals import *

class HealthState(Enum):
    HEALTHY = 0
    INJURED = 1
    HEAVILY_INJURED = 2
    DYING = 3
    UNCONSCIOUS = 4
    DEAD = 5

# A limited time bonus that the character has active.
class Buff:
    def __init__(self, bonus: Bonus, duration: int):
        self.bonus = bonus
        self.duration = duration

    # Returns true if there is any time left. Returns false if the bonus is now expired.
    def DecrementTime(self, amount: int = 1):
        self.duration -= amount
        return self.duration > 0


class Character:
    PRIMARY_STAT_BASELINE = 5.0
    DERIVED_STAT_ALPHA = 0.80
    BASE_HEALTH_AT_BASELINE = 55.0
    SPEED_PHYSICAL_WEIGHT = 0.66
    SPEED_MAGIC_WEIGHT = 0.33

    finalAttributes: Attributes
    finalAffinities: Affinities
    achievements: list[Achievement]
    spells: list[Spell]
    buffs: list[Buff]
    playerInstanceId: str
    race: str
    portraitURL: str
    footerImageURL: str
    friendlyFireTolerance: FriendlyFireTolerance

    def __init__(
        self,
        name: str,
        attributes: Attributes | None = None,
        level: int = 0,
        raceTier: str = "Tier I",
        affinities: Affinities | None = None,
        gear: Gear | None = None,
        achievements: list[Achievement] | None = None,
        generalSkills: list[GeneralSkills] | None = None,
        spells: list[Spell] | None = None,
        buffs: list[Buff] | None = None,
        race: str = "Human1",
        playerInstanceId: str = "",
        friendlyFireTolerance: FriendlyFireTolerance | str = FriendlyFireTolerance.NO_FRIENDLY_FIRE,
    ):
        self.name = name
        self.attributes = attributes if attributes is not None else Attributes()
        self.level = level
        self.raceTier = raceTier
        self.race = str(race or "Human1")
        self.playerInstanceId = str(playerInstanceId or "")
        self.affinities = affinities if affinities is not None else Affinities()
        self.gear = gear if gear is not None else Gear()
        self.activeAchievementTitle = ""
        self.description = ""
        self.portraitURL = ""
        self.footerImageURL = ""
        self.friendlyFireTolerance = self._coerce_friendly_fire_tolerance(friendlyFireTolerance)
        self.achievements = []
        if achievements is not None:
            if not isinstance(achievements, list):
                achievements = [achievements]

            for achievement in achievements:
                self.AddAchievement(achievement)
        self.generalSkills = generalSkills if generalSkills is not None else []
        self.spells = spells if spells is not None else []
        self.health = 0.0
        self.healthState = HealthState.HEALTHY
        self.buffs = buffs if buffs is not None else []
        self.totalBonus = TotalBonus(None)
        self.finalAttributes = copy.deepcopy(self.attributes)
        self.finalAffinities = copy.deepcopy(self.affinities)
        self.CalculateBonus()
        self.health = self.GetMaxHealth()

    @staticmethod
    def _coerce_friendly_fire_tolerance(value) -> FriendlyFireTolerance:
        if isinstance(value, FriendlyFireTolerance):
            return value
        text = str(value or "").strip()
        if not text:
            return FriendlyFireTolerance.NO_FRIENDLY_FIRE
        upper = text.upper()
        if upper in FriendlyFireTolerance.__members__:
            return FriendlyFireTolerance[upper]
        for entry in FriendlyFireTolerance:
            if str(entry.value).lower() == text.lower():
                return entry
        return FriendlyFireTolerance.NO_FRIENDLY_FIRE

    def EnsureRuntimeDefaults(self):
        if not hasattr(self, "race"):
            self.race = "Human1"
        if not hasattr(self, "playerInstanceId"):
            self.playerInstanceId = ""
        if not hasattr(self, "activeAchievementTitle"):
            self.activeAchievementTitle = ""
        if not hasattr(self, "description"):
            self.description = ""
        if not hasattr(self, "portraitURL"):
            self.portraitURL = ""
        if not hasattr(self, "footerImageURL"):
            self.footerImageURL = ""
        if not hasattr(self, "friendlyFireTolerance"):
            self.friendlyFireTolerance = FriendlyFireTolerance.NO_FRIENDLY_FIRE
        else:
            self.friendlyFireTolerance = self._coerce_friendly_fire_tolerance(self.friendlyFireTolerance)
        if not hasattr(self, "achievements") or self.achievements is None:
            self.achievements = []
        if not hasattr(self, "generalSkills") or self.generalSkills is None:
            self.generalSkills = []
        if not hasattr(self, "spells") or self.spells is None:
            self.spells = []
        if not hasattr(self, "buffs") or self.buffs is None:
            self.buffs = []
        if not hasattr(self, "health"):
            self.health = self.GetMaxHealth()
        if not hasattr(self, "healthState"):
            self.healthState = HealthState.HEALTHY
        if not hasattr(self, "attributes") or self.attributes is None:
            self.attributes = Attributes()
        if not hasattr(self, "affinities") or self.affinities is None:
            self.affinities = Affinities()
        if not hasattr(self, "gear") or self.gear is None:
            self.gear = Gear()
        if hasattr(self, "party"):
            delattr(self, "party")
        if self.__class__.__name__ != "MainCharacter" and hasattr(self, "stats"):
            delattr(self, "stats")
        if not hasattr(self, "raceTier"):
            self.raceTier = "Tier I"
        if not hasattr(self, "totalBonus") or self.totalBonus is None:
            self.totalBonus = TotalBonus(None)
        self.CalculateBonus()

    @classmethod
    def _scaled_primary_stat_multiplier(cls, value: float) -> float:
        ratio = max(0.0001, float(value) / cls.PRIMARY_STAT_BASELINE)
        return ratio ** cls.DERIVED_STAT_ALPHA

    def GetMaxHealth(self) -> float:
        physical_resistance = float(getattr(self.finalAttributes, "physicalResistance", getattr(self.attributes, "physicalResistance", 5.0)))
        return self.BASE_HEALTH_AT_BASELINE * self._scaled_primary_stat_multiplier(physical_resistance)

    def GetSpeed(self) -> float:
        physical_power = float(getattr(self.finalAttributes, "physicalPower", getattr(self.attributes, "physicalPower", 5.0)))
        magic_power = float(getattr(self.finalAttributes, "magicPower", getattr(self.attributes, "magicPower", 5.0)))
        speed = (physical_power * self.SPEED_PHYSICAL_WEIGHT) + (magic_power * self.SPEED_MAGIC_WEIGHT)
        return max(0.1, speed)

    def GetHealthRatio(self) -> float:
        max_health = max(1.0, self.GetMaxHealth())
        return max(0.0, min(1.0, float(getattr(self, "health", 0.0) or 0.0) / max_health))

    def ClampHealthToMax(self) -> float:
        self.health = max(0.0, min(float(getattr(self, "health", 0.0) or 0.0), self.GetMaxHealth()))
        return float(self.health)

    def RefreshHealthState(self) -> HealthState:
        ratio = self.GetHealthRatio()
        if float(getattr(self, "health", 0.0) or 0.0) <= 0.0:
            self.healthState = HealthState.UNCONSCIOUS
        elif ratio >= 0.76:
            self.healthState = HealthState.HEALTHY
        elif ratio >= 0.51:
            self.healthState = HealthState.INJURED
        elif ratio >= 0.26:
            self.healthState = HealthState.HEAVILY_INJURED
        else:
            self.healthState = HealthState.DYING
        return self.healthState

    def ListAllItemBonuses(self):
        allItemBonuses = []
        for item in self.gear.GetAllEquipped():
            if item is not None:
                for statBonus in item.statBonuses:
                    if statBonus is not None:
                        allItemBonuses.append(statBonus)
        return allItemBonuses

    def CheckIfList(self, items):
        for item in items:
            if isinstance(item, AttributeBonus):
                raise ValueError("********** Invalid value provided **********")

    def ListAllBonuses(self):
        allBonuses = []
        for achievement in self.achievements:
            for achievement_bonus in getattr(achievement, "bonuses", []):
                if achievement_bonus is not None:
                    allBonuses.append(achievement_bonus)
        self.CheckIfList(allBonuses)
        allBonuses += self.ListAllItemBonuses()
        self.CheckIfList(allBonuses)
        for buff in self.buffs:
            if buff.bonus is not None:
                allBonuses.append(buff.bonus)
        self.CheckIfList(allBonuses)

        return allBonuses

    # gives us our final stat block which is the base stats plus all other bonuses.
    def CalculateFinalAttributes(self):
        self.finalAttributes = copy.deepcopy(self.attributes) # reset our values to our baseline
        self.finalAffinities = copy.deepcopy(self.affinities)

        # first we add our inherent buffs (Achievements, strength training, etc.)
        self.finalAttributes.AddAttributes(self.totalBonus.flatInherentAttributes)
        # then apply our power multiplier
        self.finalAttributes.MultiplyAttributes(self.totalBonus.percentAttributes)
        # then add any final buffs from things like items, food, magic buffs, etc.
        self.finalAttributes.AddAttributes(self.totalBonus.flatBonusAttributes)

        # do affinities too
        self.finalAffinities.MultiplyAffinities(self.totalBonus.percentAffinities)


    # Updates the character's bonus object that is the combination of all the character's current bonuses (Equipment, achievements, buffs, etc.)
    def CalculateBonus(self):
        # Recompute from scratch each time to avoid stacking duplicate values across repeated calls.
        self.totalBonus = TotalBonus(None)
        self.totalBonus.ApplyAllBonuses(self.ListAllBonuses())
        self.CalculateFinalAttributes()
        if not hasattr(self, "health") or self.health is None:
            self.health = self.GetMaxHealth()



    # We want to make sure flat bonus achievements are inserted before multiplier bonus achievements.
    def AddAchievement(self, achievement: Achievement):

        if self.activeAchievementTitle == "" and achievement.title != "": # set up the title if they have none.
            self.activeAchievementTitle = achievement.title

        bonuses = [entry for entry in getattr(achievement, "bonuses", []) if entry is not None]
        has_percentage = any(entry.bonusType == BonusType.PERCENTAGE for entry in bonuses)

        if has_percentage: # percentages go at the end of the list for calculation
            self.achievements.append(achievement)
        else:
            self.achievements.insert(0, achievement) # flat bonuses go at the start of the list.

    def GetWoundedString(self):
        if self.healthState == HealthState.HEALTHY:
            return "Healthy"
        elif self.healthState == HealthState.INJURED:
            return "Injured."
        elif self.healthState == HealthState.HEAVILY_INJURED:
            return "Heavily Injured."
        elif self.healthState == HealthState.UNCONSCIOUS:
            return "Unconscious."
        elif self.healthState == HealthState.DYING:
            return "Dying."
        elif self.healthState == HealthState.DEAD:
            return "Dead."

    def GetAttributeString(self, text: str, base: float, percent: float, bonus: float, total: float):
        rounded_base = round(float(base), 1)
        rounded_total = round(float(total), 1)
        rounded_bonus = round(float(bonus), 1)

        text += f" - {rounded_base:.1f}"
        if percent > 0:
            text += f"(+{percent*100:g}%)"
        if rounded_bonus > 0:
            if rounded_bonus.is_integer():
                text += f"[+{int(rounded_bonus)}]"
            else:
                text += f"[+{rounded_bonus:.1f}]"
        if rounded_total != rounded_base:
            text += f" - {rounded_total:.1f}"
        return text

    def GetAttributesString(self):
        bonuses = self.ListAllBonuses()

        bonusAttributeDict = {
            Attribute.PHYSICAL_POWER: 0,
            Attribute.PHYSICAL_STAMINA: 0,
            Attribute.PHYSICAL_RESISTANCE: 0,
            Attribute.MAGIC_POWER: 0,
            Attribute.MAGIC_STAMINA: 0,
            Attribute.MAGIC_RESISTANCE: 0
        }

        bonusMultiplierDict = copy.deepcopy(bonusAttributeDict)

        baseStatDict = {
            Attribute.PHYSICAL_POWER: self.attributes.physicalPower,
            Attribute.PHYSICAL_STAMINA: self.attributes.physicalStamina,
            Attribute.PHYSICAL_RESISTANCE: self.attributes.physicalResistance,
            Attribute.MAGIC_POWER: self.attributes.magicPower,
            Attribute.MAGIC_STAMINA: self.attributes.magicStamina,
            Attribute.MAGIC_RESISTANCE: self.attributes.magicResistance
        }

        # Now we'll loop through bonuses and apply each bonus to its appropriate place in the dictionaries
        for bonus in bonuses:
            if bonus.bonusType == BonusType.FLAT:
                if bonus.attributeBonus is not None:
                    if not bonus.permanent: # do the bonuses that are not inherent (items, magic buffs, food, etc.)
                        if bonus.attributeBonus.attribute is not Attribute.ALL_ATTRIBUTES:
                            bonusAttributeDict[bonus.attributeBonus.attribute] += bonus.attributeBonus.bonus
                        else:
                            for attribute in bonusAttributeDict:
                                bonusAttributeDict[attribute] += bonus.attributeBonus.bonus
                    else: # do the bonuses that are considered inherent (Achievements, strength training, etc.)
                        if bonus.attributeBonus.attribute is not Attribute.ALL_ATTRIBUTES:
                            baseStatDict[bonus.attributeBonus.attribute] += bonus.attributeBonus.bonus
                        else:
                            for attribute in baseStatDict:
                                baseStatDict[attribute] += bonus.attributeBonus.bonus
            else: # if the bonus type is multiplicative
                if bonus.attributeBonus is not None:
                    percent_as_multiplier = float(bonus.attributeBonus.bonus) / 100.0
                    if bonus.attributeBonus.attribute is not Attribute.ALL_ATTRIBUTES:
                        bonusMultiplierDict[bonus.attributeBonus.attribute] += percent_as_multiplier
                    else:
                        for attribute in bonusMultiplierDict:
                            bonusMultiplierDict[attribute] += percent_as_multiplier

        # then we subtract the total bonus from the bonusMultiplierDict so that we only show stats which are not covered by the general bonus
        for attribute in bonusAttributeDict:
            bonusMultiplierDict[attribute] -= self.totalBonus.allStatBonusUIAmount

        attributeIncrease = ""
        if self.totalBonus.allStatBonusUIAmount > 0:
            attributeIncrease += f"Increased by {self.totalBonus.allStatBonusUIAmount*100:g}%"



        result = (f"Attributes - {attributeIncrease}\n"
                  f"{self.GetAttributeString('Physical Power', baseStatDict[Attribute.PHYSICAL_POWER], bonusMultiplierDict[Attribute.PHYSICAL_POWER], bonusAttributeDict[Attribute.PHYSICAL_POWER], self.finalAttributes.physicalPower)}\n"
                  f"{self.GetAttributeString('Physical Stamina', baseStatDict[Attribute.PHYSICAL_STAMINA], bonusMultiplierDict[Attribute.PHYSICAL_STAMINA], bonusAttributeDict[Attribute.PHYSICAL_STAMINA], self.finalAttributes.physicalStamina)}\n"
                  f"{self.GetAttributeString('Physical Resistance', baseStatDict[Attribute.PHYSICAL_RESISTANCE], bonusMultiplierDict[Attribute.PHYSICAL_RESISTANCE], bonusAttributeDict[Attribute.PHYSICAL_RESISTANCE], self.finalAttributes.physicalResistance)}\n"
                  f"{self.GetAttributeString('Magic Power', baseStatDict[Attribute.MAGIC_POWER], bonusMultiplierDict[Attribute.MAGIC_POWER], bonusAttributeDict[Attribute.MAGIC_POWER], self.finalAttributes.magicPower)}\n"
                  f"{self.GetAttributeString('Magic Stamina', baseStatDict[Attribute.MAGIC_STAMINA], bonusMultiplierDict[Attribute.MAGIC_STAMINA], bonusAttributeDict[Attribute.MAGIC_STAMINA], self.finalAttributes.magicStamina)}\n"
                  f"{self.GetAttributeString('Magic Resistance ', baseStatDict[Attribute.MAGIC_RESISTANCE], bonusMultiplierDict[Attribute.MAGIC_RESISTANCE], bonusAttributeDict[Attribute.MAGIC_RESISTANCE], self.finalAttributes.magicResistance)}\n")

        return result

    def GetGeneralSkillsString(self, fullDescription: bool = False):
        result = "General Skills -\n"
        if fullDescription:
            for skill in self.generalSkills:
                result += f"{skill.name} - {skill.description}\n"
        else:
            for skill in self.generalSkills:
                result += f"{skill.name}\n"
        return result

    def GetSpellsString(self, fullDescription: bool = False):
        result = ""
        if len(self.spells) > 0:
            result = "Spells -\n"

        if fullDescription:
            for spell in self.spells:
                result += f"{spell}\n"
        else:
            for spell in self.spells:
                result += f"{spell.name}\n"

        return result

    def GetCharacterOverviewText(self, nanoAmount: float):
        affinitySection = "Combat Classification - "
        if (self.level > 0):
            affinitySection += f"Level {self.level}\n"
            affinitySection += f"Chi - {self.finalAffinities.chi}\nMana - {self.finalAffinities.mana}\nPsi - {self.finalAffinities.psi}\nAether - {self.finalAffinities.aether}\n"
        else:
            affinitySection += "None\n"

        attributes = self.GetAttributesString()
        achievementString = ""
        for achievement in self.achievements:
            achievementString += f"{achievement.name}\n"
        nanoString = AbbreviateNumber(nanoAmount)
        vitals = f"Health - {float(self.health):.1f}/{self.GetMaxHealth():.1f}\nSpeed - {self.GetSpeed():.1f}"

        result = f"""
{affinitySection}
Race - {self.raceTier}

{attributes}
{vitals}

Achievements -
{achievementString}
{self.GetGeneralSkillsString()}{self.GetSpellsString()}
Pooled Nano {nanoEmoji} - {nanoString}
        """

        return result


    def IncreaseAttribute(self, a: Attribute, amount: int=1):
        self.attributes.IncreaseAttribute(a,amount)
        self.CalculateFinalAttributes()
