from typing import Any

from src.domain.CharacterUtil import *


class Item:
    statBonuses: list[Bonus]

    def __init__(
        self,
        name: str,
        slot: EquipSlot = EquipSlot.NOT_EQUIPABLE,
        tier: int = 0,
        durability: int = DEFAULT_DURABILITY,
        statBonuses: list[Bonus] = None,
        itemType: ItemType = ItemType.DEFAULT,
        itemPower: list[ItemPower] = None,
        damageType: list[DamageType] = None,
        itemId: str | None = None,
    ):
        self.name = name
        self.itemId = str(itemId or "").strip()
        self.slot = slot
        self.tier = tier
        self.durability = durability
        self.statBonuses = statBonuses if statBonuses is not None else []
        for bonus in self.statBonuses:
            if bonus.reason == "":
                bonus.reason = self.name
        self.itemType = itemType
        self.itemPower = itemPower if itemPower is not None else []
        self.damageType = damageType if damageType is not None else []
        self.tags = [self.name, self.itemType.name, self.slot.name]
        if self.itemId:
            self.tags.append(self.itemId)
        self.tags.extend([damage_type.name for damage_type in self.damageType])

    @staticmethod
    def _enum_from_name(enum_type, value: Any, default):
        if isinstance(value, enum_type):
            return value
        if isinstance(value, str):
            normalized = value.strip().upper()
            if normalized in enum_type.__members__:
                return enum_type[normalized]
        return default

    @classmethod
    def _item_power_from_dict(cls, data: dict[str, Any]) -> ItemPower | None:
        if not isinstance(data, dict):
            return None

        power_type = cls._enum_from_name(PowerType, data.get("powerType"), PowerType.PHYSICAL_ATTACK)
        try:
            power_value = int(data.get("power", 0))
        except Exception:
            power_value = 0

        spell_name = str(data.get("spellName", "")).strip()
        return ItemPower(powerType=power_type, power=power_value, spellName=spell_name)

    @staticmethod
    def _item_power_to_dict(item_power: ItemPower) -> dict[str, Any]:
        return {
            "powerType": item_power.powerType.name,
            "power": int(item_power.power),
            "spellName": item_power.spellName,
        }

    @classmethod
    def _damage_type_from_list(cls, value: Any) -> list[DamageType]:
        if not isinstance(value, list):
            return []

        result = []
        for item in value:
            parsed = cls._enum_from_name(DamageType, item, None)
            if parsed is not None:
                result.append(parsed)
        return result

    @classmethod
    def _bonus_from_dict(cls, data: dict[str, Any]) -> Bonus | None:
        if not isinstance(data, dict):
            return None

        bonus_type = cls._enum_from_name(BonusType, data.get("bonusType"), BonusType.FLAT)
        reason = str(data.get("reason", "")).strip()
        permanent = bool(data.get("permanent", False))
        nano_multiplier = float(data.get("nanoMultiplier", 0) or 0)

        attribute_bonus_data = data.get("attributeBonus")
        attribute_bonus = None
        if isinstance(attribute_bonus_data, dict):
            attr = cls._enum_from_name(Attribute, attribute_bonus_data.get("attribute"), None)
            if attr is not None:
                try:
                    bonus_amount = int(attribute_bonus_data.get("bonus", 0))
                except Exception:
                    bonus_amount = 0
                attribute_bonus = AttributeBonus(attribute=attr, bonus=bonus_amount)

        affinities_data = data.get("affinities")
        affinities = None
        if isinstance(affinities_data, dict):
            affinities = Affinities(
                chi=float(affinities_data.get("chi", 0) or 0),
                mana=float(affinities_data.get("mana", 0) or 0),
                psi=float(affinities_data.get("psi", 0) or 0),
                aether=float(affinities_data.get("aether", 0) or 0),
            )

        return Bonus(
            bonusType=bonus_type,
            attributeBonus=attribute_bonus,
            affinities=affinities,
            nanoMultiplier=nano_multiplier,
            reason=reason,
            permanent=permanent,
        )

    @staticmethod
    def _bonus_to_dict(bonus: Bonus) -> dict[str, Any]:
        result = {
            "bonusType": bonus.bonusType.name,
            "attributeBonus": None,
            "affinities": None,
            "nanoMultiplier": float(bonus.nanoMultiplier),
            "reason": bonus.reason,
            "permanent": bool(bonus.permanent),
        }

        if bonus.attributeBonus is not None:
            result["attributeBonus"] = {
                "attribute": bonus.attributeBonus.attribute.name,
                "bonus": int(bonus.attributeBonus.bonus),
            }

        if bonus.affinities is not None:
            result["affinities"] = {
                "chi": float(bonus.affinities.chi),
                "mana": float(bonus.affinities.mana),
                "psi": float(bonus.affinities.psi),
                "aether": float(bonus.affinities.aether),
            }

        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "itemId": self.itemId,
            "name": self.name,
            "slot": self.slot.name,
            "tier": int(self.tier),
            "durability": int(self.durability),
            "statBonuses": [self._bonus_to_dict(bonus) for bonus in self.statBonuses],
            "itemType": self.itemType.name,
            "itemPower": [self._item_power_to_dict(power) for power in self.itemPower],
            "damageType": [damage_type.name for damage_type in self.damageType],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Item":
        name = str(data.get("name", "")).strip()
        if not name:
            raise ValueError("Item data must include a non-empty 'name'.")

        slot = cls._enum_from_name(EquipSlot, data.get("slot"), EquipSlot.NOT_EQUIPABLE)
        item_type = cls._enum_from_name(ItemType, data.get("itemType"), ItemType.DEFAULT)
        item_id = str(data.get("itemId", data.get("itemID", "")) or "").strip()

        try:
            tier = int(data.get("tier", 0))
        except Exception:
            tier = 0

        try:
            durability = int(data.get("durability", DEFAULT_DURABILITY))
        except Exception:
            durability = DEFAULT_DURABILITY

        raw_powers = data.get("itemPower", [])
        item_power = []
        if isinstance(raw_powers, list):
            for raw in raw_powers:
                parsed = cls._item_power_from_dict(raw)
                if parsed is not None:
                    item_power.append(parsed)

        raw_bonuses = data.get("statBonuses", [])
        stat_bonuses = []
        if isinstance(raw_bonuses, list):
            for raw in raw_bonuses:
                parsed = cls._bonus_from_dict(raw)
                if parsed is not None:
                    stat_bonuses.append(parsed)

        damage_type = cls._damage_type_from_list(data.get("damageType", []))

        return cls(
            name=name,
            slot=slot,
            tier=tier,
            durability=durability,
            statBonuses=stat_bonuses,
            itemType=item_type,
            itemPower=item_power,
            damageType=damage_type,
            itemId=item_id,
        )


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

    def GetAllEquipped(self) -> list[Item]:
        allItems = [item for item in [self.head, self.neck, self.body, self.hands, self.ring, self.legs, self.feet, self.primaryWeapon, self.offhand] if item is not None]

        return allItems
