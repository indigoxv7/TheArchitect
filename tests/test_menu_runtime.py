import unittest

from src.config import Globals
import main as game
from src.domain.player_functions import Player
from src.services.menu_runtime_service import OriginalMessage
from src.ui.menu_functions import MenuContext, MenuState, load_menus_from_directory


class TestMenuRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        game.initialize_game()

    def test_replace_placeholders_replaces_emoji_tokens(self):
        player = Player(999, nano=321)
        player.playerName = "TestPlayer"

        text = "Nano $nanoEmoji $nano :nano: {nanoEmoji}"
        replaced = game.menu_service.replace_placeholders(text, player, MenuContext())

        self.assertIn(Globals.nanoEmoji, replaced)
        self.assertEqual(replaced.count(Globals.nanoEmoji), 3)
        self.assertNotIn("$nanoEmoji", replaced)
        self.assertNotIn(":nano:", replaced)
        self.assertNotIn("{nanoEmoji}", replaced)

    def test_menu_loader_builds_links_and_menu_state(self):
        menus = load_menus_from_directory("GameData/Menus")
        self.assertIn("mainMenu", menus)
        self.assertIn("partyMembers", menus)
        self.assertIn("character0", menus)

        main_menu_options = [m.uniqueName for m in menus["mainMenu"].Options]
        self.assertIn("partyMembers", main_menu_options)
        self.assertEqual(menus["character0"].menuState, MenuState.CHARACTER)

    def test_visible_children_comes_from_service(self):
        sample_player = Player(1)
        sample_player.playerName = "Tester"
        msg = OriginalMessage(sample_player)

        game.menu_service.update_menu_values(msg, game.context.root_menu)
        visible = game.menu_service.get_visible_child_menus(game.context.root_menu, msg)

        self.assertGreater(len(visible), 0)


if __name__ == "__main__":
    unittest.main()

