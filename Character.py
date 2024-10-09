import copy
from attr import attributes
from CharacterUtil import *
from Items import Gear, Item
from GeneralSkills import GeneralSkills
from Spells import Spell, SpellComponent
from Globals import *

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
    finalAttributes: Attributes
    finalAffinities: Affinities
    achievements: list[Achievement]
    spells: list[Spell]
    buffs: list[Buff]
    portraitURL: str
    footerImageURL: str

    def __init__(self, name: str, attributes: Attributes, level:  int = 0, raceTier: str = "Tier I",
                 affinities: Affinities = None, combatClass: str = "None", gear: Gear = None,
                 achievements=list[Achievement], generalSkills: list[GeneralSkills] = None, spells: list[Spell] = None, party: int = 0, buffs: list[Buff] = None):
        self.name = name
        self.attributes = attributes
        self.level = level
        self.raceTier = raceTier
        self.affinities = affinities
        self.combatClass = combatClass
        self.gear = gear
        self.activeAchievementTitle = ""
        self.achievements = []
        if achievements is not None:
            if not isinstance(achievements, list):
                achievements = [achievements]  # Convert to list if it's not already one

            for achievement in achievements:
                self.AddAchievement(achievement)
        self.generalSkills = []
        if generalSkills is not None:
            self.generalSkills = generalSkills
        self.spells = []
        if spells is not None:
            self.spells = spells
        self.party = party
        self.health = 100
        self.healthState = HealthState.HEALTHY
        self.buffs = []
        if buffs is not None:
            self.buffs = buffs
        self.totalBonus = TotalBonus(None)
        self.finalAttributes = copy.deepcopy(attributes)
        self.finalAffinities = copy.deepcopy(affinities)
        self.CalculateBonus()

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
            if achievement.bonus is not None:
                allBonuses.append(achievement.bonus)
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
        self.totalBonus.ApplyAllBonuses(self.ListAllBonuses())
        self.CalculateFinalAttributes()



    # We want to make sure flat bonus achievements are inserted before multiplier bonus achievements.
    def AddAchievement(self, achievement: Achievement):

        if self.activeAchievementTitle == "" and achievement.title != "": # set up the title if they have none.
            self.activeAchievementTitle = achievement.title

        if achievement.bonus.bonusType == BonusType.PERCENTAGE: # percentages go at the end of the list for calculation
            self.achievements.append(achievement)
        else:
            self.achievements.insert(0, achievement) # flat bonuses go at the start of the list.

    def GetWoundedString(self):
        if self.healthState == HealthState.HEALTHY:
            return "Healthy"
        elif self.healthState == HealthState.INJURED:
            return "Injured 🩸"
        elif self.healthState == HealthState.HEAVILY_INJURED:
            return "Heavily Injured 🩸🩸"
        elif self.healthState == HealthState.UNCONSCIOUS:
            return "Unconscious 😵‍💫"
        elif self.healthState == HealthState.DEAD:
            return "Dying ⌛"
        elif self.healthState == HealthState.DEAD:
            return "Dead 💀"

    def GetAttributeString(self, text: str, base: float, percent: float, bonus: float, total: float):
        text += " - " + str(base)
        if percent > 0:
            text += f"(+{percent*100}%)"
        if bonus > 0:
            text += f"[+{bonus}]"
        if total != base:
            text += f" - {total}"
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
                    if bonus.attributeBonus.attribute is not Attribute.ALL_ATTRIBUTES:
                        bonusMultiplierDict[bonus.attributeBonus.attribute] += bonus.attributeBonus.bonus
                    else:
                        for attribute in bonusMultiplierDict:
                            bonusMultiplierDict[attribute] += bonus.attributeBonus.bonus

        # then we subtract the total bonus from the bonusMultiplierDict so that we only show stats which are not covered by the general bonus
        for attribute in bonusAttributeDict:
            bonusMultiplierDict[attribute] -= self.totalBonus.allStatBonusUIAmount

        attributeIncrease = ""
        if self.totalBonus.allStatBonusUIAmount > 0:
            attributeIncrease += f"Increased by {self.totalBonus.allStatBonusUIAmount*100}%"



        result = (f"Attributes - {attributeIncrease}\n"
                  f"{self.GetAttributeString('　Physical Power', baseStatDict[Attribute.PHYSICAL_POWER], bonusMultiplierDict[Attribute.PHYSICAL_POWER], bonusAttributeDict[Attribute.PHYSICAL_POWER], self.finalAttributes.physicalPower)}\n"
                  f"{self.GetAttributeString('　Physical Stamina', baseStatDict[Attribute.PHYSICAL_STAMINA], bonusMultiplierDict[Attribute.PHYSICAL_STAMINA], bonusAttributeDict[Attribute.PHYSICAL_STAMINA], self.finalAttributes.physicalStamina)}\n"
                  f"{self.GetAttributeString('　Physical Resistance', baseStatDict[Attribute.PHYSICAL_RESISTANCE], bonusMultiplierDict[Attribute.PHYSICAL_RESISTANCE], bonusAttributeDict[Attribute.PHYSICAL_RESISTANCE], self.finalAttributes.physicalResistance)}\n"
                  f"{self.GetAttributeString('　Magic Power', baseStatDict[Attribute.MAGIC_POWER], bonusMultiplierDict[Attribute.MAGIC_POWER], bonusAttributeDict[Attribute.MAGIC_POWER], self.finalAttributes.magicPower)}\n"
                  f"{self.GetAttributeString('　Magic Stamina', baseStatDict[Attribute.MAGIC_STAMINA], bonusMultiplierDict[Attribute.MAGIC_STAMINA], bonusAttributeDict[Attribute.MAGIC_STAMINA], self.finalAttributes.magicStamina)}\n"
                  f"{self.GetAttributeString('　Magic Resistance ', baseStatDict[Attribute.MAGIC_RESISTANCE], bonusMultiplierDict[Attribute.MAGIC_RESISTANCE], bonusAttributeDict[Attribute.MAGIC_RESISTANCE], self.finalAttributes.magicResistance)}\n")

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
            affinitySection += f"　Chi - {self.finalAffinities.chi}\n　Mana - {self.finalAffinities.mana}\n　Psi - {self.finalAffinities.psi}\n　Aether - {self.finalAffinities.aether}\n"
        else:
            affinitySection += "None\n"

        attributes = self.GetAttributesString()
        achievementString = ""
        for achievement in self.achievements:
            achievementString += f"　{achievement.name}\n"
        nanoString = AbbreviateNumber(nanoAmount)

        result = f"""
{affinitySection}
Race - {self.raceTier}

{attributes}
Achievements -
{achievementString}
{self.GetGeneralSkillsString()}{self.GetSpellsString()}
Pooled Nano {nanoEmoji} - {nanoString}
        """

        return result


    def IncreaseAttribute(self, a: Attribute, amount: int=1):
        self.attributes.IncreaseAttribute(a,amount)













