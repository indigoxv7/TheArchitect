import unittest

import main as game
from src.services.mission_map import build_map_settings_from_range, generate_mission_map, generate_node_content_preview


class TestGoblinJungleContent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        game.initialize_game()

    def test_goblin_jungle_catalog_entries_exist(self):
        self.assertIsNotNone(game.environment_service.get_biome_by_id('GoblinJungle0'))
        self.assertIsNotNone(game.environment_service.get_terrain_by_id('GoblinRopeWalks0'))
        self.assertIsNotNone(game.environment_service.get_terrain_by_id('GoblinSnareground0'))
        self.assertIsNotNone(game.environment_service.get_climate_by_id('CanopySmoke0'))
        self.assertIsNotNone(game.environment_service.get_node_role_by_id('GoblinSentryRoost0'))
        self.assertIsNotNone(game.environment_service.get_feature_template_by_id('RopeLookoutPlatforms0'))
        self.assertIsNotNone(game.environment_service.get_hook_template_by_id('GoblinDrumSignal0'))
        self.assertIsNotNone(game.environment_service.get_description_pack_by_id('GoblinJungleArrival0'))
        self.assertIsNotNone(game.environment_service.get_generation_profile_by_id('GoblinJungleProfile0'))

    def test_goblin_missions_use_goblin_jungle_content(self):
        for mission_id in ('GoblinEliminationlvl00', 'GoblinAssassinAssassin1'):
            mission = game.mission_service.get_mission_by_id(mission_id)
            self.assertIsNotNone(mission)
            self.assertEqual(mission.biomeId, 'GoblinJungle0')
            self.assertEqual(mission.nodeGenerationProfileId, 'GoblinJungleProfile0')
            self.assertEqual(mission.descriptionPackId, 'GoblinJungleArrival0')

    def test_goblin_mission_generates_goblin_context_nodes(self):
        mission = game.mission_service.get_mission_by_id('GoblinEliminationlvl00')
        self.assertIsNotNone(mission)

        mission_map = generate_mission_map(build_map_settings_from_range(mission.mapGenerationRange, seed=91))
        setting_context, node_contents = generate_node_content_preview(game.environment_service, mission_map, mission, seed=91)

        self.assertEqual(setting_context.biomeId, 'GoblinJungle0')
        self.assertIn('goblin_territory', setting_context.allTags)
        self.assertEqual(len(node_contents), mission_map.node_count)
        self.assertTrue(any('goblin_territory' in node.canonicalTags for node in node_contents.values()))
        self.assertTrue(any(node.localDescription for node in node_contents.values()))


if __name__ == '__main__':
    unittest.main()
