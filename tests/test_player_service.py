import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.domain.character import Character
from src.domain.player_functions import Player, save_player
from src.services.game_context import GameContext
from src.services.player_service import PlayerService


class TestPlayerService(unittest.TestCase):
    def _build_service(self, temp_dir: str, bot=None):
        context = GameContext()
        player_saves = Path(temp_dir) / "PlayerSaves"
        roster_path = Path(temp_dir) / "ExistingPlayersRoster.json"
        service = PlayerService(
            bot=bot,
            guild_id=123,
            context=context,
            player_save_directory=str(player_saves),
            existing_players_roster_path=str(roster_path),
        )
        service.initialize_storage()
        return context, service, player_saves

    def test_clone_character_from_template_creates_independent_player_instance(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            context, service, _player_saves = self._build_service(temp_dir)
            template = Character(name="Template Hero", race="Elf2")
            template.description = "Global template"
            context.all_characters["TemplateHero0"] = template

            clone = service.clone_character_from_template("TemplateHero0", existing_characters=[])

            self.assertIsNotNone(clone)
            self.assertIsNot(clone, template)
            self.assertEqual(clone.name, "Template Hero")
            self.assertEqual(clone.race, "Elf2")
            self.assertTrue(getattr(clone, "playerInstanceId", ""))

            clone.description = "Player-owned copy"
            self.assertEqual(template.description, "Global template")

    def test_get_player_sync_migrates_missing_player_instance_ids(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, service, player_saves = self._build_service(temp_dir)
            save_path = player_saves / "101.json"

            legacy_character = Character(name="Legacy Hero")
            legacy_character.playerInstanceId = ""
            player = Player(101, characters=[legacy_character])
            save_player(player, str(save_path))

            loaded = service.get_player_sync(101)

            self.assertIsNotNone(loaded)
            self.assertEqual(len(loaded.characters), 1)
            self.assertTrue(loaded.characters[0].playerInstanceId)

            payload = json.loads(save_path.read_text(encoding="utf-8"))
            saved_character = payload["player_state"]["__state__"]["characters"][0]["__state__"]
            self.assertTrue(saved_character.get("playerInstanceId"))

    def test_legacy_character_party_migrates_to_player_mission_party_and_clears_stats(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, service, player_saves = self._build_service(temp_dir)
            save_path = player_saves / "202.json"

            legacy_character = Character(name="Legacy Vanguard")
            legacy_character.party = 0
            legacy_character.stats = {"kills": 9}
            player = Player(202, characters=[legacy_character])
            save_player(player, str(save_path))

            loaded = service.get_player_sync(202)

            self.assertIsNotNone(loaded)
            self.assertEqual(len(loaded.characters), 1)
            migrated_character = loaded.characters[0]
            self.assertFalse(hasattr(migrated_character, "party"))
            self.assertFalse(hasattr(migrated_character, "stats"))
            self.assertEqual(loaded.GetMissionPartyCharacterIds(), [migrated_character.playerInstanceId])

            payload = json.loads(save_path.read_text(encoding="utf-8"))
            saved_character = payload["player_state"]["__state__"]["characters"][0]["__state__"]
            self.assertFalse("party" in saved_character)
            self.assertFalse("stats" in saved_character)
            self.assertEqual(
                payload["player_state"]["__state__"].get("missionPartyCharacterIds"),
                [migrated_character.playerInstanceId],
            )

    def test_get_player_recovers_from_empty_save_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            context, service, player_saves = self._build_service(temp_dir)
            save_path = player_saves / "303.json"
            save_path.write_text("", encoding="utf-8")

            player = asyncio.run(service.get_player(303))

            self.assertEqual(player.discordID, 303)
            self.assertTrue(player.isNewPlayer)
            self.assertEqual(player.playerName, "PlayerName")
            self.assertEqual(context.player_cache[303], player)
            self.assertTrue(save_path.exists())
            payload = json.loads(save_path.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("format_version"), 1)
            self.assertEqual(payload["player_state"]["__state__"].get("playerName"), "PlayerName")

            backups = list(player_saves.glob("303.corrupt-*.json"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(encoding="utf-8"), "")

    def test_get_player_sync_uses_cached_discord_name_when_available(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bot = SimpleNamespace(
                get_guild=lambda _guild_id: None,
                get_user=lambda _discord_id: SimpleNamespace(name="FallbackUser", display_name="Cached Nick"),
            )
            _context, service, player_saves = self._build_service(temp_dir, bot=bot)
            save_path = player_saves / "404.json"

            player = Player(404)
            save_player(player, str(save_path))

            loaded = service.get_player_sync(404)

            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.playerName, "Cached Nick")
            payload = json.loads(save_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["player_state"]["__state__"].get("playerName"), "Cached Nick")


if __name__ == "__main__":
    unittest.main()
