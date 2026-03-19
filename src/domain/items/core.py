from __future__ import annotations

from typing import Any

from src.domain.character_util import (
    Affinities,
    Attribute,
    AttributeBonus,
    Bonus,
    BonusType,
    DamageType,
    DEFAULT_DURABILITY,
    EquipSlot,
    ItemPower,
    ItemType,
    PowerType,
)
from src.domain.items.support import WEAPON_ITEM_TYPES, _serialize_number, _unique_strings


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
        return ItemPower(
            powerType=cls._enum_from_name(PowerType, data.get("powerType"), PowerType.PHYSICAL_ATTACK),
            power=cls._coerce_int(data.get("power", 0), 0),
            spellName=str(data.get("spellName", "") or "").strip(),
        )

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

        attribute_bonus = None
        attribute_bonus_data = data.get("attributeBonus")
        if isinstance(attribute_bonus_data, dict):
            attr = cls._enum_from_name(Attribute, attribute_bonus_data.get("attribute"), None)
            if attr is not None:
                attribute_bonus = AttributeBonus(
                    attribute=attr,
                    bonus=cls._coerce_int(attribute_bonus_data.get("bonus", 0), 0),
                )

        affinities = None
        affinities_data = data.get("affinities")
        if isinstance(affinities_data, dict):
            affinities = Affinities(
                chi=float(affinities_data.get("chi", 0) or 0),
                mana=float(affinities_data.get("mana", 0) or 0),
                psi=float(affinities_data.get("psi", 0) or 0),
                aether=float(affinities_data.get("aether", 0) or 0),
            )

        return Bonus(
            bonusType=cls._enum_from_name(BonusType, data.get("bonusType"), BonusType.FLAT),
            attributeBonus=attribute_bonus,
            affinities=affinities,
            nanoMultiplier=float(data.get("nanoMultiplier", 0) or 0),
            reason=str(data.get("reason", "") or "").strip(),
            permanent=bool(data.get("permanent", False)),
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

        stat_bonuses = []
        raw_bonuses = data.get("statBonuses", [])
        if isinstance(raw_bonuses, list):
            for raw in raw_bonuses:
                parsed = cls._bonus_from_dict(raw)
                if parsed is not None:
                    stat_bonuses.append(parsed)

        return {
            "name": name,
            "slot": cls._enum_from_name(EquipSlot, data.get("slot"), EquipSlot.NOT_EQUIPABLE),
            "tier": cls._coerce_int(data.get("tier", 0), 0),
            "durability": cls._coerce_float(data.get("durability", DEFAULT_DURABILITY), float(DEFAULT_DURABILITY)),
            "statBonuses": stat_bonuses,
            "itemType": cls._enum_from_name(ItemType, data.get("itemType"), ItemType.DEFAULT),
            "itemId": str(data.get("itemId", data.get("itemID", "")) or "").strip(),
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

        from src.domain.items.types import Armor, Consumable, Weapon

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

