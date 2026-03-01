import json
import tempfile
import unittest
from pathlib import Path

from src.persistence.menu_store import MenuStore
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

            with open(whitelist_path, "w", encoding="utf-8") as f:
                json.dump(["456", "bad", 789], f)

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

    def test_menu_store_loads_required_menu_set(self):
        store = MenuStore("GameData/Menus")
        menus = store.load_menus()
        self.assertIn("mainMenu", menus)
        self.assertIn("newPlayerMenu", menus)


if __name__ == "__main__":
    unittest.main()

