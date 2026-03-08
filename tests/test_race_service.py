import tempfile
import unittest
from pathlib import Path

from src.services.character_service import CharacterService
from src.services.game_context import GameContext
from src.services.item_service import ItemService
from src.services.race_service import RaceService
from src.services.spell_service import SpellService


class TestRaceService(unittest.TestCase):
    def _build_services(self, temp_dir: str):
        base = Path(temp_dir)
        itembook_path = base / "itembook.json"
        spellbook_path = base / "spellbook.json"
        racebook_path = base / "racebook.json"
        characters_dir = base / "Characters"

        context = GameContext()

        item_service = ItemService(str(itembook_path), context)
        item_service.load_itembook()

        spell_service = SpellService(str(spellbook_path), context)
        spell_service.load_spellbook()

        character_service = CharacterService(str(characters_dir), context=context, item_service=item_service)
        character_service.load_characters()

        race_service = RaceService(
            racebook_path=str(racebook_path),
            context=context,
            character_service=character_service,
            spell_service=spell_service,
        )
        race_service.load_racebook()

        return context, item_service, spell_service, character_service, race_service, racebook_path, characters_dir, spellbook_path

    def test_create_edit_and_reload_racebook(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            (
                context,
                _item_service,
                spell_service,
                character_service,
                race_service,
                racebook_path,
                characters_dir,
                spellbook_path,
            ) = self._build_services(temp_dir)

            spell_service.create_spell_from_dict(
                {
                    "name": "Spark",
                    "level": 0,
                    "power": 2,
                    "affinity": "Mana",
                    "casting_time": 1,
                    "range": 30,
                    "components": {"verbal": True, "somatic": False, "material": False},
                    "duration": 0,
                    "description": "A tiny spark.",
                }
            )
            spell_service.create_spell_from_dict(
                {
                    "name": "Stone Skin",
                    "level": 2,
                    "power": 0,
                    "affinity": "Chi",
                    "casting_time": 1,
                    "range": 0,
                    "components": {"verbal": False, "somatic": True, "material": False},
                    "duration": 60,
                    "description": "Hardened skin.",
                }
            )

            avg_id, _avg_character = character_service.create_character_from_dict({"name": "Average Goblin", "level": 2})
            enemy_id, _enemy_character = character_service.create_character_from_dict({"name": "Knight Captain", "level": 5})

            race_service.create_race_from_dict(
                {
                    "name": "Goblin",
                    "detailedDescription": "Lean cave dweller with sharp ears.",
                    "beifDescription": "A small green humanoid with an ill-favored countenance.",
                    "juvenileNomenclature": "pup",
                    "size": "SMALL",
                    "averageSpecimineCharacterId": avg_id,
                    "maxAverageAttributes": {
                        "physicalPower": 7,
                        "physicalStamina": 7,
                        "physicalResistance": 6,
                        "magicPower": 5,
                        "magicStamina": 6,
                        "magicResistance": 5,
                    },
                    "minAverageAttributes": {
                        "physicalPower": 3,
                        "physicalStamina": 3,
                        "physicalResistance": 2,
                        "magicPower": 1,
                        "magicStamina": 2,
                        "magicResistance": 1,
                    },
                    "spellList": [["Spark"], [], ["Stone Skin"]],
                    "famedEnemyCharacterIds": [enemy_id],
                }
            )

            races = race_service.list_races()
            self.assertEqual(len(races), 1)
            race = races[0]
            self.assertEqual(race.name, "Goblin")
            self.assertTrue(race.raceId.startswith("Goblin"))
            self.assertEqual(getattr(race.averageSpecimine, "name", ""), "Average Goblin")
            self.assertEqual(getattr(race.spellList[0][0], "name", ""), "Spark")
            self.assertEqual(getattr(race.spellList[2][0], "name", ""), "Stone Skin")
            self.assertEqual(getattr(race.FamedEnemyList[0], "name", ""), "Knight Captain")

            original_race_id = race.raceId
            race_service.edit_race_from_patch(
                original_race_id,
                {
                    "name": "Goblin Renamed",
                    "beifDescription": "A quick and wiry raider.",
                    "spellList": [[], ["Spark"]],
                },
            )

            edited = race_service.get_race_by_id(original_race_id)
            self.assertIsNotNone(edited)
            self.assertEqual(edited.raceId, original_race_id)
            self.assertEqual(edited.name, "Goblin Renamed")
            self.assertEqual(edited.beifDescription, "A quick and wiry raider.")
            self.assertEqual(getattr(edited.spellList[1][0], "name", ""), "Spark")

            self.assertIn(original_race_id, context.racebook_overview)

            reloaded_context = GameContext()
            reloaded_item_service = ItemService(str(Path(temp_dir) / "itembook.json"), reloaded_context)
            reloaded_item_service.load_itembook()

            reloaded_spell_service = SpellService(str(spellbook_path), reloaded_context)
            reloaded_spell_service.load_spellbook()

            reloaded_character_service = CharacterService(
                str(characters_dir),
                context=reloaded_context,
                item_service=reloaded_item_service,
            )
            reloaded_character_service.load_characters()

            reloaded_race_service = RaceService(
                racebook_path=str(racebook_path),
                context=reloaded_context,
                character_service=reloaded_character_service,
                spell_service=reloaded_spell_service,
            )
            reloaded_race_service.load_racebook()

            loaded = reloaded_race_service.get_race_by_id(original_race_id)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.name, "Goblin Renamed")
            self.assertEqual(getattr(loaded.averageSpecimine, "name", ""), "Average Goblin")
            self.assertEqual(getattr(loaded.spellList[1][0], "name", ""), "Spark")
            self.assertEqual(getattr(loaded.FamedEnemyList[0], "name", ""), "Knight Captain")

    def test_duplicate_race_names_get_unique_ids(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, _item_service, _spell_service, _character_service, race_service, _path, _characters_dir, _spellbook_path = self._build_services(temp_dir)

            payload = {
                "name": "Human",
                "detailedDescription": "Standard humanoid.",
                "beifDescription": "A regular person.",
            }

            race_service.create_race_from_dict(payload)
            race_service.create_race_from_dict(payload)

            races = race_service.list_races()
            self.assertEqual(len(races), 2)
            self.assertNotEqual(races[0].raceId, races[1].raceId)


if __name__ == "__main__":
    unittest.main()
