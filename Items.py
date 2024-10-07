from CharacterUtil import *


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

    def GetAllEquipped(self):
        allItems = [self.head, self.neck, self.body, self.hands, self.ring, self.legs, self.feet, self.primaryWeapon, self.offhand]

        return allItems

