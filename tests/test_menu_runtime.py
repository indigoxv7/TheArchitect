import unittest

import Globals
import main as game
from menu_functions import MenuContext, load_menus_from_directory, MenuState
from player_functions import Player


class TestMenuRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        game.Initialize()

    def test_replace_placeholders_replaces_emoji_tokens(self):
        player = Player(999, nano=321)
        player.playerName = "TestPlayer"

        text = "Nano $nanoEmoji $nano :nano: {nanoEmoji}"
        replaced = game.ReplacePlaceholders(text, player, MenuContext())

        self.assertIn(Globals.nanoEmoji, replaced)
        self.assertEqual(replaced.count(Globals.nanoEmoji), 3)
        self.assertNotIn("$nanoEmoji", replaced)
        self.assertNotIn(":nano:", replaced)
        self.assertNotIn("{nanoEmoji}", replaced)

    def test_menu_loader_builds_links_and_menu_state(self):
        menus = load_menus_from_directory("menus")
        self.assertIn("mainMenu", menus)
        self.assertIn("partyMembers", menus)
        self.assertIn("character0", menus)

        main_menu_options = [m.uniqueName for m in menus["mainMenu"].Options]
        self.assertIn("partyMembers", main_menu_options)
        self.assertEqual(menus["character0"].menuState, MenuState.CHARACTER)


if __name__ == "__main__":
    unittest.main()
