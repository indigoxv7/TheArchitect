import tempfile
import unittest
from pathlib import Path

from src.services.game_context import GameContext
from src.services.item_service import ItemService


class TestItemService(unittest.TestCase):
    def test_create_edit_and_reload_itembook(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "itembook.json"
            context = GameContext()
            service = ItemService(str(path), context)
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
            self.assertEqual(created.itemType.name, "MELEE_WEAPON")

            service.edit_item_from_patch("Test Blade", {"name": "Test Sword", "tier": 3})
            self.assertIsNone(service.get_item("Test Blade"))
            edited = service.get_item("Test Sword")
            self.assertIsNotNone(edited)
            self.assertEqual(edited.tier, 3)

            context2 = GameContext()
            service2 = ItemService(str(path), context2)
            service2.load_itembook()
            loaded = service2.get_item("Test Sword")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.slot.name, "HANDS")


if __name__ == "__main__":
    unittest.main()
