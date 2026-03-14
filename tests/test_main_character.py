import random
import tempfile
import unittest
from pathlib import Path

from src.domain.Character import Character
from src.domain.MainCharacter import MainCharacter
from src.services.character_service import CharacterService
from src.services.game_context import GameContext
from src.services.item_service import ItemService
from src.services.main_character_generator import generate_main_character


class TestMainCharacter(unittest.TestCase):
    def _build_services(self, temp_dir: str):
        itembook_path = Path(temp_dir) / "itembook.json"
        characters_dir = Path(temp_dir) / "Characters"
        context = GameContext()

        item_service = ItemService(str(itembook_path), context)
        item_service.load_itembook()

        character_service = CharacterService(str(characters_dir), context=context, item_service=item_service)
        character_service.load_characters()
        return context, item_service, character_service

    def test_generate_main_character_populates_character_info(self):
        character = generate_main_character(name="Generated Test", rng=random.Random(12345))

        self.assertIsInstance(character, MainCharacter)
        self.assertEqual(character.name, "Generated Test")
        self.assertGreaterEqual(character.characterInfo.age, 18)
        self.assertLessEqual(character.characterInfo.age, 80)
        self.assertIn(character.characterInfo.sex, {"Male", "Female"})
        self.assertTrue(character.characterInfo.height)
        self.assertTrue(character.characterInfo.occupation)
        self.assertTrue(character.characterInfo.job)
        self.assertTrue(character.characterInfo.personalityType)
        self.assertTrue(character.characterInfo.goal)

    def test_main_character_from_character_preserves_base_fields(self):
        base_character = Character(name="Avery", level=3, raceTier="Tier II", party=1, race="Elf2")
        base_character.health = 73
        base_character.description = "Field commander"
        base_character.portraitURL = "https://example.com/portrait.png"
        base_character.footerImageURL = "https://example.com/footer.png"

        main_character = MainCharacter.from_character(base_character, rng=random.Random(77))

        self.assertIsInstance(main_character, MainCharacter)
        self.assertEqual(main_character.name, "Avery")
        self.assertEqual(main_character.level, 3)
        self.assertEqual(main_character.raceTier, "Tier II")
        self.assertEqual(main_character.race, "Elf2")
        self.assertEqual(main_character.party, 1)
        self.assertEqual(main_character.health, 73)
        self.assertEqual(main_character.description, "Field commander")
        self.assertTrue(main_character.characterInfo.occupation)

    def test_character_service_round_trip_main_character(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, _item_service, character_service = self._build_services(temp_dir)

            payload = {
                "name": "Lyra",
                "characterType": "MainCharacter",
                "level": 5,
                "race": "Human1",
                "raceTier": "Tier II",
                "characterInfo": {
                    "age": 29,
                    "birthday": "May 14, 1996",
                    "sex": "Female",
                    "height": "5'7\"",
                    "build": "fit",
                    "skinTone": "medium",
                    "hairColor": "black",
                    "eyeColor": "green",
                    "distinguishingMarks": "scar on left cheek",
                    "background": "urban working-class",
                    "occupation": "information/tech worker",
                    "job": "Software Developer",
                    "personalityType": "INTJ",
                    "coreValue": "loyalty",
                    "strength": "decisive",
                    "flaw": "guarded",
                    "socialStyle": "reserved",
                    "speechStyle": "precise",
                    "goal": "protect the team",
                    "secret": "keeps a hidden contact",
                    "emotionalTrigger": "betrayal",
                    "copingHabit": "overworking",
                },
            }

            character_id, created = character_service.create_character_from_dict(payload)
            self.assertIsInstance(created, MainCharacter)
            self.assertEqual(created.characterInfo.job, "Software Developer")

            character_service.load_characters()
            loaded = character_service.get_character(character_id)
            self.assertIsInstance(loaded, MainCharacter)
            self.assertEqual(loaded.name, "Lyra")
            self.assertEqual(loaded.level, 5)
            self.assertEqual(loaded.characterInfo.occupation, "information/tech worker")
            self.assertEqual(loaded.characterInfo.goal, "protect the team")


if __name__ == "__main__":
    unittest.main()