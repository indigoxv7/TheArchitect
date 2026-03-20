import tempfile
import unittest
from pathlib import Path

from src.domain.Character import Character
from src.domain.player_functions import Player
from src.services.allegiance_service import AllegianceService
from src.services.campaign_service import CampaignService
from src.services.character_service import CharacterService
from src.services.environment_service import EnvironmentService
from src.services.game_context import GameContext
from src.services.item_service import ItemService
from src.services.mission_service import MissionService
from src.services.race_service import RaceService
from src.services.spell_service import SpellService
from src.services.unit_service import UnitService


class TestCampaignService(unittest.TestCase):
    def _build_services(self, temp_dir: str):
        base = Path(temp_dir)
        itembook_path = base / "itembook.json"
        spellbook_path = base / "spellbook.json"
        racebook_path = base / "racebook.json"
        unitbook_path = base / "unitbook.json"
        allegiancebook_path = base / "allegiancebook.json"
        missionbook_path = base / "missionbook.json"
        campaignbook_path = base / "campaignbook.json"
        environmentbook_path = base / "environmentbook.json"
        characters_dir = base / "Characters"

        context = GameContext()
        item_service = ItemService(str(itembook_path), context)
        item_service.load_itembook()
        spell_service = SpellService(str(spellbook_path), context)
        spell_service.load_spellbook()
        character_service = CharacterService(str(characters_dir), context=context, item_service=item_service)
        character_service.load_characters()
        race_service = RaceService(
            racebook_path=str(racebook_path),
            context=context,
            character_service=character_service,
            spell_service=spell_service,
            item_service=item_service,
        )
        race_service.load_racebook()
        unit_service = UnitService(
            unitbook_path=str(unitbook_path),
            context=context,
            race_service=race_service,
            character_service=character_service,
            spell_service=spell_service,
            item_service=item_service,
        )
        unit_service.load_unitbook()
        allegiance_service = AllegianceService(str(allegiancebook_path), context)
        allegiance_service.load_allegiancebook()
        environment_service = EnvironmentService(str(environmentbook_path), context)
        environment_service.load_environmentbook()
        mission_service = MissionService(
            str(missionbook_path), context, allegiance_service, unit_service, environment_service
        )
        mission_service.load_missionbook()
        campaign_service = CampaignService(str(campaignbook_path), context, mission_service)
        campaign_service.load_campaignbook()
        return context, mission_service, campaign_service, campaignbook_path

    @staticmethod
    def _create_simple_mission(mission_service: MissionService, name: str):
        return mission_service.create_mission_from_dict(
            {
                "name": name,
                "objective": {"objectiveType": "SURVIVAL", "requiredHoursSurvived": 1.0},
                "allegianceConfigs": [],
            }
        )

    def test_create_edit_reload_campaignbook(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            context, mission_service, campaign_service, campaignbook_path = self._build_services(temp_dir)
            prologue = self._create_simple_mission(mission_service, "Prologue")
            raid = self._create_simple_mission(mission_service, "Goblin Raid")
            rescue = self._create_simple_mission(mission_service, "Village Rescue")

            campaign = campaign_service.create_campaign_from_dict(
                {
                    "name": "Frontier Arc",
                    "description": "Opening campaign.",
                    "startingMissionIds": [prologue.missionId],
                    "unlockGroups": [
                        {
                            "missionIds": [raid.missionId, rescue.missionId],
                            "requiredCompletedMissionIds": [prologue.missionId],
                            "minimumCharacterLevel": 2,
                        }
                    ],
                }
            )

            self.assertTrue(campaign.campaignId)
            self.assertEqual(campaign.startingMissionIds, [prologue.missionId])
            self.assertEqual(len(campaign.unlockGroups), 1)
            self.assertTrue(campaign.unlockGroups[0].unlockId)
            self.assertIn(campaign.campaignId, context.campaignbook_overview)

            updated = campaign_service.edit_campaign_from_patch(
                campaign.campaignId,
                {
                    "description": "Updated description.",
                    "unlockGroups": [
                        {
                            "unlockId": campaign.unlockGroups[0].unlockId,
                            "missionIds": [raid.missionId],
                            "requiredCompletedMissionIds": [prologue.missionId],
                            "minimumCharacterLevel": 3,
                        }
                    ],
                },
            )
            self.assertEqual(updated.description, "Updated description.")
            self.assertEqual(updated.unlockGroups[0].missionIds, [raid.missionId])
            self.assertEqual(updated.unlockGroups[0].minimumCharacterLevel, 3)

            reloaded_context, reloaded_mission_service, reloaded_campaign_service, _ = self._build_services(temp_dir)
            reloaded_mission_service.load_missionbook()
            reloaded_campaign_service = CampaignService(
                str(campaignbook_path), reloaded_context, reloaded_mission_service
            )
            reloaded_campaign_service.load_campaignbook()
            loaded = reloaded_campaign_service.get_campaign_by_id(campaign.campaignId)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.description, "Updated description.")
            self.assertEqual(loaded.unlockGroups[0].missionIds, [raid.missionId])

    def test_player_progress_unlocks_and_rebuilds(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, mission_service, campaign_service, _campaignbook_path = self._build_services(temp_dir)
            prologue = self._create_simple_mission(mission_service, "Prologue")
            raid = self._create_simple_mission(mission_service, "Goblin Raid")

            campaign = campaign_service.create_campaign_from_dict(
                {
                    "name": "Frontier Arc",
                    "startingMissionIds": [prologue.missionId],
                    "unlockGroups": [
                        {
                            "missionIds": [raid.missionId],
                            "requiredCompletedMissionIds": [prologue.missionId],
                            "minimumCharacterLevel": 2,
                        }
                    ],
                }
            )

            player = Player(101, characters=[Character(name="Hero", level=1)])
            changed = campaign_service.ensure_player_progress(player)
            self.assertTrue(changed)

            progress = player.GetCampaignProgress(campaign.campaignId)
            self.assertIsNotNone(progress)
            self.assertEqual(progress.unlockedMissionIds, [prologue.missionId])
            self.assertEqual(progress.completedMissionIds, [])

            player.characters[0].level = 2
            changed = campaign_service.refresh_player_campaign_progress(
                player, campaign_id=campaign.campaignId, rebuild=False
            )
            self.assertFalse(changed)
            self.assertEqual(progress.unlockedMissionIds, [prologue.missionId])

            changed = campaign_service.mark_mission_completed(player, campaign.campaignId, prologue.missionId)
            self.assertTrue(changed)
            self.assertIn(prologue.missionId, progress.completedMissionIds)
            self.assertIn(raid.missionId, progress.unlockedMissionIds)
            self.assertIn(campaign.unlockGroups[0].unlockId, progress.appliedUnlockIds)

            progress.completedMissionIds = []
            progress.unlockedMissionIds = [prologue.missionId, raid.missionId]
            progress.appliedUnlockIds = [campaign.unlockGroups[0].unlockId]
            campaign_service.refresh_player_campaign_progress(player, campaign_id=campaign.campaignId, rebuild=True)
            self.assertEqual(progress.completedMissionIds, [])
            self.assertEqual(progress.appliedUnlockIds, [])
            self.assertEqual(progress.unlockedMissionIds, [prologue.missionId])

    def test_unlocked_missions_are_deduped_and_complete_everywhere(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, mission_service, campaign_service, _campaignbook_path = self._build_services(temp_dir)
            prologue = self._create_simple_mission(mission_service, "Prologue")
            shared = self._create_simple_mission(mission_service, "Shared Mission")

            first = campaign_service.create_campaign_from_dict(
                {
                    "name": "First Arc",
                    "startingMissionIds": [prologue.missionId, shared.missionId],
                    "unlockGroups": [],
                }
            )
            second = campaign_service.create_campaign_from_dict(
                {
                    "name": "Second Arc",
                    "startingMissionIds": [shared.missionId],
                    "unlockGroups": [],
                }
            )

            player = Player(102, characters=[Character(name="Hero", level=3)])
            campaign_service.ensure_player_progress(player)

            unlocked = campaign_service.list_unlocked_missions(player)
            unlocked_ids = [entry["missionId"] for entry in unlocked]
            self.assertEqual(unlocked_ids.count(shared.missionId), 1)

            shared_entry = next(entry for entry in unlocked if entry["missionId"] == shared.missionId)
            self.assertEqual(shared_entry["campaignIds"], sorted([first.campaignId, second.campaignId]))

            changed = campaign_service.mark_mission_completed_everywhere(player, shared.missionId)
            self.assertTrue(changed)
            self.assertIn(shared.missionId, player.GetCampaignProgress(first.campaignId).completedMissionIds)
            self.assertIn(shared.missionId, player.GetCampaignProgress(second.campaignId).completedMissionIds)


if __name__ == "__main__":
    unittest.main()
