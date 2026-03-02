from src.domain.CharacterUtil import DEFAULT_DURABILITY, EquipSlot, ItemType
from src.domain.Items import Item
from src.persistence.itembook_store import ItembookStore
from src.services.game_context import GameContext


class ItemService:
    def __init__(self, itembook_path: str, context: GameContext):
        self.context = context
        self.store = ItembookStore(itembook_path)

    def _ensure_error_item(self):
        if self.context.error_item is None:
            self.context.error_item = Item(
                "[ERROR MISSING ITEM]",
                EquipSlot.NOT_EQUIPABLE,
                0,
                DEFAULT_DURABILITY,
                None,
                ItemType.DEFAULT,
                None,
                None,
            )
        self.context.all_items[self.context.error_item.name] = self.context.error_item

    def _is_error_item_name(self, name: str) -> bool:
        return self.context.error_item is not None and name == self.context.error_item.name

    def load_itembook(self, default_items: dict[str, Item] | None = None):
        payload = self.store.load()
        raw_items = payload.get("items", [])

        if not raw_items and default_items:
            self.context.all_items.clear()
            self.context.all_items.update(default_items)
            self._ensure_error_item()
            self.save_itembook()
            self.context.itembook_overview = self.build_itembook_overview()
            return

        self.context.all_items.clear()
        for item_data in raw_items:
            try:
                item = Item.from_dict(item_data)
            except Exception:
                continue
            self.context.all_items[item.name] = item

        self._ensure_error_item()
        self.context.itembook_overview = self.build_itembook_overview()

    def save_itembook(self):
        items = [item.to_dict() for item in self.list_items()]
        payload = {"format_version": 1, "items": items}
        self.store.save(payload)
        self.context.itembook_overview = self.build_itembook_overview()

    def list_items(self) -> list[Item]:
        return [
            self.context.all_items[name]
            for name in sorted(self.context.all_items.keys())
            if not self._is_error_item_name(name)
        ]

    def get_item(self, name: str) -> Item | None:
        item = self.context.all_items.get(name)
        if item is None or self._is_error_item_name(name):
            return None
        return item

    def create_item_from_dict(self, data: dict):
        item = Item.from_dict(data)
        if item.name in self.context.all_items and not self._is_error_item_name(item.name):
            raise ValueError(f"Item '{item.name}' already exists.")

        self.context.all_items[item.name] = item
        self._ensure_error_item()
        self.save_itembook()

    def edit_item_from_patch(self, item_name: str, patch: dict):
        existing = self.get_item(item_name)
        if existing is None:
            raise ValueError(f"Item '{item_name}' does not exist.")

        merged = existing.to_dict()
        merged.update(patch)
        if "name" not in merged or not str(merged["name"]).strip():
            merged["name"] = existing.name

        updated = Item.from_dict(merged)

        if updated.name != existing.name:
            self.context.all_items.pop(existing.name, None)
        self.context.all_items[updated.name] = updated
        self._ensure_error_item()
        self.save_itembook()

    def build_itembook_overview(self, max_lines: int = 20) -> str:
        items = self.list_items()
        if not items:
            return "No items in itembook yet."

        lines = []
        for item in items[:max_lines]:
            lines.append(f"- {item.name} (T{item.tier}, {item.itemType.name}, {item.slot.name})")

        if len(items) > max_lines:
            lines.append(f"... and {len(items) - max_lines} more")

        return "\n".join(lines)
