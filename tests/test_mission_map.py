import tempfile
import tkinter as tk
import unittest
from pathlib import Path

from src.services.mission_map import (
    MissionMapSettings,
    generate_mission_map,
    render_mission_map_image,
    save_mission_map_image,
)
from src.tools.admin.features.map_testing import MapTestingFrame


class _AppStub:
    def show_home(self):
        return None


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

        image = render_mission_map_image(mission_map, width=320, height=180)
        self.assertEqual(image.size, (320, 180))

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = save_mission_map_image(mission_map, Path(temp_dir) / "map_preview.png", width=320, height=180)
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
