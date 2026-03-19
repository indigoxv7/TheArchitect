from __future__ import annotations

from typing import Any, Callable

from src.domain.character_util import EquipSlot
from src.domain.items import Item


class GearOptions:
    FIELD_SPECS = [
        ("headOptions", "Head", EquipSlot.HEAD),
        ("neckOptions", "Neck", EquipSlot.NECK),
        ("bodyOptions", "Body", EquipSlot.BODY),
        ("handsOptions", "Hands", EquipSlot.HANDS),
        ("ringOptions", "Ring", EquipSlot.RING),
        ("legsOptions", "Legs", EquipSlot.LEGS),
        ("feetOptions", "Feet", EquipSlot.FEET),
        ("primaryWeaponOptions", "Primary Weapon", EquipSlot.PRIMARY_WEAPON),
        ("offhandOptions", "Offhand", EquipSlot.OFFHAND),
        ("inventoryOptions", "Inventory", None),
    ]

    def __init__(
        self,
        headOptions: list[Item] | None = None,
        neckOptions: list[Item] | None = None,
        bodyOptions: list[Item] | None = None,
        handsOptions: list[Item] | None = None,
        ringOptions: list[Item] | None = None,
        legsOptions: list[Item] | None = None,
        feetOptions: list[Item] | None = None,
        primaryWeaponOptions: list[Item] | None = None,
        offhandOptions: list[Item] | None = None,
        inventoryOptions: list[Item] | None = None,
    ):
        self.headOptions = self._normalize_items(headOptions)
        self.neckOptions = self._normalize_items(neckOptions)
        self.bodyOptions = self._normalize_items(bodyOptions)
        self.handsOptions = self._normalize_items(handsOptions)
        self.ringOptions = self._normalize_items(ringOptions)
        self.legsOptions = self._normalize_items(legsOptions)
        self.feetOptions = self._normalize_items(feetOptions)
        self.primaryWeaponOptions = self._normalize_items(primaryWeaponOptions)
        self.offhandOptions = self._normalize_items(offhandOptions)
        self.inventoryOptions = self._normalize_items(inventoryOptions)

    @staticmethod
    def _normalize_items(items: Any) -> list[Item]:
        if not isinstance(items, list):
            return []
        return [item for item in items if isinstance(item, Item)]

    @classmethod
    def empty_payload(cls) -> dict[str, list[str]]:
        return {field_name: [] for field_name, _label, _slot in cls.FIELD_SPECS}

    def to_dict(self, resolve_item_id: Callable[[Item], str | None] | None = None) -> dict[str, list[str]]:
        payload = self.empty_payload()
        for field_name, _label, _slot in self.FIELD_SPECS:
            item_ids: list[str] = []
            for item in getattr(self, field_name, []) or []:
                if item is None:
                    continue
                item_id = None
                if callable(resolve_item_id):
                    item_id = resolve_item_id(item)
                if not item_id:
                    item_id = str(getattr(item, "itemId", "") or "").strip()
                if item_id:
                    item_ids.append(item_id)
            payload[field_name] = item_ids
        return payload

    @classmethod
    def from_dict(
        cls,
        data: Any,
        resolve_item: Callable[[str], Item | None] | None = None,
    ) -> "GearOptions":
        if not isinstance(data, dict):
            return cls()

        kwargs = {}
        for field_name, _label, _slot in cls.FIELD_SPECS:
            resolved_items: list[Item] = []
            raw_value = data.get(field_name, [])
            if isinstance(raw_value, list):
                for entry in raw_value:
                    if isinstance(entry, Item):
                        resolved_items.append(entry)
                        continue
                    item_id = str(entry or "").strip()
                    if not item_id or not callable(resolve_item):
                        continue
                    resolved = resolve_item(item_id)
                    if resolved is not None:
                        resolved_items.append(resolved)
            kwargs[field_name] = resolved_items
        return cls(**kwargs)

