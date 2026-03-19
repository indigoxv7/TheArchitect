from __future__ import annotations

from src.domain.character_util import HitLocation
from src.domain.items.core import Item
from src.domain.items.types import Armor


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

