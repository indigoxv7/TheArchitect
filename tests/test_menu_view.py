import unittest
from types import SimpleNamespace

from src.bot.views.menu_view import MenuButton, normalize_button_emoji


class TestMenuView(unittest.TestCase):
    def test_normalize_button_emoji_drops_blank_and_placeholder_values(self):
        self.assertIsNone(normalize_button_emoji(None))
        self.assertIsNone(normalize_button_emoji(""))
        self.assertIsNone(normalize_button_emoji("   "))
        self.assertIsNone(normalize_button_emoji("?"))
        self.assertIsNone(normalize_button_emoji("??"))

    def test_menu_button_omits_invalid_placeholder_emoji(self):
        button = MenuButton(SimpleNamespace(myEmoji="??"), None, "Portal Mission", lambda *args: None)
        self.assertIsNone(button.emoji)

    def test_menu_button_keeps_valid_unicode_emoji(self):
        button = MenuButton(SimpleNamespace(myEmoji="\U0001f300"), None, "Portal Mission", lambda *args: None)
        self.assertIsNotNone(button.emoji)
        self.assertEqual(button.emoji.name, "\U0001f300")


if __name__ == "__main__":
    unittest.main()
