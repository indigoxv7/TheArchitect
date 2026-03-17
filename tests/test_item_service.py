import json
import tempfile
import unittest
from pathlib import Path

from src.domain.Items import Armor, Consumable, Weapon
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
                "itemClass": "Weapon",
                "slot": "PRIMARY_WEAPON",
                "tier": 2,
                "durability": 85,
                "itemType": "MELEE_WEAPON",
                "damageType": ["SLASHING"],
                "damageMin": 11,
                "damageMax": 17,
                "armorMultiplier": 1.15,
                "ignoreArmorFraction": 0.1,
                "penetrationBase": 7,
                "statBonuses": [],
                "powerLevel": 12.5,
            }
            service.create_item_from_dict(payload)

            created = service.get_item("Test Blade")
            self.assertIsInstance(created, Weapon)
            self.assertTrue(created.itemId)
            self.assertEqual(created.slot.name, "PRIMARY_WEAPON")
            self.assertEqual(created.powerLevel, 12.5)

            created_id = created.itemId
            service.edit_item_from_patch(created_id, {
                "name": "Test Sword",
                "tier": 3,
                "damageType": ["PIERCING"],
                "damageMin": 21,
                "damageMax": 29,
                "armorMultiplier": 1.5,
                "ignoreArmorFraction": 0.25,
                "penetrationBase": 14,
            })

            self.assertIsNone(service.get_item("Test Blade"))
            edited = service.get_item(created_id)
            self.assertIsNotNone(edited)
            self.assertEqual(edited.name, "Test Sword")
            self.assertEqual(edited.tier, 3)
            self.assertEqual(edited.damageType[0].name, "PIERCING")
            self.assertEqual(edited.damageMin, 21)
            self.assertEqual(edited.damageMax, 29)
            self.assertEqual(edited.armorMultiplier, 1.5)
            self.assertEqual(edited.ignoreArmorFraction, 0.25)
            self.assertEqual(edited.penetrationBase, 14)

            reloaded_context = GameContext()
            reloaded_service = ItemService(str(path), reloaded_context)
            reloaded_service.load_itembook()
            loaded = reloaded_service.get_item(created_id)
            self.assertIsInstance(loaded, Weapon)
            self.assertEqual(loaded.slot.name, "PRIMARY_WEAPON")
            self.assertEqual(loaded.name, "Test Sword")
            self.assertEqual(loaded.powerLevel, 12.5)
            self.assertEqual(loaded.damageType[0].name, "PIERCING")
            self.assertEqual(loaded.damageMin, 21)
            self.assertEqual(loaded.damageMax, 29)
            self.assertEqual(loaded.armorMultiplier, 1.5)
            self.assertEqual(loaded.ignoreArmorFraction, 0.25)
            self.assertEqual(loaded.penetrationBase, 14)

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
            self.assertIsInstance(items[0], Weapon)
            self.assertEqual(items[0].slot.name, "PRIMARY_WEAPON")

            migrated_payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(migrated_payload.get("format_version"), 3)
            self.assertTrue(migrated_payload["items"][0].get("itemId"))

    def test_duplicate_names_are_distinct_and_name_lookup_is_ambiguous(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service, _context, _path = self._make_service(temp_dir)
            service.load_itembook()

            payload = {
                "name": "Twin Blade",
                "itemClass": "Weapon",
                "slot": "PRIMARY_WEAPON",
                "tier": 1,
                "durability": 75,
                "itemType": "MELEE_WEAPON",
                "damageType": ["SLASHING"],
                "damageMin": 7,
                "damageMax": 10,
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
                self.assertIsInstance(loaded, Weapon)
                self.assertEqual(loaded.name, "Twin Blade")

    def test_edit_by_id_preserves_immutable_id_on_rename(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service, _context, path = self._make_service(temp_dir)
            service.load_itembook()

            payload = {
                "name": "Immutable Test",
                "itemClass": "Armor",
                "slot": "HEAD",
                "tier": 0,
                "itemType": "ARMOR",
                "maxArmor": 18,
                "currentArmor": 18,
                "statBonuses": [],
            }
            service.create_item_from_dict(payload)
            created = service.get_item("Immutable Test")
            self.assertIsInstance(created, Armor)

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

    def test_consumable_round_trip_uses_consumable_subclass(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service, _context, path = self._make_service(temp_dir)
            service.load_itembook()
            service.create_item_from_dict(
                {
                    "name": "Fire Bomb",
                    "itemClass": "Consumable",
                    "tier": 1,
                    "consumableKind": "BOMB",
                    "effectPowerType": "CONSUMABLE_POWER",
                    "effectPower": 16,
                    "damageType": ["FIRE"],
                    "spellName": "",
                    "statBonuses": [],
                }
            )

            created = service.get_item("Fire Bomb")
            self.assertIsInstance(created, Consumable)
            self.assertEqual(created.slot.name, "NOT_EQUIPABLE")

            reloaded_context = GameContext()
            reloaded_service = ItemService(str(path), reloaded_context)
            reloaded_service.load_itembook()
            loaded = reloaded_service.get_item(created.itemId)
            self.assertIsInstance(loaded, Consumable)
            self.assertEqual(loaded.damageType[0].name, "FIRE")


    def test_edit_subclass_specific_fields_for_armor_and_consumable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service, _context, path = self._make_service(temp_dir)
            service.load_itembook()

            service.create_item_from_dict({
                "name": "Tower Shield",
                "itemClass": "Armor",
                "slot": "OFFHAND",
                "itemType": "ARMOR",
                "maxArmor": 18,
                "currentArmor": 18,
                "statBonuses": [],
            })
            service.create_item_from_dict({
                "name": "Ice Bomb",
                "itemClass": "Consumable",
                "consumableKind": "BOMB",
                "effectPowerType": "CONSUMABLE_POWER",
                "effectPower": 16,
                "damageType": ["COLD"],
                "spellName": "",
                "statBonuses": [],
            })

            shield = service.get_item("Tower Shield")
            bomb = service.get_item("Ice Bomb")
            self.assertIsInstance(shield, Armor)
            self.assertIsInstance(bomb, Consumable)

            service.edit_item_from_patch(shield.itemId, {
                "maxArmor": 27,
                "currentArmor": 21,
            })
            service.edit_item_from_patch(bomb.itemId, {
                "effectPower": 24,
                "damageType": ["FIRE"],
                "consumableKind": "POTION",
            })

            updated_shield = service.get_item(shield.itemId)
            updated_bomb = service.get_item(bomb.itemId)
            self.assertIsInstance(updated_shield, Armor)
            self.assertIsInstance(updated_bomb, Consumable)
            self.assertEqual(updated_shield.maxArmor, 27)
            self.assertEqual(updated_shield.currentArmor, 21)
            self.assertEqual(updated_bomb.effectPower, 24)
            self.assertEqual(updated_bomb.damageType[0].name, "FIRE")
            self.assertEqual(updated_bomb.consumableKind.name, "POTION")

            reloaded_context = GameContext()
            reloaded_service = ItemService(str(path), reloaded_context)
            reloaded_service.load_itembook()
            loaded_shield = reloaded_service.get_item(shield.itemId)
            loaded_bomb = reloaded_service.get_item(bomb.itemId)
            self.assertIsInstance(loaded_shield, Armor)
            self.assertIsInstance(loaded_bomb, Consumable)
            self.assertEqual(loaded_shield.maxArmor, 27)
            self.assertEqual(loaded_shield.currentArmor, 21)
            self.assertEqual(loaded_bomb.effectPower, 24)
            self.assertEqual(loaded_bomb.damageType[0].name, "FIRE")
            self.assertEqual(loaded_bomb.consumableKind.name, "POTION")


if __name__ == "__main__":
    unittest.main()
