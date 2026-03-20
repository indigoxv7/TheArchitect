from __future__ import annotations

import unittest
from pathlib import Path

from src.domain.player_functions import LEGACY_MODULE_MAP
from src.tools.admin import start_admin_gui_thread


REPO_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_IMPORT_SNIPPETS = [
    "from src.domain.character import",
    "from src.domain.race import",
    "from src.domain.spells import",
    "from src.domain.allegiance import",
    "from src.domain.environment import",
    "from src.domain.campaign import",
    "from src.domain.unit import",
    "from src.services.main_character_generator import",
    "from src.ui.menu_functions import",
    "from src.config.Globals import",
    "from src.tools.admin_gui import",
]


class TestNavigationHygiene(unittest.TestCase):
    def test_repo_uses_only_canonical_import_paths(self):
        checked_files = (
            list((REPO_ROOT / "src").rglob("*.py"))
            + list((REPO_ROOT / "tests").rglob("*.py"))
            + [REPO_ROOT / "main.py"]
        )
        violations: list[str] = []

        for path in checked_files:
            if path == Path(__file__).resolve():
                continue
            content = path.read_text(encoding="utf-8")
            for snippet in FORBIDDEN_IMPORT_SNIPPETS:
                if snippet in content:
                    violations.append(f"{path.relative_to(REPO_ROOT)} -> {snippet}")

        self.assertEqual(violations, [])

    def test_legacy_module_map_points_old_names_to_canonical_modules(self):
        self.assertEqual(LEGACY_MODULE_MAP["Character"], "src.domain.Character")
        self.assertEqual(LEGACY_MODULE_MAP["Campaign"], "src.domain.Campaign")
        self.assertEqual(LEGACY_MODULE_MAP["Items"], "src.domain.items")
        self.assertEqual(LEGACY_MODULE_MAP["Spells"], "src.domain.Spells")
        self.assertEqual(LEGACY_MODULE_MAP["MainCharacter"], "src.domain.main_character")
        self.assertEqual(LEGACY_MODULE_MAP["Mission"], "src.domain.mission")
        self.assertEqual(LEGACY_MODULE_MAP["menu_functions"], "src.ui.menu")
        self.assertEqual(LEGACY_MODULE_MAP["main_character_generator"], "src.services.character_generation")

    def test_admin_gui_entrypoint_is_exported_from_admin_package(self):
        self.assertTrue(callable(start_admin_gui_thread))


if __name__ == "__main__":
    unittest.main()
