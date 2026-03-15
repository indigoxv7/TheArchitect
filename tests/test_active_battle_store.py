import tempfile
import unittest
from pathlib import Path

from src.persistence.active_battle_store import ActiveBattleStore


class TestActiveBattleStore(unittest.TestCase):
    def test_save_load_delete_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ActiveBattleStore(str(Path(temp_dir) / "ActiveBattles"))
            payload = {
                "format_version": 1,
                "battle_state": {
                    "player_id": 123,
                    "battle_id": "battle_123",
                },
            }

            store.save_battle_file(123, payload)
            loaded = store.load_battle_file(123)

            self.assertEqual(loaded["battle_state"]["battle_id"], "battle_123")
            self.assertEqual(store.list_player_ids(), [123])

            store.delete_battle_file(123)
            self.assertIsNone(store.load_battle_file(123))


if __name__ == "__main__":
    unittest.main()
