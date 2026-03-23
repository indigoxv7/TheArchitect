import json
import tempfile
import unittest
from pathlib import Path

from src.domain.location_content import DescriptionPack, GeneratedFeatureState, GeneratedNodeContent, SettingContext
from src.domain.mission import MissionRunState, MissionTemplate
from src.services.environment_service import EnvironmentService
from src.services.game_context import GameContext
from src.services.mission_map import (
    MissionMapOverlay,
    apply_overlay_to_node_contents,
    build_map_settings_from_range,
    build_scene_description_prompt_packet,
    generate_mission_map,
    generate_node_content_preview,
    mission_map_to_dict,
    render_local_node_description,
)


class TestLocationContentGeneration(unittest.TestCase):
    def _build_service(self, temp_dir: str):
        environmentbook_path = Path(temp_dir) / "environmentbook.json"
        context = GameContext()
        service = EnvironmentService(str(environmentbook_path), context)
        service.load_environmentbook()
        return context, service

    @staticmethod
    def _build_mission(**overrides):
        payload = {
            "name": "Node Preview Mission",
            "objective": {"objectiveType": "SURVIVAL", "requiredHoursSurvived": 1.0},
            "biomeId": "Jungle0",
            "terrainPoolIds": [],
            "climatePoolIds": [],
            "nodeGenerationProfileId": "BalancedLocal0",
            "descriptionPackId": "DefaultArrival0",
            "portalMission": True,
            "mapGenerationRange": {
                "totalNodesLow": 8,
                "totalNodesHigh": 8,
                "narrownessLow": 0.35,
                "narrownessHigh": 0.35,
                "connectednessLow": 0.3,
                "connectednessHigh": 0.3,
                "deadEndLikelihoodLow": 0.2,
                "deadEndLikelihoodHigh": 0.2,
                "nodeJitterFractionLow": 0.2,
                "nodeJitterFractionHigh": 0.2,
            },
        }
        payload.update(overrides)
        return MissionTemplate.from_dict(payload)

    def test_environment_service_seeds_legacy_jungle_alias(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, service = self._build_service(temp_dir)
            self.assertIsNotNone(service.get_biome_by_id("Jungle0"))
            self.assertIsNotNone(service.get_biome_by_id("JungleFrontier0"))

    def test_node_generation_respects_override_pools_and_produces_structured_nodes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, service = self._build_service(temp_dir)
            mission = self._build_mission(
                terrainPoolIds=["RuinedFoundations0"],
                climatePoolIds=["StormWet0"],
            )
            mission_map = generate_mission_map(build_map_settings_from_range(mission.mapGenerationRange, seed=123))

            setting_context, node_contents = generate_node_content_preview(service, mission_map, mission, seed=123)

            self.assertEqual(setting_context.terrainId, "RuinedFoundations0")
            self.assertEqual(setting_context.climateId, "StormWet0")
            self.assertEqual(len(node_contents), mission_map.node_count)

            sample = node_contents[mission_map.start_node_id]
            self.assertTrue(sample.roleId)
            self.assertTrue(sample.roleName)
            self.assertTrue(sample.canonicalTags)
            self.assertTrue(sample.localDescription)
            self.assertTrue(set(sample.settingContextTags).issubset(set(sample.canonicalTags)))

    def test_overlay_application_adds_generated_hook_and_hostile_tags(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, service = self._build_service(temp_dir)
            mission = self._build_mission()
            mission_map = generate_mission_map(build_map_settings_from_range(mission.mapGenerationRange, seed=321))
            _setting_context, node_contents = generate_node_content_preview(service, mission_map, mission, seed=321)
            node_ids = sorted(node_contents.keys())

            overlay = MissionMapOverlay(
                unitsByNode={node_ids[0]: [object()]},
                nanoByNode={node_ids[1]: 180},
                clueTargetNodeByNode={node_ids[2]: node_ids[0]},
            )
            updated = apply_overlay_to_node_contents(node_contents, overlay)

            self.assertIn("hostile_presence", updated[node_ids[0]].hookTags)
            self.assertIn("hostile_presence", updated[node_ids[0]].canonicalTags)
            self.assertTrue(any(hook.hookType == "TREASURE" for hook in updated[node_ids[1]].hookStates))
            self.assertTrue(any(hook.hookType == "CLUE" for hook in updated[node_ids[2]].hookStates))

    def test_run_state_round_trip_preserves_setting_and_node_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, service = self._build_service(temp_dir)
            mission = self._build_mission()
            mission_map = generate_mission_map(build_map_settings_from_range(mission.mapGenerationRange, seed=222))
            setting_context, node_contents = generate_node_content_preview(service, mission_map, mission, seed=222)
            sample_node = node_contents[mission_map.start_node_id]

            state = MissionRunState.from_dict(
                {
                    "playerId": 1,
                    "missionId": "TestMission0",
                    "missionName": mission.name,
                    "missionTemplate": mission.to_dict(),
                    "campaignIds": ["Campaign0"],
                    "status": "ACTIVE",
                    "selectedCharacterInstanceIds": ["Hero0"],
                    "missionMap": mission_map_to_dict(mission_map),
                    "currentNodeId": mission_map.start_node_id,
                    "visitedNodeIds": [mission_map.start_node_id],
                    "nodeStates": [
                        {
                            "nodeId": mission_map.start_node_id,
                            "nodeContentState": sample_node.to_dict(),
                        }
                    ],
                    "settingContextState": setting_context.to_dict(),
                }
            )

            round_trip = MissionRunState.from_dict(state.to_dict())
            self.assertIsNotNone(round_trip.settingContextState)
            self.assertEqual(round_trip.settingContextState.terrainId, setting_context.terrainId)
            self.assertEqual(round_trip.nodeStates[0].nodeContentState.sceneDisplayName, sample_node.sceneDisplayName)
            self.assertEqual(round_trip.nodeStates[0].nodeContentState.canonicalTags, sample_node.canonicalTags)


    def test_scene_prompt_and_local_renderer_hide_unrevealed_hazards(self):
        setting_context = SettingContext(
            biomeId="GoblinJungle0",
            biomeName="Goblin Jungle",
            terrainId="GoblinRopeWalks0",
            terrainName="Rope Walks",
            climateId="CanopySmoke0",
            climateName="Canopy Smoke",
            settingContextTags=["jungle", "goblin_territory"],
        )
        node_content = GeneratedNodeContent(
            nodeId=1,
            sceneDisplayName="Rope Walks | Sentry Roost",
            battleTerrainLabel="Rope Walks | Sentry Roost",
            roleId="SentryRoost0",
            roleName="Sentry Roost",
            roleTags=["lookout"],
            settingContextTags=["jungle", "goblin_territory"],
            featureTags=["spike_trap", "totem_marker"],
            affordanceTags=["observe"],
            hazardTags=["spike_trap"],
            hookTags=["clue"],
            memoryTags=["spike_trap", "totem_marker"],
            canonicalTags=["jungle", "lookout", "spike_trap", "totem_marker", "clue"],
            featureStates=[
                GeneratedFeatureState(
                    featureId="HiddenTrap0",
                    name="Spike Trap",
                    category="hazard",
                    tags=["spike_trap"],
                    hazardTags=["spike_trap"],
                    visibleTags=[],
                ),
                GeneratedFeatureState(
                    featureId="Totem0",
                    name="Totem Marker",
                    category="marker",
                    tags=["totem_marker"],
                    visibleTags=["totem marker"],
                ),
            ],
            visibleSummaryLines=["Role: Sentry Roost", "Features: totem marker"],
        )
        pack = DescriptionPack(
            name="Test Pack",
            descriptionPackId="TestPack0",
            openingFragments=[{"text": "The squad arrives in #terrain#."}],
            landmarkFragments=[{"text": "A glance catches #landmark#."}],
            atmosphereFragments=[{"text": "The place shows #feature_list#."}],
            hazardFragments=[{"text": "A hidden hazard waits: #hazard#."}],
            closingFragments=[{"text": "They slow to study it."}],
        )

        rendered = render_local_node_description(setting_context, node_content, pack)
        prompt_packet = build_scene_description_prompt_packet(setting_context, node_content)
        prompt_text = json.dumps(prompt_packet, ensure_ascii=False)

        self.assertNotIn("spike trap", rendered.lower())
        self.assertNotIn("spike_trap", prompt_text)
        self.assertIn("totem marker", prompt_text)
        self.assertEqual(prompt_packet["node"]["canonical_tags"], ["jungle", "lookout", "totem_marker", "clue"])


if __name__ == "__main__":
    unittest.main()
