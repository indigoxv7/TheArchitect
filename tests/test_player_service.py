import json
import tempfile
import unittest
from pathlib import Path

from src.domain.Character import Character
from src.domain.player_functions import Player, save_player
from src.services.game_context import GameContext
from src.services.player_service import PlayerService


class TestPlayerService(unittest.TestCase):
    def _build_service(self, temp_dir: str):
        context = GameContext()
        player_saves = Path(temp_dir) / 'PlayerSaves'
        roster_path = Path(temp_dir) / 'ExistingPlayersRoster.json'
        service = PlayerService(
            bot=None,
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
            template = Character(name='Template Hero', race='Elf2')
            template.description = 'Global template'
            context.all_characters['TemplateHero0'] = template

            clone = service.clone_character_from_template('TemplateHero0', existing_characters=[])

            self.assertIsNotNone(clone)
            self.assertIsNot(clone, template)
            self.assertEqual(clone.name, 'Template Hero')
            self.assertEqual(clone.race, 'Elf2')
            self.assertTrue(getattr(clone, 'playerInstanceId', ''))

            clone.description = 'Player-owned copy'
            self.assertEqual(template.description, 'Global template')

    def test_get_player_sync_migrates_missing_player_instance_ids(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, service, player_saves = self._build_service(temp_dir)
            save_path = player_saves / '101.json'

            legacy_character = Character(name='Legacy Hero')
            legacy_character.playerInstanceId = ''
            player = Player(101, characters=[legacy_character])
            save_player(player, str(save_path))

            loaded = service.get_player_sync(101)

            self.assertIsNotNone(loaded)
            self.assertEqual(len(loaded.characters), 1)
            self.assertTrue(loaded.characters[0].playerInstanceId)

            payload = json.loads(save_path.read_text(encoding='utf-8'))
            saved_character = payload['player_state']['__state__']['characters'][0]['__state__']
            self.assertTrue(saved_character.get('playerInstanceId'))


if __name__ == '__main__':
    unittest.main()
