import tempfile
import unittest
from pathlib import Path

from src.persistence.active_mission_store import ActiveMissionStore


class TestActiveMissionStore(unittest.TestCase):
    def test_save_load_delete_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ActiveMissionStore(str(Path(temp_dir) / "ActiveMissions"))
            payload = {
                "format_version": 1,
                "mission_run_state": {
                    "playerId": 123,
                    "missionId": "Mission0",
                    "missionName": "Test Mission",
                },
            }

            store.save_mission_file(123, payload)
            loaded = store.load_mission_file(123)

            self.assertEqual(loaded["mission_run_state"]["missionId"], "Mission0")
            self.assertEqual(store.list_player_ids(), [123])

            store.delete_mission_file(123)
            self.assertIsNone(store.load_mission_file(123))


if __name__ == "__main__":
    unittest.main()
