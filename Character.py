import copy

from attr import attributes

from CharacterUtil import *
from Items import Gear

class HealthState(Enum):
    HEALTHY = 0
    INJURED = 1
    HEAVILY_INJURED = 2
    UNCONSCIOUS = 3
    DEAD = 4

# A limited time bonus that the character has active.
class Buff:
    def __init__(self, bonus: Bonus, duration: int):
        self.bonus = bonus
        self.duration = duration

    # Returns true if there is any time left. Returns false if the bonus is now expired.
    def DecrementTime(self, amount: int = 1):
        self.duration -= amount
        return self.duration > 0

# general skills is fake for now...
class Character:
    finalAttributes: Attributes
    finalAffinities: Affinities
    def __init__(self, name: str, attributes: Attributes, level:  int = 0, raceTier: str = "Tier I",
                 affinities: Affinities = None, combatClass: str = "None", gear: Gear = None,
                 achievements=None, generalSkills: str = "", party: int = 0, buffs: list[Buff] = None):
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
        self.generalSkills = generalSkills
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
            allItemBonuses.append(item.statBonus)
        return allItemBonuses

    def ListAllBonuses(self):
        allBonuses = []
        for achievement in self.achievements:
            allBonuses.append(achievement.bonus)
        allBonuses.append(self.ListAllItemBonuses())
        for buff in self.buffs:
            allBonuses.append(buff.bonus)

        return allBonuses

    # gives us our final stat block which is the base stats plus all other bonuses.
    def CalculateFinalAttributes(self):
        self.finalAttributes.physicalPower += self.totalBonus.flatAttributes.physicalPower
        self.finalAttributes.physicalPower *= ( 1 + self.totalBonus.percentAttributes.physicalPower )

        self.finalAttributes.physicalStamina += self.totalBonus.flatAttributes.physicalStamina
        self.finalAttributes.physicalStamina *= ( 1 + self.totalBonus.percentAttributes.physicalStamina )

        self.
        # add affinities too

    # Updates the character's bonus object that is the combination of all the character's current bonuses (Equipment, achievements, buffs, etc.)
    def CalculateBonus(self):
        self.totalBonus.ApplyAllBonuses(self.ListAllBonuses())



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
            return "Dead 💀"

    def GetAttributesString(self):
        result = ""
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

        # Now we'll loop through bonuses and apply each one to its appropriate place in the attributeBonusDict
        for bonus in bonuses:
            if bonus.bonusType == BonusType.FLAT:
                if bonus.attributeBonus is not None:
                    if bonus.attributeBonus.attribute is not Attribute.ALL_ATTRIBUTES:
                        bonusAttributeDict[bonus.attributeBonus.attribute] += bonus.attributeBonus.bonus
                    else:
                        for attribute in bonusAttributeDict:
                            bonusAttributeDict[attribute] += bonus.attributeBonus.bonus

        physBonus = ""
        if bonusAttributeDict[Attribute.PHYSICAL_POWER] > 0:


        result = f"Physical Power - {self.attributes.physicalPower}{physBonus}"



    def GetCharacterInfoText(self):
        affinitySection = f"    Chi - {self.affinities.chi}\n   Mana - {self.affinities.mana}\n Psi - {self.affinities.psi}\n   Aether - {self.affinities.aether}\n"
        attributeIncrease = ""
        if self.totalBonus.allStatBonusUIAmount > 0:
            attributeIncrease += f"Increased by {self.totalBonus.allStatBonusUIAmount*100}%"
        achievementString = ""
        for achievement in self.achievements:
            achievementString += f"{achievement.name}\n"



        f"""
Combat Classification - {self.combatClass}

{affinitySection}

Race - {self.raceTier}

Attributes - {attributeIncrease}
Attributes -
    Physical Power - $physicalPower
    Physical Stamina - $physicalStamina
    Physical Resistance - $physicalResistance
    Magic Power - $magicPower
    Magic Stamina - $magicStamina
    Magic Resistance - $magicResistance

Achievements -
{achievementString}

General Skills -
$generalSkills

Pooled Nano :Nano~1: - 10000
        :return:
        """