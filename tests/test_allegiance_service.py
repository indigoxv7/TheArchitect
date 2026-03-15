import tempfile
import unittest
from pathlib import Path

from src.domain.Allegiance import AllegianceDefaultPolicy, AllegianceRelationship
from src.services.allegiance_service import AllegianceService
from src.services.game_context import GameContext


class TestAllegianceService(unittest.TestCase):
    def _build_service(self, temp_dir: str):
        base = Path(temp_dir)
        allegiancebook_path = base / "allegiancebook.json"
        context = GameContext()
        service = AllegianceService(str(allegiancebook_path), context)
        service.load_allegiancebook()
        return context, service, allegiancebook_path

    def test_create_edit_reload_allegiancebook(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            context, service, allegiancebook_path = self._build_service(temp_dir)

            first = service.create_allegiance_from_dict(
                {
                    "name": "Kingdom",
                    "defaultPolicy": AllegianceDefaultPolicy.NEUTRAL_BY_DEFAULT.name,
                }
            )
            second = service.create_allegiance_from_dict(
                {
                    "name": "Raiders",
                    "defaultPolicy": AllegianceDefaultPolicy.HOSTILE_BY_DEFAULT.name,
                }
            )

            service.edit_allegiance_from_patch(
                first.allegianceId,
                {
                    "relationships": {
                        second.allegianceId: AllegianceRelationship.HATED_ENEMIES.name,
                    }
                },
            )

            kingdom = service.get_allegiance_by_id(first.allegianceId)
            self.assertIsNotNone(kingdom)
            self.assertEqual(kingdom.defaultPolicy, AllegianceDefaultPolicy.NEUTRAL_BY_DEFAULT)
            self.assertEqual(kingdom.get_relationship_to(second.allegianceId), AllegianceRelationship.HATED_ENEMIES)
            self.assertEqual(service.get_relationship(second.allegianceId, first.allegianceId), AllegianceRelationship.ENEMIES)
            self.assertIn(first.allegianceId, context.allegiancebook_overview)

            reloaded_context = GameContext()
            reloaded_service = AllegianceService(str(allegiancebook_path), reloaded_context)
            reloaded_service.load_allegiancebook()
            loaded = reloaded_service.get_allegiance_by_id(first.allegianceId)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.get_relationship_to(second.allegianceId), AllegianceRelationship.HATED_ENEMIES)
            self.assertEqual(loaded.get_relationship_to(loaded.allegianceId), AllegianceRelationship.FULL_ALLIES)

    def test_duplicate_names_get_unique_ids(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, service, _path = self._build_service(temp_dir)
            a = service.create_allegiance_from_dict({"name": "Merchants"})
            b = service.create_allegiance_from_dict({"name": "Merchants"})
            self.assertNotEqual(a.allegianceId, b.allegianceId)


if __name__ == "__main__":
    unittest.main()
