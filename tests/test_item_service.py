import json
import tempfile
import unittest
from pathlib import Path

from src.services.game_context import GameContext
from src.services.item_service import ItemService


class TestItemService(unittest.TestCase):
    def _make_service(self, temp_dir: str):
        itembook_path = Path(temp_dir) / "itembook.json"
        context = GameContext()
        service = ItemService(str(itembook_path), context)
        return service, context, itembook_path

    def test_create_edit_and_reload_itembook(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service, _context, path = self._make_service(temp_dir)
            service.load_itembook()

            payload = {
                "name": "Test Blade",
                "slot": "HANDS",
                "tier": 2,
                "durability": 85,
                "itemType": "MELEE_WEAPON",
                "itemPower": [{"powerType": "PHYSICAL_ATTACK", "power": 11, "spellName": ""}],
                "damageType": ["SLASHING"],
                "statBonuses": [],
            }
            service.create_item_from_dict(payload)

            created = service.get_item("Test Blade")
            self.assertIsNotNone(created)
            self.assertTrue(created.itemId)
            self.assertEqual(created.itemType.name, "MELEE_WEAPON")

            created_id = created.itemId
            service.edit_item_from_patch(created_id, {"name": "Test Sword", "tier": 3})

            self.assertIsNone(service.get_item("Test Blade"))
            edited = service.get_item(created_id)
            self.assertIsNotNone(edited)
            self.assertEqual(edited.name, "Test Sword")
            self.assertEqual(edited.tier, 3)

            reloaded_context = GameContext()
            reloaded_service = ItemService(str(path), reloaded_context)
            reloaded_service.load_itembook()
            loaded = reloaded_service.get_item(created_id)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.slot.name, "HANDS")
            self.assertEqual(loaded.name, "Test Sword")

    def test_legacy_itembook_without_ids_auto_migrates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service, _context, path = self._make_service(temp_dir)
            legacy_payload = {
                "format_version": 1,
                "items": [
                    {
                        "name": "Legacy Spear",
                        "slot": "HANDS",
                        "tier": 1,
                        "durability": 100,
                        "statBonuses": [],
                        "itemType": "MELEE_WEAPON",
                        "itemPower": [{"powerType": "PHYSICAL_ATTACK", "power": 5, "spellName": ""}],
                        "damageType": ["PIERCING"],
                    }
                ],
            }
            path.write_text(json.dumps(legacy_payload, indent=2), encoding="utf-8")

            service.load_itembook()
            items = service.list_items()
            self.assertEqual(len(items), 1)
            self.assertTrue(items[0].itemId)

            migrated_payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(migrated_payload.get("format_version"), 2)
            self.assertTrue(migrated_payload["items"][0].get("itemId"))

    def test_duplicate_names_are_distinct_and_name_lookup_is_ambiguous(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service, _context, _path = self._make_service(temp_dir)
            service.load_itembook()

            payload = {
                "name": "Twin Blade",
                "slot": "HANDS",
                "tier": 1,
                "durability": 75,
                "itemType": "MELEE_WEAPON",
                "itemPower": [{"powerType": "PHYSICAL_ATTACK", "power": 7, "spellName": ""}],
                "damageType": ["SLASHING"],
                "statBonuses": [],
            }
            service.create_item_from_dict(payload)
            service.create_item_from_dict(payload)

            by_name = service.get_items_by_name("Twin Blade")
            self.assertEqual(len(by_name), 2)
            self.assertIsNone(service.get_item("Twin Blade"))

            ids = {item.itemId for item in by_name}
            self.assertEqual(len(ids), 2)
            for item_id in ids:
                loaded = service.get_item(item_id)
                self.assertIsNotNone(loaded)
                self.assertEqual(loaded.name, "Twin Blade")

    def test_edit_by_id_preserves_immutable_id_on_rename(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service, _context, path = self._make_service(temp_dir)
            service.load_itembook()

            payload = {
                "name": "Immutable Test",
                "slot": "HEAD",
                "tier": 0,
                "durability": 100,
                "itemType": "ARMOR",
                "itemPower": [],
                "damageType": [],
                "statBonuses": [],
            }
            service.create_item_from_dict(payload)
            created = service.get_item("Immutable Test")
            self.assertIsNotNone(created)

            original_id = created.itemId
            service.edit_item_from_patch(original_id, {"name": "Immutable Renamed", "itemId": "TamperedId999"})

            updated = service.get_item(original_id)
            self.assertIsNotNone(updated)
            self.assertEqual(updated.itemId, original_id)
            self.assertEqual(updated.name, "Immutable Renamed")

            reloaded_context = GameContext()
            reloaded_service = ItemService(str(path), reloaded_context)
            reloaded_service.load_itembook()
            reloaded = reloaded_service.get_item(original_id)
            self.assertIsNotNone(reloaded)
            self.assertEqual(reloaded.itemId, original_id)
            self.assertEqual(reloaded.name, "Immutable Renamed")


if __name__ == "__main__":
    unittest.main()
