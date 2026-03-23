import copy
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
from src.domain.location_content import NodeGenerationProfile, SceneDescriptionMode
from src.services.local_scene_description_service import LocalSceneRenderResult
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

    def test_main_menu_mission_button_uses_real_emoji(self):
        menus = load_menus_from_directory("GameData/Menus")

        self.assertEqual(menus["missionAction"].myEmoji, "\U0001f30c")

    def test_how_to_play_menu_exposes_customize_player_action(self):
        menus = load_menus_from_directory("GameData/Menus")

        option_names = [option.uniqueName for option in menus["HowToPlayMenu"].Options]
        self.assertIn("mainMenu", option_names)
        self.assertIn("customizePlayerAction", option_names)

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


    def test_mission_runtime_reveals_hazards_only_after_spotting_roll(self):
        player = game.player_service.get_player_sync(191980469670248448)
        mission = game.mission_service.get_mission_by_id("GoblinEliminationlvl00")

        self.assertIsNotNone(player)
        self.assertIsNotNone(mission)
        if not getattr(player, "characters", []):
            template_character = copy.deepcopy(next(iter(game.context.all_characters.values())))
            template_character.playerInstanceId = "HazardSpotter0"
            if not getattr(template_character, "name", ""):
                template_character.name = "Hazard Spotter"
            ensure_defaults = getattr(template_character, "EnsureRuntimeDefaults", None)
            if callable(ensure_defaults):
                ensure_defaults()
            player.characters = [template_character]

        state = game.mission_runtime_service._generate_state(player, mission, ["TheApocalypseBegins0"])
        state.partyState.selectedCharacterInstanceIds = [str(getattr(player.characters[0], "playerInstanceId", "") or "")]
        node_state = state.get_node(int(state.currentNodeId))

        self.assertIsNotNone(node_state)
        self.assertIsNotNone(node_state.nodeContentState)

        node_state.nodeContentState.hazardTags = ["spike_trap"]
        node_state.nodeContentState.canonicalTags = ["jungle", "lookout", "spike_trap"]
        node_state.revealedHazardTags = []
        node_state.hazardSpottersByTag = {}

        class AlwaysSpot:
            @staticmethod
            def random():
                return 0.0

        self.assertNotIn("spike_trap", game.mission_runtime_service._visible_node_tags(node_state))
        discoveries = game.mission_runtime_service._attempt_hazard_spotting(player, state, node_state, rng=AlwaysSpot())

        self.assertTrue(discoveries)
        self.assertIn("spike trap", discoveries[0].lower())
        self.assertIn("spike_trap", node_state.revealedHazardTags)
        self.assertIn("spike_trap", game.mission_runtime_service._visible_node_tags(node_state))


    def test_mission_runtime_prefetches_local_descriptions_from_start_outward(self):
        player = game.player_service.get_player_sync(191980469670248448)
        mission = game.mission_service.get_mission_by_id("GoblinEliminationlvl00")

        self.assertIsNotNone(player)
        self.assertIsNotNone(mission)

        state = game.mission_runtime_service._generate_state(player, mission, ["TheApocalypseBegins0"])
        game.context.active_missions[int(state.playerId)] = state

        profile = NodeGenerationProfile(
            name="Test Runtime Local",
            rendererMode=SceneDescriptionMode.LOCAL_ONLY,
            localRendererKey="ollama:test-local",
            generationProfileId="TestRuntimeLocal0",
        )

        class FakeLocalSceneService:
            def __init__(self):
                self.calls = []

            def default_runtime_option_key(self):
                return "ollama:test-local"

            def describe_scene_with_history(self, prompt_packet, option_key, render_state=None):
                node_packet = dict(prompt_packet.get("node") or {})
                node_id = int(node_packet.get("node_id", 0) or 0)
                self.calls.append(node_id)
                next_turn = int(dict(render_state or {}).get("turn", 0) or 0) + 1
                return LocalSceneRenderResult(
                    text=f"Rendered node {node_id}",
                    render_state={"turn": next_turn},
                    node_signature=str(node_id),
                    style_variant="landmark_first",
                    telemetry={},
                )

        fake_service = FakeLocalSceneService()
        runtime = game.mission_runtime_service
        old_local_scene_service = runtime.local_scene_service
        old_profile_getter = runtime._generation_profile_for_state
        old_save_active_mission = runtime.save_active_mission
        try:
            runtime.local_scene_service = fake_service
            runtime._generation_profile_for_state = lambda _state: profile
            runtime.save_active_mission = lambda _state: None

            current_node_state = state.get_node(int(state.currentNodeId))
            asyncio.run(runtime._ensure_runtime_local_description(state, current_node_state))
            expected_prefetch_order = runtime._ordered_prefetch_node_ids(state, exclude_current=True)
            asyncio.run(runtime._prefetch_runtime_local_descriptions_for_state(state, exclude_current=True))

            self.assertEqual(fake_service.calls[0], int(state.currentNodeId))
            self.assertEqual(fake_service.calls[1:], expected_prefetch_order)
            for node_state in state.nodeStates:
                self.assertEqual(node_state.nodeContentState.localDescriptionRendererKey, "ollama:test-local")
                self.assertTrue(node_state.nodeContentState.localDescription.startswith("Rendered node"))
        finally:
            runtime.local_scene_service = old_local_scene_service
            runtime._generation_profile_for_state = old_profile_getter
            runtime.save_active_mission = old_save_active_mission
            game.context.active_missions.pop(int(state.playerId), None)


if __name__ == "__main__":
    unittest.main()
