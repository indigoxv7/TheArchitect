import tempfile
import tkinter as tk
import unittest
from pathlib import Path

from src.domain.gear_options import GearOptions
from src.services.character_service import CharacterService
from src.services.game_context import GameContext
from src.services.item_service import ItemService
from src.services.race_service import RaceService
from src.services.spell_service import SpellService
from src.services.unit_service import UnitService
from src.tools.admin.features.units.frame import UnitEditorFrame


class _AppStub:
    def __init__(self, item_service, character_service, spell_service, race_service, unit_service):
        self.item_service = item_service
        self.character_service = character_service
        self.spell_service = spell_service
        self.race_service = race_service
        self.unit_service = unit_service

    def show_home(self):
        return None


class TestUnitEditorFrame(unittest.TestCase):
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
        return item_service, spell_service, character_service, race_service, unit_service

    def test_selecting_saved_unit_from_dropdown_loads_override_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            item_service, spell_service, character_service, race_service, unit_service = self._build_services(temp_dir)
            item_service.create_item_from_dict({"name": "Club", "slot": "PRIMARY_WEAPON", "itemType": "MELEE_WEAPON"})
            item_service.create_item_from_dict(
                {
                    "name": "Scrap Vest",
                    "itemClass": "Armor",
                    "slot": "BODY",
                    "itemType": "ARMOR",
                    "maxArmor": 10,
                    "currentArmor": 10,
                    "statBonuses": [],
                }
            )
            club = item_service.get_item("Club")
            armor = item_service.get_item("Scrap Vest")
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
                    "averageSpecimineCharacterId": avg_id,
                }
            )
            goblin = race_service.get_race("Goblin")
            unit = unit_service.create_unit_from_dict(
                {
                    "baseRaceId": goblin.raceId,
                    "name": "Goblin Fighter",
                    "size": "LARGE",
                    "spellList": [["Hex"], ["Hex"]],
                    "gearOptions": {
                        "primaryWeaponOptions": [club.itemId],
                        "bodyOptions": [armor.itemId, GearOptions.NONE_OPTION_ID],
                    },
                }
            )

            root = None
            try:
                root = tk.Tk()
                root.withdraw()
            except tk.TclError as exc:
                self.skipTest(f"Tk is not available in this environment: {exc}")

            try:
                app = _AppStub(item_service, character_service, spell_service, race_service, unit_service)
                frame = UnitEditorFrame(root, app)
                label = unit_service.get_unit_label(unit)
                frame.pick_var.set(label)
                frame._on_pick()

                self.assertEqual(frame.current_unit_id, unit.unitId)
                self.assertEqual(frame.selected_race_id, goblin.raceId)
                self.assertTrue(frame.simple_override_vars["name"].get())
                self.assertEqual(frame.simple_value_vars["name"].get(), "Goblin Fighter")
                self.assertTrue(frame.simple_override_vars["size"].get())
                self.assertEqual(frame.simple_value_vars["size"].get(), "LARGE")
                self.assertTrue(frame.simple_override_vars["spellList"].get())
                self.assertTrue(frame.simple_override_vars["gearOptions"].get())
                self.assertIn(GearOptions.NONE_OPTION_ID, frame.gear_options_override["bodyOptions"])
                self.assertIn(club.itemId, frame.gear_options_override["primaryWeaponOptions"])
            finally:
                if root is not None:
                    root.destroy()


if __name__ == "__main__":
    unittest.main()
