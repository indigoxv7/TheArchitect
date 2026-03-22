import unittest

import asyncio
import json
import tempfile
from pathlib import Path

from src.config import nanoEmoji
import main as game
from src.domain.player_functions import Player
from src.domain.items import Weapon
from src.domain.character_util import EquipSlot
from src.persistence.menu_store import load_menus_from_directory
from src.services.menu_runtime import ConsoleMenuInterface, OriginalMessage
from src.ui.menu import MenuContext, MenuState


class TestMenuRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        game.initialize_game()

    def test_replace_placeholders_replaces_emoji_tokens(self):
        player = Player(999, nano=1450)
        player.playerName = "TestPlayer"

        text = "Nano $nanoEmoji $nano :nano: {nanoEmoji}"
        replaced = game.menu_service.replace_placeholders(text, player, MenuContext())

        self.assertIn(nanoEmoji, replaced)
        self.assertEqual(replaced.count(nanoEmoji), 3)
        self.assertNotIn("$nanoEmoji", replaced)
        self.assertNotIn(":nano:", replaced)
        self.assertIn("1.450 K", replaced)
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

    def test_main_menu_mission_actions_use_real_emojis(self):
        menus = load_menus_from_directory("GameData/Menus")

        self.assertEqual(menus["scavengingMissionAction"].myEmoji, "🏚️")
        self.assertEqual(menus["portalMissionAction"].myEmoji, "🌌")

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
            m.uniqueName
            for m, _ in game.menu_service.get_visible_child_menus(game.context.root_menu, non_admin_message)
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

    def test_display_menu_updates_player_name_from_live_interface_name(self):
        sample_player = Player(555)
        sample_player.playerName = "Old Saved Name"

        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "555.json"
            sample_player.AttachSavePath(str(save_path), enableAutoSave=True)
            sample_player.Save()

            original_get_player = game.menu_runtime_service.player_service.get_player

            async def fake_get_player(_discord_id: int):
                return sample_player

            game.menu_runtime_service.player_service.get_player = fake_get_player
            try:
                interface = ConsoleMenuInterface(user_id=555, display_name="Fresh Discord Nick")
                asyncio.run(game.menu_runtime_service.display_menu_with_interface(interface, game.context.root_menu))
            finally:
                game.menu_runtime_service.player_service.get_player = original_get_player

            self.assertEqual(sample_player.playerName, "Fresh Discord Nick")
            payload = json.loads(save_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["player_state"]["__state__"].get("playerName"), "Fresh Discord Nick")

    def test_generated_mission_state_keeps_hostile_units_and_starts_active(self):
        player = game.player_service.get_player_sync(191980469670248448)
        mission = game.mission_service.get_mission_by_id("GoblinEliminationlvl00")

        self.assertIsNotNone(player)
        self.assertIsNotNone(mission)

        state = game.mission_runtime_service._generate_state(player, mission, ["TheApocalypseBegins0"])

        self.assertEqual(state.status.name, "ACTIVE")
        self.assertEqual(state.missionObjectiveStatus.name, "IN_PROGRESS")
        self.assertGreater(state.missionStatistics.totalStartingEnemies, 0)
        self.assertGreater(
            sum(1 for node_state in state.nodeStates if node_state.living_unit_states()),
            0,
        )


if __name__ == "__main__":
    unittest.main()
