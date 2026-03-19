from __future__ import annotations

from typing import Any

from src.domain.CharacterUtil import (
    Bonus,
    ConsumableKind,
    DamageType,
    DEFAULT_DURABILITY,
    EquipSlot,
    ItemPower,
    ItemType,
    PowerType,
)
from src.domain.item_core import Item
from src.domain.item_support import WEAPON_ITEM_TYPES, _serialize_number


class Weapon(Item):
    def __init__(
        self,
        name: str,
        slot: EquipSlot = EquipSlot.PRIMARY_WEAPON,
        tier: int = 0,
        durability: float = DEFAULT_DURABILITY,
        statBonuses: list[Bonus] | None = None,
        itemType: ItemType = ItemType.MELEE_WEAPON,
        damageType: list[DamageType] | None = None,
        damageMin: float = 0.0,
        damageMax: float | None = None,
        armorMultiplier: float = 1.0,
        ignoreArmorFraction: float = 0.0,
        penetrationBase: float = 0.0,
        staminaCost: float = 10.0,
        itemId: str | None = None,
        powerLevel: float = 0.0,
    ):
        normalized_type = itemType if itemType in WEAPON_ITEM_TYPES else ItemType.MELEE_WEAPON
        super().__init__(
            name=name,
            slot=self._normalize_weapon_slot(slot),
            tier=tier,
            durability=durability,
            statBonuses=statBonuses,
            itemType=normalized_type,
            itemId=itemId,
            powerLevel=powerLevel,
        )
        self.damageType = self._damage_type_from_list(damageType or [])
        self.damageMin = float(damageMin or 0.0)
        self.damageMax = float(self.damageMin if damageMax is None else damageMax)
        self.armorMultiplier = float(armorMultiplier)
        self.ignoreArmorFraction = max(0.0, min(1.0, float(ignoreArmorFraction)))
        self.penetrationBase = max(0.0, float(penetrationBase))
        self.staminaCost = max(0.0, float(staminaCost))
        representative_power = int(round(max(self.damageMin, self.damageMax, 0.0)))
        self.itemPower = [ItemPower(PowerType.PHYSICAL_ATTACK, representative_power)] if representative_power > 0 else []
        self.refresh_tags()

    @staticmethod
    def _normalize_weapon_slot(value: Any) -> EquipSlot:
        slot = Item._enum_from_name(EquipSlot, value, EquipSlot.PRIMARY_WEAPON)
        if slot in {EquipSlot.PRIMARY_WEAPON, EquipSlot.OFFHAND}:
            return slot
        if slot == EquipSlot.HANDS:
            return EquipSlot.PRIMARY_WEAPON
        return EquipSlot.PRIMARY_WEAPON

    @property
    def isRanged(self) -> bool:
        return self.itemType == ItemType.RANGED_WEAPON

    def refresh_tags(self):
        self._rebuild_tags([damage_type.name for damage_type in self.damageType])

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "weaponStats": {
                    "damageTypes": [damage_type.name for damage_type in self.damageType],
                    "damageMin": _serialize_number(self.damageMin),
                    "damageMax": _serialize_number(self.damageMax),
                    "armorMultiplier": float(self.armorMultiplier),
                    "ignoreArmorFraction": float(self.ignoreArmorFraction),
                    "penetrationBase": float(self.penetrationBase),
                    "staminaCost": float(self.staminaCost),
                },
                "damageType": [damage_type.name for damage_type in self.damageType],
                "damageMin": _serialize_number(self.damageMin),
                "damageMax": _serialize_number(self.damageMax),
                "armorMultiplier": float(self.armorMultiplier),
                "ignoreArmorFraction": float(self.ignoreArmorFraction),
                "penetrationBase": float(self.penetrationBase),
                "staminaCost": float(self.staminaCost),
            }
        )
        return payload

    @classmethod
    def _from_dict_internal(cls, data: dict[str, Any], common: dict[str, Any]) -> "Weapon":
        weapon_stats = data.get("weaponStats") if isinstance(data.get("weaponStats"), dict) else {}
        raw_power = cls._parse_item_power_list(data.get("itemPower", []))
        fallback_damage = float(raw_power[0].power) if raw_power else 0.0
        return cls(
            name=common["name"],
            slot=common["slot"],
            tier=common["tier"],
            durability=common["durability"],
            statBonuses=common["statBonuses"],
            itemType=common["itemType"],
            damageType=cls._damage_type_from_list(weapon_stats.get("damageTypes", data.get("damageType", []))),
            damageMin=cls._coerce_float(weapon_stats.get("damageMin", data.get("damageMin", fallback_damage)), fallback_damage),
            damageMax=cls._coerce_float(weapon_stats.get("damageMax", data.get("damageMax", fallback_damage)), fallback_damage),
            armorMultiplier=cls._coerce_float(weapon_stats.get("armorMultiplier", data.get("armorMultiplier", 1.0)), 1.0),
            ignoreArmorFraction=cls._coerce_float(weapon_stats.get("ignoreArmorFraction", data.get("ignoreArmorFraction", 0.0)), 0.0),
            penetrationBase=cls._coerce_float(weapon_stats.get("penetrationBase", data.get("penetrationBase", 0.0)), 0.0),
            staminaCost=cls._coerce_float(weapon_stats.get("staminaCost", data.get("staminaCost", 10.0)), 10.0),
            itemId=common["itemId"],
            powerLevel=common["powerLevel"],
        )


class Armor(Item):
    def __init__(
        self,
        name: str,
        slot: EquipSlot = EquipSlot.BODY,
        tier: int = 0,
        durability: float = DEFAULT_DURABILITY,
        statBonuses: list[Bonus] | None = None,
        itemType: ItemType = ItemType.ARMOR,
        maxArmor: float | None = None,
        currentArmor: float | None = None,
        itemId: str | None = None,
        powerLevel: float = 0.0,
    ):
        effective_current = float(durability if currentArmor is None else currentArmor)
        effective_max = float(effective_current if maxArmor is None else maxArmor)
        effective_max = max(0.0, effective_max)
        effective_current = max(0.0, min(effective_max, effective_current))
        super().__init__(
            name=name,
            slot=self._normalize_armor_slot(slot),
            tier=tier,
            durability=effective_current,
            statBonuses=statBonuses,
            itemType=itemType,
            itemId=itemId,
            powerLevel=powerLevel,
        )
        self.itemType = ItemType.ARMOR
        self.maxArmor = effective_max
        self.itemPower = []
        self.damageType = []
        self.refresh_tags()

    @staticmethod
    def _normalize_armor_slot(value: Any) -> EquipSlot:
        slot = Item._enum_from_name(EquipSlot, value, EquipSlot.BODY)
        if slot == EquipSlot.PRIMARY_WEAPON:
            return EquipSlot.OFFHAND
        return slot

    @property
    def currentArmor(self) -> float:
        return float(self.durability)

    @currentArmor.setter
    def currentArmor(self, value: float):
        self.durability = max(0.0, min(float(self.maxArmor), float(value)))

    def refresh_tags(self):
        self._rebuild_tags(["ARMOR"])

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "armorStats": {
                    "maxArmor": _serialize_number(self.maxArmor),
                    "currentArmor": _serialize_number(self.currentArmor),
                },
                "maxArmor": _serialize_number(self.maxArmor),
                "currentArmor": _serialize_number(self.currentArmor),
                "durability": _serialize_number(self.currentArmor),
            }
        )
        return payload

    @classmethod
    def _from_dict_internal(cls, data: dict[str, Any], common: dict[str, Any]) -> "Armor":
        armor_stats = data.get("armorStats") if isinstance(data.get("armorStats"), dict) else {}
        current_armor = cls._coerce_float(armor_stats.get("currentArmor", data.get("currentArmor", common["durability"])), common["durability"])
        max_armor = cls._coerce_float(armor_stats.get("maxArmor", data.get("maxArmor", common["durability"])), common["durability"])
        return cls(
            name=common["name"],
            slot=common["slot"],
            tier=common["tier"],
            durability=current_armor,
            statBonuses=common["statBonuses"],
            itemType=common["itemType"],
            maxArmor=max_armor,
            currentArmor=current_armor,
            itemId=common["itemId"],
            powerLevel=common["powerLevel"],
        )


class Consumable(Item):
    def __init__(
        self,
        name: str,
        tier: int = 0,
        statBonuses: list[Bonus] | None = None,
        consumableKind: ConsumableKind = ConsumableKind.NONE,
        effectPowerType: PowerType = PowerType.CONSUMABLE_POWER,
        effectPower: float = 0.0,
        spellName: str = "",
        damageType: list[DamageType] | None = None,
        itemId: str | None = None,
        powerLevel: float = 0.0,
    ):
        super().__init__(
            name=name,
            slot=EquipSlot.NOT_EQUIPABLE,
            tier=tier,
            durability=1.0,
            statBonuses=statBonuses,
            itemType=ItemType.CONSUMABLE,
            itemId=itemId,
            powerLevel=powerLevel,
        )
        self.consumableKind = self._enum_from_name(ConsumableKind, consumableKind, ConsumableKind.NONE)
        self.effectPowerType = self._enum_from_name(PowerType, effectPowerType, PowerType.CONSUMABLE_POWER)
        self.effectPower = float(effectPower or 0.0)
        self.spellName = str(spellName or "").strip()
        self.damageType = self._damage_type_from_list(damageType or [])
        self.itemPower = [ItemPower(self.effectPowerType, int(round(self.effectPower)), self.spellName)]
        self.refresh_tags()

    @property
    def isOffensive(self) -> bool:
        return bool(self.damageType)

    def refresh_tags(self):
        self._rebuild_tags([self.consumableKind.name] + [damage_type.name for damage_type in self.damageType])

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload.update(
            {
                "consumableStats": {
                    "consumableKind": self.consumableKind.name,
                    "effectPowerType": self.effectPowerType.name,
                    "effectPower": _serialize_number(self.effectPower),
                    "spellName": self.spellName,
                    "damageTypes": [damage_type.name for damage_type in self.damageType],
                },
                "consumableKind": self.consumableKind.name,
                "itemPower": [self._item_power_to_dict(power) for power in self.itemPower],
                "damageType": [damage_type.name for damage_type in self.damageType],
            }
        )
        return payload

    @classmethod
    def _from_dict_internal(cls, data: dict[str, Any], common: dict[str, Any]) -> "Consumable":
        consumable_stats = data.get("consumableStats") if isinstance(data.get("consumableStats"), dict) else {}
        raw_power = cls._parse_item_power_list(data.get("itemPower", []))
        first_power = raw_power[0] if raw_power else ItemPower(PowerType.CONSUMABLE_POWER, 0, "")
        return cls(
            name=common["name"],
            tier=common["tier"],
            statBonuses=common["statBonuses"],
            consumableKind=consumable_stats.get("consumableKind", data.get("consumableKind", ConsumableKind.NONE.name)),
            effectPowerType=consumable_stats.get("effectPowerType", getattr(first_power, "powerType", PowerType.CONSUMABLE_POWER)),
            effectPower=consumable_stats.get("effectPower", getattr(first_power, "power", 0)),
            spellName=consumable_stats.get("spellName", getattr(first_power, "spellName", "")),
            damageType=consumable_stats.get("damageTypes", data.get("damageType", [])),
            itemId=common["itemId"],
            powerLevel=common["powerLevel"],
        )
