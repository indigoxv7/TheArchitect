import random
import tempfile
import unittest
from pathlib import Path

from src.domain.character import Character
from src.domain.character_util import Attributes, BodyPart
from src.domain.main_character import CharacterInfo, HobbyInterestLevel, MainCharacter
from src.domain.race import Race
from src.services.character_service import CharacterService
from src.services.game_context import GameContext
from src.services.item_service import ItemService
from src.services.character_generation import (
    _interest_options_for_profile,
    generate_character_from_race,
    generate_character_name,
    generate_hobbies,
    generate_main_character,
    generate_main_character_from_scratch,
)
from src.services.character_generation.names import load_first_name_options, load_last_name_options


class ScriptedRandom:
    def __init__(self, scripted_choices: list[object]):
        self._scripted_choices = list(scripted_choices)

    def choices(self, population, weights=None, k=1):
        if not self._scripted_choices:
            raise AssertionError("No scripted choice left for choices().")
        value = self._scripted_choices.pop(0)
        return [value]

    def choice(self, population):
        if not population:
            raise AssertionError("choice() called with empty population.")
        return population[0]

    def randint(self, start, end):
        return int(start)


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

    def test_generate_main_character_populates_character_info_and_hobbies(self):
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
        self.assertIn(character.characterInfo.distinguishingMarksLocation, BodyPart.__members__)
        self.assertGreaterEqual(len(character.hobbies), 1)
        self.assertEqual(len({hobby_name for hobby_name, _interest in character.hobbies}), len(character.hobbies))
        for hobby_name, interest_level in character.hobbies:
            self.assertTrue(hobby_name)
            self.assertIsInstance(interest_level, HobbyInterestLevel)

    def test_generate_character_name_uses_sex_specific_first_name_lists(self):
        male_name = generate_character_name("Male", rng=ScriptedRandom(["James", "Smith"]))
        female_name = generate_character_name("Female", rng=ScriptedRandom(["Mary", "Smith"]))

        self.assertEqual(male_name, "James Smith")
        self.assertEqual(female_name, "Mary Smith")

    def test_generate_hobbies_zero_count_uses_default_entry(self):
        hobbies = generate_hobbies(rng=ScriptedRandom([0]))

        self.assertEqual(hobbies, [("No particular hobby", HobbyInterestLevel.INDIFFERENT)])

    def test_generate_hobbies_downgrades_second_burning_passion(self):
        hobbies = generate_hobbies(
            rng=ScriptedRandom(
                [
                    3,
                    "Enthusiast",
                    "Cooking and baking",
                    "Reading",
                    "Traveling",
                    HobbyInterestLevel.BURNING_PASSION,
                    HobbyInterestLevel.BURNING_PASSION,
                    HobbyInterestLevel.INTERESTED,
                ]
            )
        )

        self.assertEqual(
            hobbies,
            [
                ("Cooking and baking", HobbyInterestLevel.BURNING_PASSION),
                ("Reading", HobbyInterestLevel.PASSIONATE),
                ("Traveling", HobbyInterestLevel.INTERESTED),
            ],
        )

    def test_single_hobby_interest_weights_make_indifferent_rare(self):
        base_weights = dict(_interest_options_for_profile("Casual dabbler", 2))
        single_hobby_weights = dict(_interest_options_for_profile("Casual dabbler", 1))

        self.assertEqual(base_weights[HobbyInterestLevel.INDIFFERENT], 40.0)
        self.assertLess(single_hobby_weights[HobbyInterestLevel.INDIFFERENT], 10.0)
        self.assertGreater(single_hobby_weights[HobbyInterestLevel.INTERESTED], base_weights[HobbyInterestLevel.INTERESTED])

    def test_generate_character_from_race_respects_attribute_bounds(self):
        average = Character(
            name="Average Goblin",
            attributes=Attributes(physicalPower=5, physicalStamina=5, physicalResistance=5, magicPower=4, magicStamina=4, magicResistance=4),
            level=2,
            raceTier="Tier I",
            race="Goblin1",
        )
        race = Race(
            name="Goblin",
            raceId="Goblin1",
            averageSpecimine=average,
            minAverageAttributes=Attributes(physicalPower=3, physicalStamina=3, physicalResistance=3, magicPower=2, magicStamina=2, magicResistance=2),
            maxAverageAttributes=Attributes(physicalPower=7, physicalStamina=7, physicalResistance=7, magicPower=6, magicStamina=6, magicResistance=6),
        )

        generated = generate_character_from_race(name="Goblin Scout", race=race, rng=random.Random(9))

        self.assertIsInstance(generated, Character)
        self.assertNotIsInstance(generated, MainCharacter)
        self.assertEqual(generated.name, "Goblin Scout")
        self.assertEqual(generated.race, "Goblin1")
        self.assertEqual(generated.level, 2)

        self.assertGreaterEqual(generated.attributes.physicalPower, 3)
        self.assertLessEqual(generated.attributes.physicalPower, 7)
        self.assertGreaterEqual(generated.attributes.magicResistance, 2)
        self.assertLessEqual(generated.attributes.magicResistance, 6)

    def test_generate_main_character_from_scratch_average_build_is_no_op(self):
        average = Character(
            name="Average Human",
            attributes=Attributes(physicalPower=5, physicalStamina=5, physicalResistance=5, magicPower=5, magicStamina=5, magicResistance=5),
            race="Human1",
        )
        race = Race(
            name="Human",
            raceId="Human1",
            averageSpecimine=average,
            minAverageAttributes=Attributes(physicalPower=5, physicalStamina=5, physicalResistance=5, magicPower=5, magicStamina=5, magicResistance=5),
            maxAverageAttributes=Attributes(physicalPower=10, physicalStamina=10, physicalResistance=10, magicPower=10, magicStamina=10, magicResistance=10),
        )
        info = CharacterInfo(build="average", distinguishingMarks="Freckles")

        generated = generate_main_character_from_scratch(
            name="Average Hero",
            race=race,
            rng=random.Random(21),
            character_info=info,
        )

        self.assertEqual(generated.attributes.physicalPower, 5)
        self.assertEqual(generated.attributes.physicalStamina, 5)
        self.assertEqual(generated.attributes.physicalResistance, 5)
        self.assertEqual(generated.attributes.magicPower, 5)
        self.assertEqual(generated.attributes.magicStamina, 5)
        self.assertEqual(generated.attributes.magicResistance, 5)

    def test_generate_main_character_from_scratch_generates_name_after_sex_roll(self):
        average = Character(
            name="Average Human",
            attributes=Attributes(physicalPower=5, physicalStamina=5, physicalResistance=5, magicPower=5, magicStamina=5, magicResistance=5),
            race="Human1",
        )
        race = Race(
            name="Human",
            raceId="Human1",
            averageSpecimine=average,
            minAverageAttributes=Attributes(physicalPower=5, physicalStamina=5, physicalResistance=5, magicPower=5, magicStamina=5, magicResistance=5),
            maxAverageAttributes=Attributes(physicalPower=10, physicalStamina=10, physicalResistance=10, magicPower=10, magicStamina=10, magicResistance=10),
        )
        info = CharacterInfo(sex="Female", build="average", distinguishingMarks="Birthmark")

        generated = generate_main_character_from_scratch(
            name="",
            race=race,
            rng=random.Random(18),
            character_info=info,
        )

        female_first_names = {name for name, _weight in load_first_name_options("Female")}
        last_names = {name for name, _weight in load_last_name_options()}

        self.assertTrue(generated.name)
        self.assertNotEqual(generated.name, "Generated Main Character")
        self.assertIn(generated.name.split()[0], female_first_names)
        self.assertIn(generated.name.split()[-1], last_names)
        self.assertEqual(generated.characterInfo.sex, "Female")

    def test_generate_main_character_from_scratch_replaces_placeholder_name(self):
        average = Character(
            name="Average Human",
            attributes=Attributes(physicalPower=5, physicalStamina=5, physicalResistance=5, magicPower=5, magicStamina=5, magicResistance=5),
            race="Human1",
        )
        race = Race(
            name="Human",
            raceId="Human1",
            averageSpecimine=average,
            minAverageAttributes=Attributes(physicalPower=5, physicalStamina=5, physicalResistance=5, magicPower=5, magicStamina=5, magicResistance=5),
            maxAverageAttributes=Attributes(physicalPower=10, physicalStamina=10, physicalResistance=10, magicPower=10, magicStamina=10, magicResistance=10),
        )
        info = CharacterInfo(sex="Male", build="average", distinguishingMarks="Scar")

        generated = generate_main_character_from_scratch(
            name="Human Main Character",
            race=race,
            rng=random.Random(7),
            character_info=info,
        )

        male_first_names = {name for name, _weight in load_first_name_options("Male")}

        self.assertNotEqual(generated.name, "Human Main Character")
        self.assertIn(generated.name.split()[0], male_first_names)

    def test_generate_main_character_from_scratch_applies_build_modifier(self):
        average = Character(
            name="Average Human",
            attributes=Attributes(physicalPower=5, physicalStamina=5, physicalResistance=5, magicPower=5, magicStamina=5, magicResistance=5),
            race="Human1",
        )
        race = Race(
            name="Human",
            raceId="Human1",
            averageSpecimine=average,
            minAverageAttributes=Attributes(physicalPower=5, physicalStamina=5, physicalResistance=5, magicPower=5, magicStamina=5, magicResistance=5),
            maxAverageAttributes=Attributes(physicalPower=10, physicalStamina=10, physicalResistance=10, magicPower=10, magicStamina=10, magicResistance=10),
        )
        info = CharacterInfo(build="Fit", distinguishingMarks="Scar")

        generated = generate_main_character_from_scratch(
            name="Generated Hero",
            race=race,
            rng=random.Random(12),
            character_info=info,
        )

        self.assertIsInstance(generated, MainCharacter)
        self.assertEqual(generated.race, "Human1")
        self.assertEqual(generated.attributes.physicalPower, 7)
        self.assertEqual(generated.attributes.physicalStamina, 7)
        self.assertEqual(generated.attributes.physicalResistance, 7)
        self.assertEqual(generated.attributes.magicPower, 5)
        self.assertEqual(generated.attributes.magicStamina, 5)
        self.assertEqual(generated.attributes.magicResistance, 5)
        self.assertEqual(generated.characterInfo.build, "Fit")
        self.assertIn(generated.characterInfo.distinguishingMarksLocation, BodyPart.__members__)

    def test_main_character_from_character_preserves_base_fields(self):
        base_character = Character(name="Avery", level=3, raceTier="Tier II", race="Elf2")
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
        self.assertEqual(main_character.health, 73)
        self.assertEqual(main_character.description, "Field commander")
        self.assertTrue(main_character.characterInfo.occupation)
        self.assertGreaterEqual(len(main_character.hobbies), 1)

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
                    "distinguishingMarksLocation": "FACE",
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
                "hobbies": [
                    {"name": "Reading", "interestLevel": "BurningPassion"},
                    {"name": "Cooking and baking", "interestLevel": "Interested"},
                ],
            }

            character_id, created = character_service.create_character_from_dict(payload)
            self.assertIsInstance(created, MainCharacter)
            self.assertEqual(created.characterInfo.job, "Software Developer")
            self.assertEqual(created.characterInfo.distinguishingMarksLocation, "FACE")
            self.assertEqual(created.hobbies[0], ("Reading", HobbyInterestLevel.BURNING_PASSION))

            character_service.load_characters()
            loaded = character_service.get_character(character_id)
            self.assertIsInstance(loaded, MainCharacter)
            self.assertEqual(loaded.name, "Lyra")
            self.assertEqual(loaded.level, 5)
            self.assertEqual(loaded.characterInfo.occupation, "information/tech worker")
            self.assertEqual(loaded.characterInfo.goal, "protect the team")
            self.assertEqual(loaded.characterInfo.distinguishingMarksLocation, "FACE")
            self.assertEqual(
                loaded.hobbies,
                [
                    ("Reading", HobbyInterestLevel.BURNING_PASSION),
                    ("Cooking and baking", HobbyInterestLevel.INTERESTED),
                ],
            )


if __name__ == "__main__":
    unittest.main()



