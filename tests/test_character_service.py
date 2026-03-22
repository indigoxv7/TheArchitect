import json
import tempfile
import unittest
from pathlib import Path

from src.domain.main_character import MainCharacter
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

    def _create_item(self, item_service: ItemService, name: str, slot: str = "PRIMARY_WEAPON"):
        payload = {
            "name": name,
            "slot": slot,
            "tier": 1,
            "durability": 90,
            "itemType": "MELEE_WEAPON" if slot == "PRIMARY_WEAPON" else "ARMOR",
            "itemPower": [{"powerType": "PHYSICAL_ATTACK", "power": 6, "spellName": ""}]
            if slot == "PRIMARY_WEAPON"
            else [],
            "damageType": ["SLASHING"] if slot == "PRIMARY_WEAPON" else [],
            "statBonuses": [],
        }
        item_service.create_item_from_dict(payload)
        return item_service.get_item(name)

    def test_create_save_and_reload_character_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            context, item_service, character_service, characters_dir = self._build_services(temp_dir)
            helm = self._create_item(item_service, "Test Helm", slot="HEAD")
            sword = self._create_item(item_service, "Test Sword", slot="PRIMARY_WEAPON")
            self.assertIsNotNone(helm)
            self.assertIsNotNone(sword)

            payload = {
                "name": "Rhea",
                "level": 4,
                "raceTier": "Tier II",
                "race": "Elf2",
                "health": 87,
                "healthState": "INJURED",
                "friendlyFireTolerance": "Avoid intentional but allow risk",
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
            self.assertEqual(loaded.race, "Elf2")
            self.assertEqual(loaded.health, 87)
            self.assertEqual(loaded.healthState.name, "INJURED")
            self.assertEqual(getattr(loaded.friendlyFireTolerance, "value", ""), "Avoid intentional but allow risk")
            self.assertEqual(loaded.gear.head.itemId, helm.itemId)
            self.assertEqual(loaded.gear.primaryWeapon.itemId, sword.itemId)
            self.assertEqual(len(loaded.gear.inventory), 2)
            self.assertEqual(len(loaded.achievements), 1)
            self.assertEqual(len(loaded.buffs), 1)

            self.assertIn(character_id, reloaded_context.characterbook_overview)

    def test_achievement_with_multiple_bonuses_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, item_service, character_service, characters_dir = self._build_services(temp_dir)
            sword = self._create_item(item_service, "Multi Bonus Sword", slot="PRIMARY_WEAPON")
            self.assertIsNotNone(sword)

            payload = {
                "name": "Multi Bonus Hero",
                "gear": {
                    "head_item_id": "",
                    "neck_item_id": "",
                    "body_item_id": "",
                    "hands_item_id": "",
                    "ring_item_id": "",
                    "legs_item_id": "",
                    "feet_item_id": "",
                    "primary_weapon_item_id": sword.itemId,
                    "offhand_item_id": "",
                    "inventory_item_ids": [],
                },
                "achievements": [
                    {
                        "name": "Dual Blessing",
                        "title": "Favored",
                        "bonuses": [
                            {
                                "bonusType": "FLAT",
                                "attributeBonus": {"attribute": "PHYSICAL_POWER", "bonus": 2},
                                "affinities": None,
                                "nanoMultiplier": 0.0,
                                "reason": "Blessing A",
                                "permanent": True,
                            },
                            {
                                "bonusType": "PERCENTAGE",
                                "attributeBonus": {"attribute": "MAGIC_POWER", "bonus": 1},
                                "affinities": None,
                                "nanoMultiplier": 0.1,
                                "reason": "Blessing B",
                                "permanent": False,
                            },
                        ],
                    }
                ],
                "buffs": [],
            }

            character_id, _ = character_service.create_character_from_dict(payload)
            character_path = characters_dir / f"{character_id}.json"
            raw = json.loads(character_path.read_text(encoding="utf-8"))
            achievements = raw.get("character_state", {}).get("achievements", [])
            self.assertEqual(len(achievements), 1)
            self.assertEqual(len(achievements[0].get("bonuses", [])), 2)

            character_service.load_characters()
            loaded = character_service.get_character(character_id)
            self.assertIsNotNone(loaded)
            self.assertEqual(len(loaded.achievements), 1)
            self.assertEqual(len(getattr(loaded.achievements[0], "bonuses", [])), 2)
            self.assertGreaterEqual(len(loaded.ListAllBonuses()), 2)

    def test_missing_race_field_defaults_to_human1(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, _item_service, character_service, characters_dir = self._build_services(temp_dir)

            character_path = characters_dir / "LegacyNoRace0.json"
            payload = {
                "format_version": 1,
                "character_id": "LegacyNoRace0",
                "character_state": {
                    "name": "Legacy No Race",
                    "level": 1,
                    "raceTier": "Tier I",
                },
            }
            character_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

            character_service.load_characters()
            loaded = character_service.get_character("LegacyNoRace0")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.name, "Legacy No Race")
            self.assertEqual(getattr(loaded, "race", None), "Human1")

    def test_missing_gear_item_ids_fallback_without_crash(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, item_service, character_service, _characters_dir = self._build_services(temp_dir)
            known_item = self._create_item(item_service, "Known Sword", slot="PRIMARY_WEAPON")
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

    def test_main_character_stats_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, _item_service, character_service, _characters_dir = self._build_services(temp_dir)

            payload = {
                "name": "Seren",
                "characterType": "MainCharacter",
                "race": "Human1",
                "stats": {
                    "kills": 3,
                    "damageTaken": 12.5,
                    "missionCount": 2,
                    "damageDone": 44.0,
                    "spellsCast": 5,
                    "injuriesTaken": 2,
                    "alliesProtected": 1,
                    "bossesKilled": 1,
                    "elitesKilled": 2,
                    "unitsKilled": {"Goblin Raider 3": 2, "Goblin Raider 4": 1},
                },
            }

            character_id, created = character_service.create_character_from_dict(payload)
            self.assertIsInstance(created, MainCharacter)
            self.assertEqual(created.stats.damageDone, 44.0)
            self.assertEqual(created.stats.spellsCast, 5)
            self.assertEqual(created.stats.unitsKilled.get("Goblin Raider"), 3)

            character_service.load_characters()
            loaded = character_service.get_character(character_id)
            self.assertIsInstance(loaded, MainCharacter)
            self.assertEqual(loaded.stats.kills, 3)
            self.assertEqual(loaded.stats.damageTaken, 12.5)
            self.assertEqual(loaded.stats.missionCount, 2)
            self.assertEqual(loaded.stats.bossesKilled, 1)
            self.assertEqual(loaded.stats.elitesKilled, 2)
            self.assertEqual(loaded.stats.unitsKilled.get("Goblin Raider"), 3)


if __name__ == "__main__":
    unittest.main()
