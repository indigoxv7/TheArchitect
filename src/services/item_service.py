import re

from src.domain.CharacterUtil import DEFAULT_DURABILITY, EquipSlot, ItemType
from src.domain.Items import Armor, Consumable, Item, Weapon
from src.persistence.itembook_store import ItembookStore
from src.services.game_context import GameContext


class ItemService:
    ERROR_ITEM_ID = "ERRORMISSINGITEM999999"

    def __init__(self, itembook_path: str, context: GameContext):
        self.context = context
        self.store = ItembookStore(itembook_path)

    @staticmethod
    def _slugify_name(name: str) -> str:
        compact = re.sub(r"\s+", "", str(name or "").strip())
        compact = re.sub(r"[^A-Za-z0-9_\-]", "", compact)
        return compact or "Item"

    @staticmethod
    def _normalize_slot(slot) -> EquipSlot | None:
        if isinstance(slot, EquipSlot):
            return slot
        if isinstance(slot, str):
            text = slot.strip().upper()
            if text in EquipSlot.__members__:
                return EquipSlot[text]
        return None

    def _is_error_item_id(self, item_id: str) -> bool:
        return self.context.error_item is not None and item_id == self.context.error_item.itemId

    def _generate_item_id(self, name: str) -> str:
        prefix = self._slugify_name(name)
        index = len([item for item in self.context.all_items.values() if not self._is_error_item_id(item.itemId)])
        candidate = f"{prefix}{index}"
        while candidate in self.context.all_items:
            index += 1
            candidate = f"{prefix}{index}"
        return candidate

    def _assign_item_id_if_missing(self, item: Item):
        if not getattr(item, "itemId", ""):
            item.itemId = self._generate_item_id(item.name)
        refresh_tags = getattr(item, "refresh_tags", None)
        if callable(refresh_tags):
            refresh_tags()

    def _rebuild_name_index(self):
        index: dict[str, list[str]] = {}
        for item_id, item in self.context.all_items.items():
            if self._is_error_item_id(item_id):
                continue
            key = str(item.name or "").strip().lower()
            if not key:
                continue
            index.setdefault(key, []).append(item_id)
        self.context.all_items_by_name = index

    def _ensure_error_item(self):
        if self.context.error_item is None:
            self.context.error_item = Item(
                name="[ERROR MISSING ITEM]",
                slot=EquipSlot.NOT_EQUIPABLE,
                tier=0,
                durability=DEFAULT_DURABILITY,
                statBonuses=None,
                itemType=ItemType.DEFAULT,
                itemId=self.ERROR_ITEM_ID,
            )
        self.context.error_item.itemId = self.ERROR_ITEM_ID
        self.context.all_items[self.ERROR_ITEM_ID] = self.context.error_item

    def load_itembook(self, default_items: dict[str, Item] | None = None):
        payload = self.store.load()
        raw_items = payload.get("items", [])
        migrated = False

        self.context.all_items.clear()

        if not raw_items and default_items:
            seen_item_ids = set()
            for item in default_items.values():
                if item is self.context.error_item or str(getattr(item, "name", "")).strip() == "[ERROR MISSING ITEM]":
                    continue
                self._assign_item_id_if_missing(item)
                if item.itemId in seen_item_ids:
                    item.itemId = self._generate_item_id(item.name)
                seen_item_ids.add(item.itemId)
                self.context.all_items[item.itemId] = item
            migrated = True
        else:
            for item_data in raw_items:
                try:
                    item = Item.from_dict(item_data)
                except Exception:
                    continue

                if not item.itemId:
                    item.itemId = self._generate_item_id(item.name)
                    migrated = True

                if item.itemId in self.context.all_items:
                    item.itemId = self._generate_item_id(item.name)
                    migrated = True

                self.context.all_items[item.itemId] = item

        self._ensure_error_item()
        self._rebuild_name_index()

        if migrated:
            self.save_itembook()
        else:
            self.context.itembook_overview = self.build_itembook_overview()

    def save_itembook(self):
        items = [item.to_dict() for item in self.list_items()]
        payload = {"format_version": 3, "items": items}
        self.store.save(payload)
        self.context.itembook_overview = self.build_itembook_overview()

    def list_items(self) -> list[Item]:
        items = [item for item_id, item in self.context.all_items.items() if not self._is_error_item_id(item_id)]
        return sorted(items, key=lambda item: (item.name.lower(), item.itemId))

    def list_items_for_slot(self, slot) -> list[Item]:
        slot_enum = self._normalize_slot(slot)
        if slot_enum is None:
            return self.list_items()
        return [item for item in self.list_items() if getattr(item, "can_equip_in", lambda _slot: False)(slot_enum)]

    def get_item_by_id(self, item_id: str) -> Item | None:
        item = self.context.all_items.get(str(item_id or "").strip())
        if item is None:
            return None
        if self._is_error_item_id(item.itemId):
            return None
        return item

    def get_weapon_by_id(self, item_id: str) -> Weapon | None:
        item = self.get_item_by_id(item_id)
        return item if isinstance(item, Weapon) else None

    def get_armor_by_id(self, item_id: str) -> Armor | None:
        item = self.get_item_by_id(item_id)
        return item if isinstance(item, Armor) else None

    def get_consumable_by_id(self, item_id: str) -> Consumable | None:
        item = self.get_item_by_id(item_id)
        return item if isinstance(item, Consumable) else None

    def get_items_by_name(self, name: str) -> list[Item]:
        key = str(name or "").strip().lower()
        if not key:
            return []

        item_ids = self.context.all_items_by_name.get(key, [])
        items: list[Item] = []
        for item_id in item_ids:
            item = self.get_item_by_id(item_id)
            if item is not None:
                items.append(item)
        return items

    def get_item(self, identifier: str) -> Item | None:
        key = str(identifier or "").strip()
        if not key:
            return None

        by_id = self.get_item_by_id(key)
        if by_id is not None:
            return by_id

        by_name = self.get_items_by_name(key)
        if len(by_name) == 1:
            return by_name[0]

        return None

    def get_weapon(self, identifier: str) -> Weapon | None:
        item = self.get_item(identifier)
        return item if isinstance(item, Weapon) else None

    def get_armor(self, identifier: str) -> Armor | None:
        item = self.get_item(identifier)
        return item if isinstance(item, Armor) else None

    def get_consumable(self, identifier: str) -> Consumable | None:
        item = self.get_item(identifier)
        return item if isinstance(item, Consumable) else None

    @staticmethod
    def get_item_label(item: Item) -> str:
        return f"{item.name} [{item.itemId}]"

    @staticmethod
    def parse_item_id_from_label(label: str) -> str:
        text = str(label or "").strip()
        if text.endswith("]") and "[" in text:
            return text[text.rfind("[") + 1 : -1].strip()
        return text

    @staticmethod
    def _synchronize_subclass_payload(payload: dict) -> dict:
        if not isinstance(payload, dict):
            return payload

        item_class = str(payload.get("itemClass", "") or "").strip().lower()
        item_type = str(payload.get("itemType", "") or "").strip().upper()

        if item_class == "weapon" or item_type in {"MELEE_WEAPON", "MELEE_THROWABLE", "RANGED_WEAPON"}:
            damage_types = payload.get("damageType", [])
            payload["weaponStats"] = {
                "damageTypes": list(damage_types) if isinstance(damage_types, list) else [],
                "damageMin": payload.get("damageMin", 0.0),
                "damageMax": payload.get("damageMax", payload.get("damageMin", 0.0)),
                "armorMultiplier": payload.get("armorMultiplier", 1.0),
                "ignoreArmorFraction": payload.get("ignoreArmorFraction", 0.0),
                "penetrationBase": payload.get("penetrationBase", 0.0),
                "staminaCost": payload.get("staminaCost", 10.0),
            }
        elif item_class == "armor" or item_type == "ARMOR":
            current_armor = payload.get("currentArmor", payload.get("durability", 0.0))
            payload["armorStats"] = {
                "maxArmor": payload.get("maxArmor", current_armor),
                "currentArmor": current_armor,
            }
        elif item_class == "consumable" or item_type == "CONSUMABLE":
            damage_types = payload.get("damageType", [])
            payload["consumableStats"] = {
                "consumableKind": payload.get("consumableKind", "NONE"),
                "effectPowerType": payload.get("effectPowerType", "CONSUMABLE_POWER"),
                "effectPower": payload.get("effectPower", 0.0),
                "spellName": payload.get("spellName", ""),
                "damageTypes": list(damage_types) if isinstance(damage_types, list) else [],
            }
        return payload

    def create_item_from_dict(self, data: dict):
        normalized = self._synchronize_subclass_payload(dict(data or {}))
        item = Item.from_dict(normalized)
        self._assign_item_id_if_missing(item)

        if item.itemId in self.context.all_items and not self._is_error_item_id(item.itemId):
            raise ValueError(f"Item ID '{item.itemId}' already exists.")

        self.context.all_items[item.itemId] = item
        self._ensure_error_item()
        self._rebuild_name_index()
        self.save_itembook()
        return item

    def edit_item_from_patch(self, item_identifier: str, patch: dict):
        existing = self.get_item(item_identifier)
        if existing is None:
            raise ValueError(f"Item '{item_identifier}' does not exist or is ambiguous.")

        merged = existing.to_dict()
        merged.update(patch)
        if "name" not in merged or not str(merged["name"]).strip():
            merged["name"] = existing.name

        merged["itemId"] = existing.itemId
        merged = self._synchronize_subclass_payload(merged)

        updated = Item.from_dict(merged)
        updated.itemId = existing.itemId

        self.context.all_items[updated.itemId] = updated
        self._ensure_error_item()
        self._rebuild_name_index()
        self.save_itembook()
        return updated

    def build_itembook_overview(self, max_lines: int = 20) -> str:
        items = self.list_items()
        if not items:
            return "No items in itembook yet."

        lines = []
        for item in items[:max_lines]:
            lines.append(
                f"- {item.name} [{item.itemId}] (T{item.tier}, {item.itemClass}, {item.slot.name})"
            )

        if len(items) > max_lines:
            lines.append(f"... and {len(items) - max_lines} more")

        return "\n".join(lines)
