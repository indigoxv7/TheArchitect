import unittest

from src.config import Globals
import main as game
from src.domain.player_functions import Player
from src.domain.Items import Weapon
from src.domain.CharacterUtil import EquipSlot
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

    def test_inventory_placeholder_uses_player_inventory(self):
        sample_player = Player(2)
        sample_player.playerName = "Tester"
        sample_player.inventory = [
            Weapon(name="Rusty Dagger", slot=EquipSlot.PRIMARY_WEAPON, itemId="RustyDagger0", damageMin=4, damageMax=6),
            "Mysterious Rock",
        ]

        rendered = game.menu_service.replace_placeholders(
            "Inventory ($inventoryCount items)\n$inventoryList",
            sample_player,
            MenuContext(),
        )

        self.assertIn("Inventory (2 items)", rendered)
        self.assertIn("1. Rusty Dagger [RustyDagger0]", rendered)
        self.assertIn("2. Mysterious Rock", rendered)

    def test_menu_loader_builds_links_and_menu_state(self):
        menus = load_menus_from_directory("GameData/Menus")
        self.assertIn("mainMenu", menus)
        self.assertIn("partyMembers", menus)
        self.assertIn("character0", menus)
        self.assertIn("spellbookMenu", menus)

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

    def test_editor_menus_hidden_from_main_menu_for_all_users(self):
        sample_player = Player(1)
        sample_player.playerName = "Tester"

        non_admin_message = OriginalMessage(sample_player, is_developer_admin=False)
        game.menu_service.update_menu_values(non_admin_message, game.context.root_menu)
        non_admin_visible = [
            m.uniqueName for m, _ in game.menu_service.get_visible_child_menus(game.context.root_menu, non_admin_message)
        ]

        admin_message = OriginalMessage(sample_player, is_developer_admin=True)
        game.menu_service.update_menu_values(admin_message, game.context.root_menu)
        admin_visible = [
            m.uniqueName for m, _ in game.menu_service.get_visible_child_menus(game.context.root_menu, admin_message)
        ]

        for hidden_editor_menu in (
            "spellbookMenu",
            "itembookMenu",
            "attributesEditorMenu",
            "gearEditorMenu",
            "bonusEditorMenu",
            "achievementEditorMenu",
        ):
            self.assertNotIn(hidden_editor_menu, non_admin_visible)
            self.assertNotIn(hidden_editor_menu, admin_visible)


if __name__ == "__main__":
    unittest.main()
