from __future__ import annotations

from typing import Any

from src.domain.CharacterUtil import (
    Affinities,
    Attribute,
    AttributeBonus,
    Bonus,
    BonusType,
    ConsumableKind,
    DamageType,
    DEFAULT_DURABILITY,
    EquipSlot,
    HitLocation,
    ItemPower,
    ItemType,
    PowerType,
)


WEAPON_ITEM_TYPES = {
    ItemType.MELEE_WEAPON,
    ItemType.MELEE_THROWABLE,
    ItemType.RANGED_WEAPON,
}


def _serialize_number(value: float | int) -> float | int:
    numeric = float(value)
    if numeric.is_integer():
        return int(numeric)
    return numeric


def _unique_strings(values: list[str]) -> list[str]:
    result = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result


class Item:
    statBonuses: list[Bonus]

    def __init__(
        self,
        name: str,
        slot: EquipSlot = EquipSlot.NOT_EQUIPABLE,
        tier: int = 0,
        durability: float = DEFAULT_DURABILITY,
        statBonuses: list[Bonus] | None = None,
        itemType: ItemType = ItemType.DEFAULT,
        itemId: str | None = None,
        powerLevel: float = 0.0,
    ):
        self.name = str(name or "")
        self.itemId = str(itemId or "").strip()
        self.slot = self._enum_from_name(EquipSlot, slot, EquipSlot.NOT_EQUIPABLE)
        self.tier = self._coerce_int(tier, 0)
        self.durability = float(durability if durability is not None else DEFAULT_DURABILITY)
        self.statBonuses = self._normalize_bonuses(statBonuses)
        self.itemType = self._enum_from_name(ItemType, itemType, ItemType.DEFAULT)
        self.powerLevel = float(powerLevel or 0.0)
        self.itemPower: list[ItemPower] = []
        self.damageType: list[DamageType] = []
        self.tags: list[str] = []
        self._apply_default_bonus_reasons()
        self._rebuild_tags()

    @property
    def itemClass(self) -> str:
        return type(self).__name__

    @property
    def isEquippable(self) -> bool:
        return self.slot != EquipSlot.NOT_EQUIPABLE

    def can_equip_in(self, slot: EquipSlot) -> bool:
        target = self._enum_from_name(EquipSlot, slot, EquipSlot.NOT_EQUIPABLE)
        return self.isEquippable and self.slot == target

    def _apply_default_bonus_reasons(self):
        for bonus in self.statBonuses:
            if getattr(bonus, "reason", "") == "":
                bonus.reason = self.name

    def _rebuild_tags(self, extra_tags: list[str] | None = None):
        tags = [self.name, self.itemType.name, self.slot.name, self.itemClass]
        if self.itemId:
            tags.append(self.itemId)
        if extra_tags:
            tags.extend(str(getattr(tag, "name", tag) or "").strip() for tag in extra_tags)
        self.tags = _unique_strings(tags)

    def refresh_tags(self):
        self._rebuild_tags()

    @staticmethod
    def _coerce_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except Exception:
            return default

    @staticmethod
    def _coerce_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default

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
    def _normalize_bonuses(cls, values: list[Bonus] | None) -> list[Bonus]:
        if not isinstance(values, list):
            return []
        return [bonus for bonus in values if isinstance(bonus, Bonus)]

    @classmethod
    def _item_power_from_dict(cls, data: dict[str, Any]) -> ItemPower | None:
        if not isinstance(data, dict):
            return None

        power_type = cls._enum_from_name(PowerType, data.get("powerType"), PowerType.PHYSICAL_ATTACK)
        power_value = cls._coerce_int(data.get("power", 0), 0)
        spell_name = str(data.get("spellName", "") or "").strip()
        return ItemPower(powerType=power_type, power=power_value, spellName=spell_name)

    @staticmethod
    def _item_power_to_dict(item_power: ItemPower) -> dict[str, Any]:
        return {
            "powerType": item_power.powerType.name,
            "power": int(item_power.power),
            "spellName": item_power.spellName,
        }

    @classmethod
    def _parse_item_power_list(cls, raw_value: Any) -> list[ItemPower]:
        if not isinstance(raw_value, list):
            return []
        result = []
        for raw_entry in raw_value:
            parsed = cls._item_power_from_dict(raw_entry)
            if parsed is not None:
                result.append(parsed)
        return result

    @classmethod
    def _damage_type_from_list(cls, value: Any) -> list[DamageType]:
        if not isinstance(value, list):
            return []

        result = []
        for item in value:
            parsed = cls._enum_from_name(DamageType, item, None)
            if parsed is not None and parsed not in result:
                result.append(parsed)
        return result

    @classmethod
    def _bonus_from_dict(cls, data: dict[str, Any]) -> Bonus | None:
        if not isinstance(data, dict):
            return None

        bonus_type = cls._enum_from_name(BonusType, data.get("bonusType"), BonusType.FLAT)
        reason = str(data.get("reason", "") or "").strip()
        permanent = bool(data.get("permanent", False))
        nano_multiplier = float(data.get("nanoMultiplier", 0) or 0)

        attribute_bonus_data = data.get("attributeBonus")
        attribute_bonus = None
        if isinstance(attribute_bonus_data, dict):
            attr = cls._enum_from_name(Attribute, attribute_bonus_data.get("attribute"), None)
            if attr is not None:
                bonus_amount = cls._coerce_int(attribute_bonus_data.get("bonus", 0), 0)
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

    @classmethod
    def _common_payload_from_dict(cls, data: dict[str, Any]) -> dict[str, Any]:
        name = str(data.get("name", "") or "").strip()
        if not name:
            raise ValueError("Item data must include a non-empty 'name'.")

        slot = cls._enum_from_name(EquipSlot, data.get("slot"), EquipSlot.NOT_EQUIPABLE)
        item_type = cls._enum_from_name(ItemType, data.get("itemType"), ItemType.DEFAULT)
        item_id = str(data.get("itemId", data.get("itemID", "")) or "").strip()
        tier = cls._coerce_int(data.get("tier", 0), 0)
        durability = cls._coerce_float(data.get("durability", DEFAULT_DURABILITY), float(DEFAULT_DURABILITY))

        raw_bonuses = data.get("statBonuses", [])
        stat_bonuses = []
        if isinstance(raw_bonuses, list):
            for raw in raw_bonuses:
                parsed = cls._bonus_from_dict(raw)
                if parsed is not None:
                    stat_bonuses.append(parsed)

        return {
            "name": name,
            "slot": slot,
            "tier": tier,
            "durability": durability,
            "statBonuses": stat_bonuses,
            "itemType": item_type,
            "itemId": item_id,
            "powerLevel": cls._coerce_float(data.get("powerLevel", 0.0), 0.0),
        }

    @classmethod
    def _looks_like_legacy_shield(cls, data: dict[str, Any], item_type: ItemType, name: str) -> bool:
        if item_type not in WEAPON_ITEM_TYPES:
            return False
        if "shield" not in name.lower():
            return False
        if isinstance(data.get("weaponStats"), dict):
            return False
        if cls._damage_type_from_list(data.get("damageType", [])):
            return False
        raw_powers = cls._parse_item_power_list(data.get("itemPower", []))
        if any(int(getattr(power, "power", 0) or 0) > 0 for power in raw_powers):
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "itemId": self.itemId,
            "itemClass": self.itemClass,
            "name": self.name,
            "slot": self.slot.name,
            "tier": int(self.tier),
            "durability": _serialize_number(self.durability),
            "statBonuses": [self._bonus_to_dict(bonus) for bonus in self.statBonuses],
            "itemType": self.itemType.name,
            "powerLevel": _serialize_number(self.powerLevel),
            "itemPower": [self._item_power_to_dict(power) for power in self.itemPower],
            "damageType": [damage_type.name for damage_type in self.damageType],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Item":
        if not isinstance(data, dict):
            raise ValueError("Item data must be a dictionary.")

        common = cls._common_payload_from_dict(data)
        item_class = str(data.get("itemClass", "") or "").strip().lower()
        item_type = common["itemType"]
        name = common["name"]

        if item_class == "weapon" or (not item_class and item_type in WEAPON_ITEM_TYPES and not cls._looks_like_legacy_shield(data, item_type, name)):
            return Weapon._from_dict_internal(data, common)
        if item_class == "armor" or item_type == ItemType.ARMOR or cls._looks_like_legacy_shield(data, item_type, name):
            return Armor._from_dict_internal(data, common)
        if item_class == "consumable" or item_type == ItemType.CONSUMABLE:
            return Consumable._from_dict_internal(data, common)
        return cls(**common)


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
        itemId: str | None = None,
        powerLevel: float = 0.0,
    ):
        normalized_type = itemType if itemType in WEAPON_ITEM_TYPES else ItemType.MELEE_WEAPON
        normalized_slot = self._normalize_weapon_slot(slot)
        super().__init__(
            name=name,
            slot=normalized_slot,
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
                },
                "damageType": [damage_type.name for damage_type in self.damageType],
                "damageMin": _serialize_number(self.damageMin),
                "damageMax": _serialize_number(self.damageMax),
                "armorMultiplier": float(self.armorMultiplier),
                "ignoreArmorFraction": float(self.ignoreArmorFraction),
                "penetrationBase": float(self.penetrationBase),
            }
        )
        return payload

    @classmethod
    def _from_dict_internal(cls, data: dict[str, Any], common: dict[str, Any]) -> "Weapon":
        weapon_stats = data.get("weaponStats") if isinstance(data.get("weaponStats"), dict) else {}
        raw_power = cls._parse_item_power_list(data.get("itemPower", []))
        fallback_damage = float(raw_power[0].power) if raw_power else 0.0
        damage_types = weapon_stats.get("damageTypes", data.get("damageType", []))
        damage_min = cls._coerce_float(weapon_stats.get("damageMin", data.get("damageMin", fallback_damage)), fallback_damage)
        damage_max = cls._coerce_float(weapon_stats.get("damageMax", data.get("damageMax", damage_min)), damage_min)
        armor_multiplier = cls._coerce_float(weapon_stats.get("armorMultiplier", data.get("armorMultiplier", 1.0)), 1.0)
        ignore_armor_fraction = cls._coerce_float(weapon_stats.get("ignoreArmorFraction", data.get("ignoreArmorFraction", 0.0)), 0.0)
        penetration_base = cls._coerce_float(weapon_stats.get("penetrationBase", data.get("penetrationBase", 0.0)), 0.0)
        return cls(
            name=common["name"],
            slot=common["slot"],
            tier=common["tier"],
            durability=common["durability"],
            statBonuses=common["statBonuses"],
            itemType=common["itemType"],
            damageType=cls._damage_type_from_list(damage_types),
            damageMin=damage_min,
            damageMax=damage_max,
            armorMultiplier=armor_multiplier,
            ignoreArmorFraction=ignore_armor_fraction,
            penetrationBase=penetration_base,
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
            itemType=ItemType.ARMOR,
            itemId=itemId,
            powerLevel=powerLevel,
        )
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
        max_armor = cls._coerce_float(armor_stats.get("maxArmor", data.get("maxArmor", common["durability"])), common["durability"])
        current_armor = cls._coerce_float(armor_stats.get("currentArmor", data.get("currentArmor", common["durability"])), common["durability"])
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


class Gear:
    def __init__(
        self,
        head: Item | None = None,
        neck: Item | None = None,
        body: Item | None = None,
        hands: Item | None = None,
        ring: Item | None = None,
        legs: Item | None = None,
        feet: Item | None = None,
        primaryWeapon: Item | None = None,
        offhand: Item | None = None,
        inventory: list[Item] | None = None,
    ):
        self.head = head
        self.neck = neck
        self.body = body
        self.hands = hands
        self.ring = ring
        self.legs = legs
        self.feet = feet
        self.primaryWeapon = primaryWeapon
        self.offhand = offhand
        self.inventory = inventory if inventory is not None else []

    def GetAllEquipped(self) -> list[Item]:
        return [
            item
            for item in [
                self.head,
                self.neck,
                self.body,
                self.hands,
                self.ring,
                self.legs,
                self.feet,
                self.primaryWeapon,
                self.offhand,
            ]
            if item is not None
        ]

    def _get_item_for_location(self, location: HitLocation) -> Armor | None:
        item = None
        if location == HitLocation.HEAD:
            item = self.head
        elif location == HitLocation.BODY:
            item = self.body
        elif location == HitLocation.ARMS:
            item = self.hands
        elif location == HitLocation.LEGS:
            item = self.legs
        return item if isinstance(item, Armor) else None

    def get_armor(self, location: HitLocation) -> float:
        item = self._get_item_for_location(location)
        if item is None:
            return 0.0
        return max(0.0, float(item.currentArmor))

    def set_armor(self, location: HitLocation, new_value: float) -> None:
        item = self._get_item_for_location(location)
        if item is None:
            return
        item.currentArmor = max(0.0, float(new_value))
