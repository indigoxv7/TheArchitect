import json
import tempfile
import unittest
from pathlib import Path

from src.domain.campaign import CampaignProgress
from src.domain.Character import Character
from src.domain.player_functions import Player, load_player


class TestPlayerSave(unittest.TestCase):
    def test_energy_regen_uses_rate_and_updates_timestamp(self):
        player = Player(
            100,
            energy=10,
            energyCap=50,
            energyLastCalculatedTime=100.0,
            energyRegenRatePerSecond=0.5,
        )

        current_energy = player.GetCurrentEnergy(currentTime=104.0, persist=False)

        self.assertEqual(current_energy, 12)
        self.assertEqual(player.energyLastCalculatedTime, 104.0)

    def test_json_save_load_and_autosave(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "100.json"

            player = Player(100, nano=5)
            player.AttachSavePath(str(save_path), enableAutoSave=True)
            player.nano = 42

            self.assertTrue(save_path.exists())
            with open(save_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            self.assertEqual(payload.get("format_version"), 1)

            loaded = load_player(str(save_path))
            self.assertEqual(loaded.nano, 42)

            loaded.nano = 77
            reloaded = load_player(str(save_path))
            self.assertEqual(reloaded.nano, 77)

    def test_mission_party_ids_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "200.json"

            first = Character(name="First Hero")
            first.playerInstanceId = "FirstHero0"
            second = Character(name="Second Hero")
            second.playerInstanceId = "SecondHero1"
            player = Player(200, characters=[first, second], missionPartyCharacterIds=["SecondHero1"])
            player.AttachSavePath(str(save_path), enableAutoSave=False)
            player.Save()

            loaded = load_player(str(save_path))

            self.assertEqual(loaded.missionPartyCharacterIds, ["SecondHero1"])
            self.assertEqual(loaded.GetMissionPartyCharacterIds(), ["SecondHero1"])

    def test_campaign_progress_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "300.json"
            progress = CampaignProgress(
                campaignId="FrontierArc0",
                unlockedMissionIds=["Prologue0", "Raid1"],
                completedMissionIds=["Prologue0"],
                appliedUnlockIds=["FrontierArc0Unlock0"],
            )
            player = Player(300, campaignProgressById={"FrontierArc0": progress})
            player.AttachSavePath(str(save_path), enableAutoSave=False)
            player.Save()

            loaded = load_player(str(save_path))
            loaded_progress = loaded.GetCampaignProgress("FrontierArc0")

            self.assertIsNotNone(loaded_progress)
            self.assertEqual(loaded_progress.unlockedMissionIds, ["Prologue0", "Raid1"])
            self.assertEqual(loaded_progress.completedMissionIds, ["Prologue0"])
            self.assertEqual(loaded_progress.appliedUnlockIds, ["FrontierArc0Unlock0"])

    def test_load_player_rejects_empty_save_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "empty.json"
            save_path.write_text("", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "is empty"):
                load_player(str(save_path))


if __name__ == "__main__":
    unittest.main()
