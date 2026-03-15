import tempfile
import unittest
from pathlib import Path

from src.services.character_service import CharacterService
from src.services.game_context import GameContext
from src.services.item_service import ItemService
from src.services.race_service import RaceService
from src.services.spell_service import SpellService
from src.services.unit_service import UnitService


class TestUnitService(unittest.TestCase):
    def _build_services(self, temp_dir: str):
        base = Path(temp_dir)
        itembook_path = base / "itembook.json"
        spellbook_path = base / "spellbook.json"
        racebook_path = base / "racebook.json"
        unitbook_path = base / "unitbook.json"
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
            item_service=item_service,
        )
        race_service.load_racebook()
        unit_service = UnitService(
            unitbook_path=str(unitbook_path),
            context=context,
            race_service=race_service,
            character_service=character_service,
            spell_service=spell_service,
            item_service=item_service,
        )
        unit_service.load_unitbook()
        return context, item_service, spell_service, character_service, race_service, unit_service, unitbook_path

    def test_unit_overrides_fall_back_to_race(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, item_service, spell_service, character_service, race_service, unit_service, unitbook_path = self._build_services(temp_dir)

            item_service.create_item_from_dict({"name": "Club", "slot": "PRIMARY_WEAPON", "itemType": "MELEE_WEAPON"})
            club = item_service.get_item("Club")
            spell_service.create_spell_from_dict(
                {
                    "name": "Hex",
                    "level": 1,
                    "power": 2,
                    "affinity": "Mana",
                    "casting_time": 1,
                    "range": 30,
                    "components": {"verbal": True, "somatic": False, "material": False},
                    "duration": 0,
                    "description": "A nasty curse.",
                }
            )
            avg_id, _ = character_service.create_character_from_dict({"name": "Average Goblin", "level": 2})

            race_service.create_race_from_dict(
                {
                    "name": "Goblin",
                    "detailedDescription": "Base goblin description.",
                    "beifDescription": "A goblin.",
                    "juvenileNomenclature": "pup",
                    "size": "SMALL",
                    "averageSpecimineCharacterId": avg_id,
                    "spellList": [["Hex"]],
                    "gearOptions": {"primaryWeaponOptions": [club.itemId]},
                }
            )
            goblin = race_service.get_race("Goblin")

            unit_service.create_unit_from_dict(
                {
                    "baseRaceId": goblin.raceId,
                    "name": "Goblin Shaman",
                    "spellList": [["Hex"], ["Hex"]],
                }
            )

            unit = unit_service.list_units()[0]
            self.assertEqual(unit.baseRaceId, goblin.raceId)
            self.assertEqual(unit.name, "Goblin Shaman")
            self.assertIsNone(unit.size)
            effective = unit_service.resolve_effective_race(unit)
            self.assertIsNotNone(effective)
            self.assertEqual(effective.name, "Goblin Shaman")
            self.assertEqual(effective.size.name, "SMALL")
            self.assertEqual(getattr(effective.averageSpecimine, "name", ""), "Average Goblin")
            self.assertEqual(getattr(effective.spellList[1][0], "name", ""), "Hex")
            self.assertEqual(getattr(effective.gearOptions.primaryWeaponOptions[0], "itemId", ""), club.itemId)

            reloaded_context = GameContext()
            reloaded_item_service = ItemService(str(Path(temp_dir) / "itembook.json"), reloaded_context)
            reloaded_item_service.load_itembook()
            reloaded_spell_service = SpellService(str(Path(temp_dir) / "spellbook.json"), reloaded_context)
            reloaded_spell_service.load_spellbook()
            reloaded_character_service = CharacterService(str(Path(temp_dir) / "Characters"), context=reloaded_context, item_service=reloaded_item_service)
            reloaded_character_service.load_characters()
            reloaded_race_service = RaceService(
                racebook_path=str(Path(temp_dir) / "racebook.json"),
                context=reloaded_context,
                character_service=reloaded_character_service,
                spell_service=reloaded_spell_service,
                item_service=reloaded_item_service,
            )
            reloaded_race_service.load_racebook()
            reloaded_unit_service = UnitService(
                unitbook_path=str(unitbook_path),
                context=reloaded_context,
                race_service=reloaded_race_service,
                character_service=reloaded_character_service,
                spell_service=reloaded_spell_service,
                item_service=reloaded_item_service,
            )
            reloaded_unit_service.load_unitbook()

            loaded_unit = reloaded_unit_service.get_unit_by_id(unit.unitId)
            self.assertIsNotNone(loaded_unit)
            loaded_effective = reloaded_unit_service.resolve_effective_race(loaded_unit)
            self.assertEqual(loaded_effective.name, "Goblin Shaman")
            self.assertEqual(loaded_effective.size.name, "SMALL")
            self.assertEqual(getattr(loaded_effective.gearOptions.primaryWeaponOptions[0], "itemId", ""), club.itemId)

    def test_units_are_sorted_by_race(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, _item_service, _spell_service, _character_service, race_service, unit_service, _unitbook_path = self._build_services(temp_dir)
            race_service.create_race_from_dict({"name": "Goblin"})
            race_service.create_race_from_dict({"name": "Orc"})
            goblin = race_service.get_race("Goblin")
            orc = race_service.get_race("Orc")
            unit_service.create_unit_from_dict({"baseRaceId": orc.raceId, "name": "Orc Brute"})
            unit_service.create_unit_from_dict({"baseRaceId": goblin.raceId, "name": "Goblin Sneak"})
            labels = [unit_service.get_unit_label(unit) for unit in unit_service.list_units()]
            self.assertTrue(labels[0].startswith("Goblin Sneak"))
            self.assertTrue(labels[1].startswith("Orc Brute"))


if __name__ == "__main__":
    unittest.main()
