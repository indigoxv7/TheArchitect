import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.domain.Character import Character
from src.domain.CharacterUtil import Attributes
from src.domain.Items import Gear
from src.domain.Race import CreatureSize, Race
from src.domain.combat import BattleOutcome, BattlePhase, EncounterDefinition, EncounterEnemyEntry, EncounterType
from src.domain.player_functions import Player
from src.persistence.active_battle_store import ActiveBattleStore
from src.services.battle_service import BattleService
from src.services.encounter_service import EncounterService
from src.services.game_context import GameContext
from src.services.item_service import ItemService
from src.services.player_service import PlayerService
from src.services.spell_service import SpellService
from src.services.character_service import CharacterService


class _FakeMemoryService:
    def __init__(self):
        self.events = []

    def append_manual_event(self, **kwargs):
        self.events.append(kwargs)


class _FakeOpenAIService:
    def __init__(self, scores):
        self._scores = list(scores)

    def is_configured(self):
        return True

    def judge_combat_strategy(self, _prompt_packet):
        score = self._scores.pop(0)
        self._scores.append(score)
        return SimpleNamespace(score=score, reasons=[f"score {score}"], risk_flags=[], confidence=0.75)


class TestBattleService(unittest.TestCase):
    def _build_services(self, temp_dir: str, openai_service=None):
        context = GameContext()
        player_saves = Path(temp_dir) / "PlayerSaves"
        roster_path = Path(temp_dir) / "ExistingPlayersRoster.json"
        itembook_path = Path(temp_dir) / "itembook.json"
        spellbook_path = Path(temp_dir) / "spellbook.json"
        characters_dir = Path(temp_dir) / "Characters"
        portal_dir = Path(temp_dir) / "PortalEncounters"
        active_battles_dir = Path(temp_dir) / "ActiveBattles"

        player_service = PlayerService(
            bot=None,
            guild_id=1,
            context=context,
            player_save_directory=str(player_saves),
            existing_players_roster_path=str(roster_path),
        )
        player_service.initialize_storage()

        item_service = ItemService(str(itembook_path), context)
        item_service.load_itembook(default_items=dict(context.all_items))

        spell_service = SpellService(str(spellbook_path), context)
        spell_service.load_spellbook()

        character_service = CharacterService(str(characters_dir), context=context, item_service=item_service)
        character_service.load_characters()

        sword = item_service.get_item("Sword")
        bandage = item_service.get_item("Bandage")
        self.assertIsNotNone(sword)
        self.assertIsNotNone(bandage)

        ally = Character(
            name="Hero",
            race="Human1",
            level=3,
            attributes=Attributes(physicalPower=7, physicalStamina=7, physicalResistance=6, magicPower=5, magicStamina=5, magicResistance=5),
            gear=Gear(primaryWeapon=sword),
        )
        ally.playerInstanceId = "Hero0"
        ally.health = 80

        enemy_template = Character(
            name="Goblin Raider",
            race="Goblin0",
            level=1,
            attributes=Attributes(physicalPower=5, physicalStamina=5, physicalResistance=4, magicPower=3, magicStamina=3, magicResistance=3),
            gear=Gear(primaryWeapon=sword),
        )
        enemy_template.health = 60
        context.all_characters["GoblinRaider0"] = enemy_template

        context.all_races["Human1"] = Race(name="Human", size=CreatureSize.STANDARD, averageSpecimine=ally, raceId="Human1")
        context.all_races["Goblin0"] = Race(name="Goblin", size=CreatureSize.SMALL, averageSpecimine=enemy_template, raceId="Goblin0")

        player = Player(111, characters=[ally], inventory=[bandage.itemId])
        player.playerName = "Tester"
        save_path = player_saves / "111.json"
        player.AttachSavePath(str(save_path), enableAutoSave=False)
        player.Save()
        context.player_cache[111] = player
        context.existing_players[111] = True

        encounter_service = EncounterService(
            portal_encounter_directory=str(portal_dir),
            context=context,
            race_service=None,
            character_service=character_service,
        )
        active_battle_store = ActiveBattleStore(str(active_battles_dir))
        memory_service = _FakeMemoryService()
        battle_service = BattleService(
            context=context,
            player_service=player_service,
            item_service=item_service,
            spell_service=spell_service,
            character_service=character_service,
            race_service=None,
            encounter_service=encounter_service,
            active_battle_store=active_battle_store,
            openai_service=openai_service,
            memory_service=memory_service,
        )
        battle_service.initialize()
        return context, player_service, item_service, battle_service, memory_service, bandage

    def test_start_battle_saves_and_resumes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, _player_service, _item_service, battle_service, _memory_service, _bandage = self._build_services(temp_dir)

            battle, resumed = battle_service.start_or_resume_battle(111, EncounterType.SCAVENGING)
            self.assertFalse(resumed)
            self.assertEqual(battle.player_id, 111)
            self.assertTrue((Path(temp_dir) / "ActiveBattles" / "111.json").exists())

            resumed_battle, resumed = battle_service.start_or_resume_battle(111, EncounterType.PORTAL)
            self.assertTrue(resumed)
            self.assertEqual(resumed_battle.battle_id, battle.battle_id)

    def test_recentering_shifts_pressed_side_toward_equilibrium(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, player_service, _item_service, battle_service, _memory_service, _bandage = self._build_services(temp_dir)
            player = player_service.get_player_sync(111)
            encounter = EncounterDefinition(
                encounter_id="test_recentering",
                encounter_type=EncounterType.SCAVENGING,
                name="Pressed Line",
                terrain="Roadside",
                width=3,
                total_lines=7,
                objective_text="Hold.",
                allow_retreat=True,
                enemy_entries=[EncounterEnemyEntry(kind="race", identifier="Goblin0", count=2, use_stack=True)],
                player_front_line=1,
                enemy_front_line=2,
            )
            battle = battle_service._build_battle_from_encounter(player, encounter, "test")
            battle.default_player_front_line = 3
            battle.default_enemy_front_line = 4
            battle.player_recenter_pressure = 10.0
            highlights = []

            battle_service._apply_recentering(battle, player_progress=False, enemy_progress=False, highlights=highlights)

            self.assertEqual(battle.player_front_line, 2)
            self.assertEqual(battle.enemy_front_line, 3)
            self.assertTrue(any("re-center" in line for line in highlights))

    def test_player_off_map_in_scavenging_forces_retreat(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, player_service, _item_service, battle_service, _memory_service, _bandage = self._build_services(temp_dir)
            player = player_service.get_player_sync(111)
            encounter = EncounterDefinition(
                encounter_id="test_retreat",
                encounter_type=EncounterType.SCAVENGING,
                name="Off Map",
                terrain="Ruins",
                width=3,
                total_lines=5,
                objective_text="Survive.",
                allow_retreat=True,
                enemy_entries=[],
                player_front_line=0,
                enemy_front_line=1,
            )
            battle = battle_service._build_battle_from_encounter(player, encounter, "test")
            battle.player_front_line = -1
            battle.enemy_front_line = 0
            highlights = []

            ended = battle_service._check_off_map_outcome(battle, highlights)

            self.assertTrue(ended)
            self.assertEqual(battle.phase, BattlePhase.RESOLVED)
            self.assertEqual(battle.outcome, BattleOutcome.RETREAT)

    def test_enemy_off_map_breaks_and_player_wins(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, player_service, _item_service, battle_service, _memory_service, _bandage = self._build_services(temp_dir)
            player = player_service.get_player_sync(111)
            encounter = EncounterDefinition(
                encounter_id="test_victory",
                encounter_type=EncounterType.PORTAL,
                name="Victory",
                terrain="Gate",
                width=3,
                total_lines=5,
                objective_text="Win.",
                allow_retreat=False,
                enemy_entries=[],
                player_front_line=2,
                enemy_front_line=3,
            )
            battle = battle_service._build_battle_from_encounter(player, encounter, "test")
            battle.enemy_front_line = battle.total_lines
            highlights = []

            ended = battle_service._check_off_map_outcome(battle, highlights)

            self.assertTrue(ended)
            self.assertEqual(battle.outcome, BattleOutcome.VICTORY)

    def test_estimate_victory_odds_is_cached_by_orders(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, _player_service, _item_service, battle_service, _memory_service, _bandage = self._build_services(temp_dir)
            battle, _ = battle_service.start_or_resume_battle(111, EncounterType.SCAVENGING)

            first = battle_service.estimate_victory_odds(battle, simulations=4)
            second = battle_service.estimate_victory_odds(battle, simulations=4)

            self.assertGreaterEqual(first, 0.0)
            self.assertLessEqual(first, 1.0)
            self.assertEqual(first, second)
            self.assertEqual(battle.cached_orders_signature, battle.orders.signature())

    def test_use_consumable_consumes_inventory_and_heals(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, player_service, _item_service, battle_service, _memory_service, bandage = self._build_services(temp_dir)
            battle, _ = battle_service.start_or_resume_battle(111, EncounterType.SCAVENGING)
            battle.ally_units[0].health = 40
            player = player_service.get_player_sync(111)
            starting_inventory = len(player.inventory)

            message = battle_service.use_consumable(battle, bandage.itemId)

            self.assertIn("restored", message)
            self.assertEqual(len(player.inventory), starting_inventory - 1)
            self.assertGreater(battle.ally_units[0].health, 40)

    def test_apply_strategy_uses_median_score(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_openai = _FakeOpenAIService([2, 9, 7])
            _context, _player_service, _item_service, battle_service, _memory_service, _bandage = self._build_services(temp_dir, openai_service=fake_openai)
            battle, _ = battle_service.start_or_resume_battle(111, EncounterType.SCAVENGING)

            judgment = battle_service.apply_strategy(battle, "Advance on the weak flank while keeping reserves tight.")

            self.assertEqual(judgment["score"], 7)
            self.assertEqual(battle.orders.strategy_score, 7)
            self.assertAlmostEqual(battle.orders.lane_discipline_modifier, 0.05)
            self.assertEqual(battle.orders.width_control_bonus, 0)


if __name__ == "__main__":
    unittest.main()
