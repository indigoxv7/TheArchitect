import tempfile
import unittest
from pathlib import Path

from src.domain.character_io import character_to_state
from src.services.character_service import CharacterService
from src.services.combat_simulator_service import CombatSimulatorService
from src.services.game_context import GameContext
from src.services.item_service import ItemService
from src.services.race_service import RaceService
from src.services.spell_service import SpellService


class TestCombatSimulatorService(unittest.TestCase):
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
            item_service=item_service,
        )
        race_service.load_racebook()

        simulator = CombatSimulatorService(
            character_service=character_service,
            item_service=item_service,
            spell_service=spell_service,
            race_service=race_service,
            seed=17,
        )
        return item_service, spell_service, character_service, race_service, simulator

    def test_duplicate_names_are_suffixed_and_debug_logs_include_rolls(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            item_service, spell_service, character_service, race_service, simulator = self._build_services(temp_dir)
            item_service.create_item_from_dict(
                {
                    "name": "Goblin Claws",
                    "itemClass": "Weapon",
                    "slot": "PRIMARY_WEAPON",
                    "itemType": "MELEE_WEAPON",
                    "damageType": ["SLASHING"],
                    "damageMin": 6,
                    "damageMax": 8,
                    "penetrationBase": 1,
                }
            )
            claws = item_service.get_weapon("Goblin Claws")
            self.assertIsNotNone(claws)

            race_service.create_race_from_dict(
                {
                    "name": "Goblin",
                    "beifDescription": "A small green humanoid.",
                    "naturalWeaponItemIds": [claws.itemId],
                }
            )
            goblin_race = race_service.get_race("Goblin")
            self.assertIsNotNone(goblin_race)

            left_id, left_character = character_service.create_character_from_dict(
                {
                    "name": "Goblin",
                    "race": goblin_race.raceId,
                    "attributes": {
                        "physicalPower": 7,
                        "physicalStamina": 6,
                        "physicalResistance": 9,
                        "magicPower": 4,
                        "magicStamina": 4,
                        "magicResistance": 4,
                    },
                }
            )
            right_id, right_character = character_service.create_character_from_dict(
                {
                    "name": "Goblin",
                    "race": goblin_race.raceId,
                    "attributes": {
                        "physicalPower": 6,
                        "physicalStamina": 6,
                        "physicalResistance": 6,
                        "magicPower": 4,
                        "magicStamina": 4,
                        "magicResistance": 4,
                    },
                }
            )
            self.assertNotEqual(left_id, right_id)

            session = simulator.start_session(
                character_to_state(left_character), character_to_state(right_character), debug=True, seed=99
            )
            self.assertEqual(session.left_character.name, "Goblin1")
            self.assertEqual(session.right_character.name, "Goblin2")

            active_weapon = simulator._active_weapon(session.left_character)
            self.assertIsNotNone(active_weapon)
            self.assertEqual(active_weapon.name, "Goblin Claws")
            self.assertGreaterEqual(active_weapon.penetrationBase, 9.0)

            lines = simulator.step_session(session)
            self.assertTrue(any("Debug:" in line for line in lines))
            debug_lines = [line for line in lines if "Debug:" in line]
            self.assertTrue(any("base hp roll=" in line for line in debug_lines))
            self.assertTrue(any("scaled hp=" in line for line in debug_lines))
            self.assertTrue(any("hp after armor=" in line for line in debug_lines))
            self.assertTrue(any("resist eff=" in line for line in debug_lines))

    def test_auto_simulate_returns_win_rates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            item_service, _spell_service, character_service, _race_service, simulator = self._build_services(temp_dir)
            item_service.create_item_from_dict(
                {
                    "name": "Short Sword",
                    "itemClass": "Weapon",
                    "slot": "PRIMARY_WEAPON",
                    "itemType": "MELEE_WEAPON",
                    "damageType": ["SLASHING"],
                    "damageMin": 7,
                    "damageMax": 9,
                    "penetrationBase": 3,
                }
            )
            sword = item_service.get_weapon("Short Sword")
            self.assertIsNotNone(sword)

            left_id, left_character = character_service.create_character_from_dict(
                {
                    "name": "Duelist",
                    "gear": {"primary_weapon_item_id": sword.itemId, "inventory_item_ids": []},
                }
            )
            right_id, right_character = character_service.create_character_from_dict(
                {
                    "name": "Raider",
                    "gear": {"primary_weapon_item_id": sword.itemId, "inventory_item_ids": []},
                }
            )
            self.assertNotEqual(left_id, right_id)

            result = simulator.run_auto(
                character_to_state(left_character), character_to_state(right_character), repeats=20
            )
            self.assertEqual(result.sampleCount, 20)
            self.assertGreaterEqual(result.leftWinRate, 0.0)
            self.assertGreaterEqual(result.rightWinRate, 0.0)
            self.assertLessEqual(result.leftWinRate + result.rightWinRate, 1.0)
            self.assertGreater(result.averageRounds, 0.0)

    def test_higher_speed_character_acts_more_often(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _item_service, _spell_service, character_service, _race_service, simulator = self._build_services(temp_dir)

            _fast_id, fast = character_service.create_character_from_dict(
                {
                    "name": "Swift",
                    "attributes": {
                        "physicalPower": 12,
                        "physicalStamina": 5,
                        "physicalResistance": 20,
                        "magicPower": 9,
                        "magicStamina": 5,
                        "magicResistance": 5,
                    },
                }
            )
            _slow_id, slow = character_service.create_character_from_dict(
                {
                    "name": "Steady",
                    "attributes": {
                        "physicalPower": 5,
                        "physicalStamina": 5,
                        "physicalResistance": 20,
                        "magicPower": 5,
                        "magicStamina": 5,
                        "magicResistance": 5,
                    },
                }
            )

            session = simulator.start_session(character_to_state(fast), character_to_state(slow), debug=False, seed=123)
            action_counts = {"Swift": 0, "Steady": 0}

            for _ in range(8):
                lines = simulator.step_session(session)
                for line in lines:
                    if line.startswith("Swift "):
                        action_counts["Swift"] += 1
                    elif line.startswith("Steady "):
                        action_counts["Steady"] += 1
                if session.finished:
                    break

            self.assertGreater(action_counts["Swift"], action_counts["Steady"])


if __name__ == "__main__":
    unittest.main()
