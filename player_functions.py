import json
import pickle
from enum import Enum
from faction_functions import Faction

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

class HealthState(Enum):
    HEALTHY = 0
    INJURED = 1
    HEAVILY_INJURED = 2
    UNCONSCIOUS = 3
    DEAD = 4

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

# each value is a percentage, from 0.01 at the lowest to 0.9 at the highest.
class Affinities:
    def __init__(self, chi: float, mana: float, psi: float, aether: float):
        self.chi = chi
        self.mana = mana
        self.psi = psi
        self.aether = aether

class BonusType(Enum):
    FLAT = 0,
    PERCENTAGE = 1

# This class is presumed to work by holding only the appropriate type of bonuses. A bonus of None or 0 should be ignored.
# Flat bonus's should be applied first, then multipliers.
# if the bonus type is flat, add it. if the bonus is percentage, multiply.
class Bonus:
    def __init__(self, bonusType: BonusType, attributeBonus: AttributeBonus = None, affinities: Affinities = None, nanoMultiplier: int = 0):
        self.bonusType = bonusType
        self.attributeBonus = attributeBonus
        self.affinities = affinities
        self.nanoMultiplier = nanoMultiplier

class Achievement:
    def __init__(self, name: str, bonus: Bonus = None, title: str = ""):
        self.name = name
        self.bonus = bonus
        self.title = title


DEFAULT_DURABILITY = 100
class Item:
    def __init__(self, name: str, slot: EquipSlot = EquipSlot.NOT_EQUIPABLE, tier: int = 0,
                 durability: int = DEFAULT_DURABILITY, statBonus: list[AttributeBonus] = None,
                 itemType: ItemType = ItemType.DEFAULT, itemPower: list[ItemPower] = None, damageType: list[DamageType] = None):
        self.name = name
        self.slot = slot
        self.tier = tier
        self.durability = durability
        self.statBonus = statBonus if statBonus is not None else []
        self.itemType = itemType
        self.itemPower = itemPower if itemType is not None else []
        self.damageType = damageType if damageType is not None else []
        damageTypeTags = ","
        if damageType and len(damageType) > 0:
            damageTypeTags += ",".join([e.name for e in damageType])
        else:
            damageTypeTags = ""
        self.tags = name + "," + itemType.name + "," + slot.name + damageTypeTags


class Gear:
    def __init__(self, head: Item = None, neck: Item = None, body: Item = None, hands: Item = None, ring: Item = None, legs: Item = None, feet: Item = None, primaryWeapon: Item = None, offhand: Item = None, inventory: list[Item] = None):
        self.head = head
        self.neck = neck
        self.body = body
        self.hands = hands
        self.ring = ring
        self.legs = legs
        self.feet = feet
        self.primaryWeapon = primaryWeapon
        self.offhand = offhand
        self.inventory = inventory if inventory is not None else [] # Imagine 1-4 items you can carry extra, such as back up weapons, potions, bombs, tools, etc.

# general skills is fake for now...
class Character:
    def __init__(self, name: str, attributes: Attributes, level:  int = 0, raceTier: str = "Tier I", combatClass: str = "None", gear: Gear = None, achievements=None, generalSkills: str = "", party: int = 0):
        self.name = name
        self.attributes = attributes
        self.level = level
        self.raceTier = raceTier
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




class Player:
    def __init__(self, discord_id: int, nano: int = 0, chronos: int = 0, titlePreference: TitlePreference = TitlePreference.Masculine, characters=None, faction: Faction = None):
        self.discordID = discord_id  # Discord user ID
        self.playerName = "PlayerName" # will be filled in immediately after player creation/loading.
        self.nano = nano  # Placeholder for player's 'nano' currency or points
        self.chronos = chronos  # Placeholder for player's 'chronos' currency or points
        self.titlePreference = titlePreference # use the Enum TitlePreference.Masculine or TitlePreference.Feminine
        self.characters = characters if characters is not None else []  # List of character objects
        self.faction = faction
        self.achievementTitle = ""
        self.isNewPlayer = False
        self.partyNames = ["Delta Team", "2", "3", "4"] # It would be cool to be able to name parties. "Foxtrot" "Demons" "Delta Team"

    def GetCharacterText(self):
        cString = ""
        for character in self.characters:
            cString = "**" + character.name + "** │ LvL " + str(character.level) + " │ (" + character.GetWoundedString() + ") │ Party: " + self.partyNames[character.party] + "\n"
        return cString

    def GetCharacterName(self, characterIndex: int):
        if len(self.characters) > characterIndex:
            return self.characters[characterIndex].name
        else:
            return ""

    def GetCharacterLevel(self, characterIndex: int):
        if len(self.characters) > characterIndex:
            return self.characters[characterIndex].level
        else:
            return ""

    def GetCharacterParty(self, characterIndex: int):
        if len(self.characters) > characterIndex:
            return self.partyNames[self.characters[characterIndex].party]
        else:
            return ""

    # Returns the requested character index. If no such index exists, return the last character in the list.
    def GetCharacter(self, index: int):
        if len(self.characters) > index:
            return self.characters[index]
        else:
            return self.characters[len(self.characters)-1]




def save_player(player: Player, filename: str):
    with open(filename, 'wb') as file:
        pickle.dump(player, file)

def load_player(filename: str) -> Player:
    with open(filename, 'rb') as file:
        return pickle.load(file)
