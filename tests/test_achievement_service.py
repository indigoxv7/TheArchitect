import tempfile
import unittest
from pathlib import Path

from src.services.achievement_service import AchievementService
from src.services.game_context import GameContext


class TestAchievementService(unittest.TestCase):
    def test_create_edit_and_reload_achievementbook(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            achievementbook_path = Path(temp_dir) / "achievementbook.json"
            context = GameContext()
            service = AchievementService(str(achievementbook_path), context)

            service.load_achievementbook()
            self.assertEqual(len(service.list_achievements()), 0)

            service.create_achievement_from_dict(
                {
                    "name": "Pathfinder",
                    "title": "Trailblazer",
                    "description": "Complete your first mission.",
                    "bonuses": [
                        {
                            "bonusType": "FLAT",
                            "attributeBonus": {"attribute": "PHYSICAL_POWER", "bonus": 1},
                            "affinities": None,
                            "nanoMultiplier": 0.0,
                            "reason": "Pathfinder bonus",
                            "permanent": True,
                        },
                        {
                            "bonusType": "PERCENTAGE",
                            "attributeBonus": {"attribute": "MAGIC_STAMINA", "bonus": 1},
                            "affinities": None,
                            "nanoMultiplier": 0.2,
                            "reason": "Momentum",
                            "permanent": False,
                        },
                    ],
                }
            )

            created = service.get_achievement("Pathfinder")
            self.assertIsNotNone(created)
            self.assertEqual(created.description, "Complete your first mission.")
            self.assertEqual(len(created.bonuses), 2)

            service.edit_achievement_from_patch(
                "Pathfinder",
                {
                    "name": "Pathfinder",
                    "title": "Trailmaster",
                    "description": "Complete three missions.",
                },
            )

            edited = service.get_achievement("Pathfinder")
            self.assertIsNotNone(edited)
            self.assertEqual(edited.title, "Trailmaster")
            self.assertEqual(edited.description, "Complete three missions.")

            context2 = GameContext()
            service2 = AchievementService(str(achievementbook_path), context2)
            service2.load_achievementbook()
            reloaded = service2.get_achievement("Pathfinder")
            self.assertIsNotNone(reloaded)
            self.assertEqual(reloaded.title, "Trailmaster")
            self.assertEqual(reloaded.description, "Complete three missions.")
            self.assertEqual(len(reloaded.bonuses), 2)


if __name__ == "__main__":
    unittest.main()
