import tempfile
import unittest
from pathlib import Path

from src.services.game_context import GameContext
from src.services.spell_service import SpellService


class TestSpellService(unittest.TestCase):
    def test_create_edit_and_reload_spellbook(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            spellbook_path = Path(temp_dir) / "spellbook.json"
            context = GameContext()
            service = SpellService(str(spellbook_path), context)

            service.load_spellbook()
            self.assertEqual(len(service.list_spells()), 0)

            service.create_spell_from_dict(
                {
                    "name": "Fire Bolt",
                    "level": 1,
                    "power": "1d10",
                    "powerLevel": 5.5,
                    "affinity": "fire",
                    "casting_time": "1 action",
                    "range": "120 ft",
                    "components": {"verbal": True, "somatic": True, "material": False},
                    "duration": "Instantaneous",
                    "description": "A bolt of fire streaks toward a creature.",
                }
            )

            self.assertIsNotNone(service.get_spell("Fire Bolt"))

            service.edit_spell_from_patch("Fire Bolt", {"level": 2, "power": "2d10", "powerLevel": 11.0})
            self.assertEqual(service.get_spell("Fire Bolt").level, 2)
            self.assertEqual(service.get_spell("Fire Bolt").power, "2d10")
            self.assertEqual(service.get_spell("Fire Bolt").powerLevel, 11.0)

            reloaded_context = GameContext()
            reloaded_service = SpellService(str(spellbook_path), reloaded_context)
            reloaded_service.load_spellbook()
            loaded = reloaded_service.get_spell("Fire Bolt")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.powerLevel, 11.0)
            self.assertIn("Fire Bolt", reloaded_context.spellbook_overview)


if __name__ == "__main__":
    unittest.main()
