import tempfile
import unittest
from pathlib import Path

from src.domain.environment import CompatibilitySelectionMode, IncompatibilityMode
from src.services.environment_service import EnvironmentService
from src.services.game_context import GameContext


class TestEnvironmentService(unittest.TestCase):
    def _build_service(self, temp_dir: str):
        environmentbook_path = Path(temp_dir) / "environmentbook.json"
        context = GameContext()
        service = EnvironmentService(str(environmentbook_path), context)
        service.load_environmentbook()
        return context, service, environmentbook_path

    def test_create_and_reload_environment_catalog(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, service, environmentbook_path = self._build_service(temp_dir)

            effect = service.create_effect_from_dict(
                {
                    "name": "Dense Foliage",
                    "description": "Visibility is reduced.",
                    "counterplay": "Use scouts or elevated positions.",
                }
            )
            terrain = service.create_terrain_from_dict(
                {
                    "name": "Jungle Floor",
                    "description": "Dense roots and undergrowth.",
                    "effectIds": [effect.effectId],
                }
            )
            climate = service.create_climate_from_dict(
                {
                    "name": "Tropical Wet",
                    "temperature": "Hot",
                    "humidity": "Humid",
                    "description": "Heavy moisture and oppressive heat.",
                    "effectIds": [effect.effectId],
                }
            )
            biome = service.create_biome_from_dict(
                {
                    "name": "Jungle",
                    "description": "A dense tropical biome.",
                    "effectIds": [effect.effectId],
                    "terrainCompatibilityMode": CompatibilitySelectionMode.SELECTED.name,
                    "compatibleTerrainIds": [terrain.terrainId],
                    "terrainIncompatibilityMode": IncompatibilityMode.ALL_EXCEPT_COMPATIBLE.name,
                    "incompatibleTerrainIds": [],
                    "climateCompatibilityMode": CompatibilitySelectionMode.SELECTED.name,
                    "compatibleClimateIds": [climate.climateId],
                    "climateIncompatibilityMode": IncompatibilityMode.EXPLICIT.name,
                    "incompatibleClimateIds": [],
                }
            )

            reloaded_context = GameContext()
            reloaded_service = EnvironmentService(str(environmentbook_path), reloaded_context)
            reloaded_service.load_environmentbook()

            loaded_effect = reloaded_service.get_effect_by_id(effect.effectId)
            loaded_terrain = reloaded_service.get_terrain_by_id(terrain.terrainId)
            loaded_climate = reloaded_service.get_climate_by_id(climate.climateId)
            loaded_biome = reloaded_service.get_biome_by_id(biome.biomeId)

            self.assertIsNotNone(loaded_effect)
            self.assertEqual(loaded_effect.counterplay, "Use scouts or elevated positions.")
            self.assertEqual(loaded_terrain.effectIds, [effect.effectId])
            self.assertEqual(loaded_climate.temperature, "Hot")
            self.assertEqual(loaded_climate.humidity, "Humid")
            self.assertEqual(loaded_biome.compatibleTerrainIds, [terrain.terrainId])
            self.assertEqual(loaded_biome.terrainCompatibilityMode, CompatibilitySelectionMode.SELECTED)
            self.assertEqual(loaded_biome.terrainIncompatibilityMode, IncompatibilityMode.ALL_EXCEPT_COMPATIBLE)
            self.assertIn(effect.effectId, reloaded_context.effectbook_overview)
            self.assertIn(terrain.terrainId, reloaded_context.terrainbook_overview)
            self.assertIn(climate.climateId, reloaded_context.climatebook_overview)
            self.assertIn(biome.biomeId, reloaded_context.biomebook_overview)

    def test_invalid_references_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, service, _environmentbook_path = self._build_service(temp_dir)
            effect = service.create_effect_from_dict({"name": "Heat Haze"})
            terrain = service.create_terrain_from_dict({"name": "Dunes", "effectIds": [effect.effectId]})

            with self.assertRaises(ValueError):
                service.create_terrain_from_dict({"name": "Broken Terrain", "effectIds": ["MissingEffect999"]})

            with self.assertRaises(ValueError):
                service.create_biome_from_dict(
                    {
                        "name": "Broken Biome",
                        "terrainCompatibilityMode": CompatibilitySelectionMode.SELECTED.name,
                        "compatibleTerrainIds": [terrain.terrainId, "MissingTerrain999"],
                    }
                )

    def test_duplicate_names_receive_unique_ids(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, service, _environmentbook_path = self._build_service(temp_dir)
            first = service.create_effect_from_dict({"name": "Mist"})
            second = service.create_effect_from_dict({"name": "Mist"})
            self.assertNotEqual(first.effectId, second.effectId)


if __name__ == "__main__":
    unittest.main()
