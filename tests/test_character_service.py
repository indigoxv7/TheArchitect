import json
import tempfile
import unittest
from pathlib import Path

from src.services.character_service import CharacterService
from src.services.game_context import GameContext
from src.services.item_service import ItemService


class TestCharacterService(unittest.TestCase):
    def _build_services(self, temp_dir: str):
        itembook_path = Path(temp_dir) / "itembook.json"
        characters_dir = Path(temp_dir) / "Characters"
        context = GameContext()

        item_service = ItemService(str(itembook_path), context)
        item_service.load_itembook()

        character_service = CharacterService(str(characters_dir), context=context, item_service=item_service)
        character_service.load_characters()
        return context, item_service, character_service, characters_dir

    def _create_item(self, item_service: ItemService, name: str, slot: str = "HANDS"):
        payload = {
            "name": name,
            "slot": slot,
            "tier": 1,
            "durability": 90,
            "itemType": "MELEE_WEAPON" if slot == "HANDS" else "ARMOR",
            "itemPower": [{"powerType": "PHYSICAL_ATTACK", "power": 6, "spellName": ""}] if slot == "HANDS" else [],
            "damageType": ["SLASHING"] if slot == "HANDS" else [],
            "statBonuses": [],
        }
        item_service.create_item_from_dict(payload)
        return item_service.get_item(name)

    def test_create_save_and_reload_character_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            context, item_service, character_service, characters_dir = self._build_services(temp_dir)
            helm = self._create_item(item_service, "Test Helm", slot="HEAD")
            sword = self._create_item(item_service, "Test Sword", slot="HANDS")
            self.assertIsNotNone(helm)
            self.assertIsNotNone(sword)

            payload = {
                "name": "Rhea",
                "level": 4,
                "raceTier": "Tier II",
                "party": 1,
                "health": 87,
                "healthState": "INJURED",
                "activeAchievementTitle": "Storm Caller",
                "attributes": {
                    "physicalPower": 7,
                    "physicalStamina": 6,
                    "physicalResistance": 5,
                    "magicPower": 8,
                    "magicStamina": 7,
                    "magicResistance": 6,
                },
                "affinities": {"chi": 0.6, "mana": 0.7, "psi": 0.5, "aether": 0.4},
                "gear": {
                    "head_item_id": helm.itemId,
                    "neck_item_id": "",
                    "body_item_id": "",
                    "hands_item_id": "",
                    "ring_item_id": "",
                    "legs_item_id": "",
                    "feet_item_id": "",
                    "primary_weapon_item_id": sword.itemId,
                    "offhand_item_id": "",
                    "inventory_item_ids": [helm.itemId, sword.itemId],
                },
                "achievements": [
                    {
                        "name": "First Steps",
                        "title": "Initiate",
                        "bonus": {
                            "bonusType": "FLAT",
                            "attributeBonus": {"attribute": "PHYSICAL_POWER", "bonus": 1},
                            "affinities": None,
                            "nanoMultiplier": 0.0,
                            "reason": "Achievement bonus",
                            "permanent": True,
                        },
                    }
                ],
                "buffs": [
                    {
                        "duration": 3,
                        "bonus": {
                            "bonusType": "PERCENTAGE",
                            "attributeBonus": {"attribute": "MAGIC_POWER", "bonus": 1},
                            "affinities": None,
                            "nanoMultiplier": 0.2,
                            "reason": "Potion",
                            "permanent": False,
                        },
                    }
                ],
                "spells": [
                    {
                        "name": "Spark",
                        "level": 1,
                        "power": 3,
                        "affinity": "Mana",
                        "casting_time": 1,
                        "range": 30,
                        "components": {"verbal": True, "somatic": False, "material": False},
                        "duration": 0,
                        "description": "A tiny spark.",
                    }
                ],
                "generalSkills": [{"name": "Stealth", "description": "Move quietly."}],
                "stats": {"kills": 2, "damageTaken": 5, "missionCount": 1},
            }

            character_id, _ = character_service.create_character_from_dict(payload)
            self.assertTrue(character_id.startswith("Rhea"))

            character_file = characters_dir / f"{character_id}.json"
            self.assertTrue(character_file.exists())
            raw_payload = json.loads(character_file.read_text(encoding="utf-8"))
            self.assertEqual(raw_payload.get("format_version"), 1)
            self.assertEqual(raw_payload.get("character_id"), character_id)
            self.assertIn("character_state", raw_payload)

            reloaded_context = GameContext()
            reloaded_item_service = ItemService(str(Path(temp_dir) / "itembook.json"), reloaded_context)
            reloaded_item_service.load_itembook()
            reloaded_character_service = CharacterService(
                str(characters_dir),
                context=reloaded_context,
                item_service=reloaded_item_service,
            )
            reloaded_character_service.load_characters()

            loaded = reloaded_character_service.get_character(character_id)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.name, "Rhea")
            self.assertEqual(loaded.level, 4)
            self.assertEqual(loaded.health, 87)
            self.assertEqual(loaded.healthState.name, "INJURED")
            self.assertEqual(loaded.gear.head.itemId, helm.itemId)
            self.assertEqual(loaded.gear.primaryWeapon.itemId, sword.itemId)
            self.assertEqual(len(loaded.gear.inventory), 2)
            self.assertEqual(len(loaded.achievements), 1)
            self.assertEqual(len(loaded.buffs), 1)

            self.assertIn(character_id, reloaded_context.characterbook_overview)

    def test_missing_gear_item_ids_fallback_without_crash(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, item_service, character_service, _characters_dir = self._build_services(temp_dir)
            known_item = self._create_item(item_service, "Known Sword", slot="HANDS")
            self.assertIsNotNone(known_item)

            payload = {
                "name": "Fallback Tester",
                "gear": {
                    "head_item_id": "MISSING-ID-001",
                    "neck_item_id": "",
                    "body_item_id": "",
                    "hands_item_id": "",
                    "ring_item_id": "",
                    "legs_item_id": "",
                    "feet_item_id": "",
                    "primary_weapon_item_id": known_item.itemId,
                    "offhand_item_id": "MISSING-ID-002",
                    "inventory_item_ids": ["MISSING-ID-003", known_item.itemId],
                },
                "achievements": [],
                "buffs": [],
            }

            character_id, created = character_service.create_character_from_dict(payload)
            self.assertIsNotNone(created.gear.head)
            self.assertEqual(created.gear.head.itemId, ItemService.ERROR_ITEM_ID)
            self.assertEqual(created.gear.primaryWeapon.itemId, known_item.itemId)

            character_service.load_characters()
            loaded = character_service.get_character(character_id)
            self.assertIsNotNone(loaded)
            self.assertIsNotNone(loaded.gear.head)
            self.assertEqual(loaded.gear.head.itemId, ItemService.ERROR_ITEM_ID)
            self.assertEqual(loaded.gear.offhand.itemId, ItemService.ERROR_ITEM_ID)
            self.assertGreaterEqual(len(loaded.gear.inventory), 1)


if __name__ == "__main__":
    unittest.main()
