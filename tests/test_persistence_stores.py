import json
import tempfile
import unittest
from pathlib import Path

from src.persistence.campaignbook_store import CampaignbookStore
from src.persistence.character_store import CharacterStore
from src.persistence.menu_store import MenuStore
from src.persistence.racebook_store import RacebookStore
from src.persistence.roster_store import ExistingPlayersRosterStore
from src.persistence.whitelist_store import WhitelistStore


class TestPersistenceStores(unittest.TestCase):
    def test_whitelist_store_creates_and_loads_ids(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            whitelist_path = Path(temp_dir) / "AdminWhitelist.json"
            store = WhitelistStore(str(whitelist_path), default_admin_id=123)

            ids = store.load_ids()
            self.assertTrue(whitelist_path.exists())
            self.assertEqual(ids, [123])

            with open(whitelist_path, "w", encoding="utf-8") as file:
                json.dump(["456", "bad", 789], file)

            ids = store.load_ids()
            self.assertEqual(ids, [456, 789])

    def test_roster_store_save_load_discover(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            saves_dir = Path(temp_dir) / "PlayerSaves"
            roster_path = Path(temp_dir) / "ExistingPlayersRoster.json"
            store = ExistingPlayersRosterStore(str(roster_path), str(saves_dir))

            store.ensure_save_directory()
            self.assertTrue(saves_dir.exists())

            existing_players = {100: True, 200: False}
            store.save_roster(existing_players)
            loaded = store.load_roster()
            self.assertEqual(loaded, {100: False, 200: False})

            (saves_dir / "100.json").write_text("{}", encoding="utf-8")
            (saves_dir / "300.json").write_text("{}", encoding="utf-8")
            (saves_dir / "notes.txt").write_text("x", encoding="utf-8")

            discovered = store.discover_save_ids()
            self.assertEqual(discovered, {100, 300})

    def test_character_store_directory_and_file_behavior(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            characters_dir = Path(temp_dir) / "Characters"
            store = CharacterStore(str(characters_dir))

            store.ensure_directory()
            self.assertTrue(characters_dir.exists())
            self.assertEqual(store.list_character_ids(), [])

            payload = {
                "format_version": 1,
                "character_id": "TestCharacter0",
                "character_state": {"name": "Test Character", "level": 1},
            }
            store.save_character_file("TestCharacter0", payload)

            loaded = store.load_character_file("TestCharacter0")
            self.assertIsInstance(loaded, dict)
            self.assertEqual(loaded.get("character_id"), "TestCharacter0")

            ids = store.list_character_ids()
            self.assertEqual(ids, ["TestCharacter0"])

            store.delete_character_file("TestCharacter0")
            self.assertEqual(store.list_character_ids(), [])

    def test_racebook_store_load_save_behavior(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            racebook_path = Path(temp_dir) / "racebook.json"
            store = RacebookStore(str(racebook_path))

            loaded = store.load()
            self.assertEqual(loaded.get("format_version"), 1)
            self.assertEqual(loaded.get("races"), [])

            payload = {
                "format_version": 1,
                "races": [{"raceId": "Human0", "name": "Human"}],
            }
            store.save(payload)

            reloaded = store.load()
            self.assertEqual(reloaded.get("races", [])[0].get("raceId"), "Human0")

    def test_campaignbook_store_load_save_behavior(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            campaignbook_path = Path(temp_dir) / "campaignbook.json"
            store = CampaignbookStore(str(campaignbook_path))

            loaded = store.load()
            self.assertEqual(loaded.get("format_version"), 1)
            self.assertEqual(loaded.get("campaigns"), [])

            payload = {
                "format_version": 1,
                "campaigns": [{"campaignId": "Frontier0", "name": "Frontier Arc"}],
            }
            store.save(payload)

            reloaded = store.load()
            self.assertEqual(reloaded.get("campaigns", [])[0].get("campaignId"), "Frontier0")

    def test_menu_store_loads_required_menu_set(self):
        store = MenuStore("GameData/Menus")
        menus = store.load_menus()
        self.assertIn("mainMenu", menus)
        self.assertIn("newPlayerMenu", menus)


if __name__ == "__main__":
    unittest.main()
