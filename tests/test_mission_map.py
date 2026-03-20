import tempfile
import tkinter as tk
import unittest
from dataclasses import dataclass
from pathlib import Path

from src.domain.mission import MissionMapGenerationRange, MissionTemplate
from src.services.mission_map import (
    MissionMapOverlay,
    MissionMapSettings,
    generate_all_map_features,
    generate_clue_overlay,
    generate_map_from_range,
    generate_mission_map,
    generate_treasure_overlay,
    place_characters_on_map,
    render_mission_map_image,
    save_mission_map_image,
)
from src.tools.admin.features.map_testing import MapTestingFrame


class _AppStub:
    def show_home(self):
        return None


@dataclass
class _PopulatedAllegianceStub:
    allegianceId: str
    generatedUnits: list[object]


@dataclass
class _PopulationPreviewStub:
    allegiances: list[_PopulatedAllegianceStub]


class TestMissionMap(unittest.TestCase):
    def test_generate_mission_map_uses_requested_node_count_and_materializes_seed(self):
        mission_map = generate_mission_map(
            MissionMapSettings(
                total_nodes=60,
                narrowness=0.5,
                connectedness=0.25,
                dead_end_likelihood=0.7,
            )
        )

        self.assertEqual(mission_map.node_count, 60)
        self.assertIsNotNone(mission_map.settings.seed)
        self.assertGreaterEqual(mission_map.edge_count, mission_map.node_count - 1)

        visited = set()
        stack = [mission_map.start_node_id]
        while stack:
            node_id = stack.pop()
            if node_id in visited:
                continue
            visited.add(node_id)
            stack.extend(mission_map.adjacency_by_node[node_id] - visited)

        self.assertEqual(len(visited), mission_map.node_count)

    def test_generate_map_from_range_samples_deterministically_with_seed(self):
        settings_range = MissionMapGenerationRange(
            totalNodesLow=18,
            totalNodesHigh=24,
            narrownessLow=0.2,
            narrownessHigh=0.4,
            connectednessLow=0.15,
            connectednessHigh=0.35,
            deadEndLikelihoodLow=0.4,
            deadEndLikelihoodHigh=0.8,
        )

        left = generate_map_from_range(settings_range, seed=12345)
        right = generate_map_from_range(settings_range, seed=12345)

        self.assertEqual(left.settings.total_nodes, right.settings.total_nodes)
        self.assertEqual(left.settings.narrowness, right.settings.narrowness)
        self.assertEqual(left.settings.connectedness, right.settings.connectedness)
        self.assertEqual(left.settings.dead_end_likelihood, right.settings.dead_end_likelihood)
        self.assertGreaterEqual(left.settings.total_nodes, 18)
        self.assertLessEqual(left.settings.total_nodes, 24)
        self.assertGreaterEqual(left.settings.narrowness, 0.2)
        self.assertLessEqual(left.settings.narrowness, 0.4)
        self.assertGreaterEqual(left.settings.connectedness, 0.15)
        self.assertLessEqual(left.settings.connectedness, 0.35)
        self.assertGreaterEqual(left.settings.dead_end_likelihood, 0.4)
        self.assertLessEqual(left.settings.dead_end_likelihood, 0.8)

    def test_place_characters_on_map_uses_preview_units_and_preserves_treasure(self):
        mission = MissionTemplate.from_dict(
            {
                "name": "Cluster Trial",
                "objective": {"objectiveType": "SURVIVAL", "requiredHoursSurvived": 1.0},
                "allegianceConfigs": [
                    {
                        "allegianceId": "Raiders1",
                        "clusterProbability": 1.0,
                        "clusterProbabilityVariance": 0.0,
                        "unitOptions": [],
                    }
                ],
            }
        )
        preview = _PopulationPreviewStub(
            allegiances=[_PopulatedAllegianceStub("Raiders1", [object(), object(), object(), object()])]
        )
        mission_map = generate_map_from_range(MissionMapGenerationRange(totalNodesLow=18, totalNodesHigh=18), seed=987)
        existing_overlay = MissionMapOverlay(nanoByNode={mission_map.start_node_id: 90})

        overlay = place_characters_on_map(
            mission_map,
            mission,
            preview,
            existing_overlay=existing_overlay,
            seed=11,
        )

        self.assertEqual(overlay.totalPlacedCharacters, 4)
        self.assertEqual(sum(overlay.characterCountByNode.values()), 4)
        self.assertEqual(len(overlay.characterCountByNode), 1)
        self.assertEqual(overlay.nanoByNode, {mission_map.start_node_id: 90})
        self.assertEqual(overlay.clueTargetNodeByNode, {})

    def test_generate_treasure_overlay_only_replaces_treasure(self):
        mission_map = generate_map_from_range(MissionMapGenerationRange(totalNodesLow=16, totalNodesHigh=16), seed=321)
        overlay = MissionMapOverlay(
            unitsByNode={1: [object(), object()]},
            nanoByNode={2: 10},
            clueTargetNodeByNode={3: 4},
        )

        updated = generate_treasure_overlay(mission_map, existing_overlay=overlay, seed=7)

        self.assertEqual(updated.unitsByNode, overlay.unitsByNode)
        self.assertEqual(updated.clueTargetNodeByNode, overlay.clueTargetNodeByNode)
        self.assertNotEqual(updated.nanoByNode, {2: 10})
        self.assertGreater(len(updated.nanoByNode), 0)
        self.assertGreater(updated.totalNano, 0)

    def test_generate_clue_overlay_requires_characters(self):
        mission_map = generate_map_from_range(MissionMapGenerationRange(totalNodesLow=14, totalNodesHigh=14), seed=456)
        with self.assertRaises(ValueError):
            generate_clue_overlay(mission_map, existing_overlay=MissionMapOverlay(), seed=8)

    def test_generate_all_map_features_stacks_character_treasure_and_clues(self):
        mission = MissionTemplate.from_dict(
            {
                "name": "Full Generation",
                "objective": {"objectiveType": "SURVIVAL", "requiredHoursSurvived": 1.0},
                "allegianceConfigs": [
                    {
                        "allegianceId": "Raiders1",
                        "clusterProbability": 0.5,
                        "clusterProbabilityVariance": 0.0,
                        "unitOptions": [],
                    }
                ],
            }
        )
        preview = _PopulationPreviewStub(
            allegiances=[_PopulatedAllegianceStub("Raiders1", [object(), object(), object()])]
        )
        mission_map = generate_map_from_range(MissionMapGenerationRange(totalNodesLow=20, totalNodesHigh=20), seed=654)

        overlay = generate_all_map_features(mission_map, mission, preview, seed=12)

        self.assertEqual(overlay.totalPlacedCharacters, 3)
        self.assertGreater(len(overlay.nanoByNode), 0)
        self.assertGreater(len(overlay.clueTargetNodeByNode), 0)

    def test_render_and_save_mission_map_image(self):
        mission_map = generate_mission_map(
            MissionMapSettings(
                total_nodes=12,
                narrowness=0.4,
                connectedness=0.3,
                dead_end_likelihood=0.6,
                seed=1234,
            )
        )
        overlay = MissionMapOverlay(
            unitsByNode={mission_map.start_node_id: [object(), object()]},
            nanoByNode={mission_map.start_node_id + 1: 150},
            clueTargetNodeByNode={mission_map.start_node_id + 2: mission_map.start_node_id},
        )

        image = render_mission_map_image(mission_map, width=320, height=180, overlay=overlay)
        self.assertEqual(image.size, (320, 180))

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = save_mission_map_image(
                mission_map,
                Path(temp_dir) / "map_preview.png",
                width=320,
                height=180,
                overlay=overlay,
            )
            self.assertTrue(output_path.exists())
            self.assertGreater(output_path.stat().st_size, 0)

    def test_map_testing_frame_generates_preview(self):
        root = None
        try:
            root = tk.Tk()
            root.withdraw()
        except tk.TclError as exc:
            self.skipTest(f"Tk is not available in this environment: {exc}")

        try:
            frame = MapTestingFrame(root, _AppStub())
            frame._generate_map()

            self.assertIsNotNone(frame.current_map)
            self.assertIsNotNone(frame.preview_photo)
            self.assertTrue(frame.seed_var.get().strip())
            self.assertIn("Nodes:", frame.summary_var.get())
        finally:
            if root is not None:
                root.destroy()


if __name__ == "__main__":
    unittest.main()
