import tempfile
import unittest
from pathlib import Path

from src.domain.Mission import Mission, MissionObjectiveStatus, MissionStatistics
from src.services.allegiance_service import AllegianceService
from src.services.character_service import CharacterService
from src.services.game_context import GameContext
from src.services.item_service import ItemService
from src.services.mission_service import MissionService
from src.services.race_service import RaceService
from src.services.spell_service import SpellService
from src.services.unit_service import UnitService


class TestMissionService(unittest.TestCase):
    def _build_services(self, temp_dir: str):
        base = Path(temp_dir)
        itembook_path = base / "itembook.json"
        spellbook_path = base / "spellbook.json"
        racebook_path = base / "racebook.json"
        unitbook_path = base / "unitbook.json"
        allegiancebook_path = base / "allegiancebook.json"
        missionbook_path = base / "missionbook.json"
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
        allegiance_service = AllegianceService(str(allegiancebook_path), context)
        allegiance_service.load_allegiancebook()
        mission_service = MissionService(str(missionbook_path), context, allegiance_service, unit_service)
        mission_service.load_missionbook()
        return context, item_service, race_service, unit_service, allegiance_service, mission_service, missionbook_path

    def _create_delivery_item(self, item_service: ItemService):
        item_service.create_item_from_dict(
            {
                "name": "Supply Crate",
                "itemClass": "Consumable",
                "tier": 0,
                "consumableKind": "GENERIC",
                "effectPowerType": "CONSUMABLE_POWER",
                "effectPower": 0,
                "damageType": [],
                "spellName": "",
                "statBonuses": [],
            }
        )
        return item_service.get_item("Supply Crate")

    def test_create_edit_reload_missionbook(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            context, item_service, race_service, unit_service, allegiance_service, mission_service, missionbook_path = self._build_services(temp_dir)

            race_service.create_race_from_dict({"name": "Goblin"})
            race_service.create_race_from_dict({"name": "Orc"})
            goblin_race = race_service.get_race("Goblin")
            orc_race = race_service.get_race("Orc")
            goblin_unit = unit_service.create_unit_from_dict({"baseRaceId": goblin_race.raceId, "name": "Goblin Shaman"})
            orc_unit = unit_service.create_unit_from_dict({"baseRaceId": orc_race.raceId, "name": "Orc Brute"})
            delivery_item = self._create_delivery_item(item_service)

            raiders = allegiance_service.create_allegiance_from_dict({"name": "Raiders"})
            cult = allegiance_service.create_allegiance_from_dict({"name": "Cult"})

            mission = mission_service.create_mission_from_dict(
                {
                    "name": "Ruined Crossing",
                    "objective": {
                        "objectiveType": "DELIVERY",
                        "requiredItemId": delivery_item.itemId,
                        "targetAllegianceId": raiders.allegianceId,
                        "requiredPackagesDelivered": 2,
                    },
                    "allegianceConfigs": [
                        {
                            "allegianceId": raiders.allegianceId,
                            "powerPointCap": 25,
                            "unitOptions": [
                                {
                                    "unitId": goblin_unit.unitId,
                                    "capacityMin": 1,
                                    "capacityMax": 2,
                                    "eliteChance": 0.35,
                                    "isBoss": True,
                                }
                            ],
                            "clusterProbability": 0.4,
                            "clusterProbabilityVariance": 0.25,
                            "levelMin": 1,
                            "levelMax": 3,
                        },
                        {
                            "allegianceId": cult.allegianceId,
                            "powerPointCap": 12,
                            "unitOptions": [
                                {
                                    "unitId": orc_unit.unitId,
                                    "capacityMin": None,
                                    "capacityMax": 1,
                                    "eliteChance": 0.0,
                                    "isBoss": False,
                                }
                            ],
                            "clusterProbability": 1.7,
                            "clusterProbabilityVariance": -4.0,
                            "levelMin": 2,
                            "levelMax": 5,
                        },
                    ],
                }
            )

            self.assertEqual(len(mission.allegianceConfigs), 2)
            self.assertEqual(mission.allegianceConfigs[1].clusterProbability, 1.0)
            self.assertEqual(mission.allegianceConfigs[1].clusterProbabilityVariance, 0.0)
            self.assertEqual(mission.allegianceConfigs[0].unitOptions[0].eliteChance, 0.35)
            self.assertTrue(mission.allegianceConfigs[0].unitOptions[0].isBoss)
            self.assertIn(mission.missionId, context.missionbook_overview)
            self.assertIn("Delivery", context.missionbook_overview)

            updated = mission_service.edit_mission_from_patch(
                mission.missionId,
                {
                    "objective": {
                        "objectiveType": "ASSASSINATION",
                        "requiredBossesDefeated": 2,
                    },
                    "allegianceConfigs": [
                        {
                            "allegianceId": raiders.allegianceId,
                            "powerPointCap": 40,
                            "unitOptions": [
                                {
                                    "unitId": goblin_unit.unitId,
                                    "capacityMin": 2,
                                    "capacityMax": 2,
                                    "eliteChance": 0.6,
                                    "isBoss": False,
                                }
                            ],
                            "clusterProbability": 0.75,
                            "clusterProbabilityVariance": 0.1,
                            "levelMin": 3,
                            "levelMax": 6,
                        }
                    ],
                },
            )
            self.assertEqual(updated.allegianceConfigs[0].powerPointCap, 40)
            self.assertEqual(updated.allegianceConfigs[0].unitOptions[0].capacityMin, 2)
            self.assertAlmostEqual(updated.allegianceConfigs[0].unitOptions[0].eliteChance, 0.6)
            self.assertEqual(updated.objective.objectiveType.name, "ASSASSINATION")

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
                unitbook_path=str(Path(temp_dir) / "unitbook.json"),
                context=reloaded_context,
                race_service=reloaded_race_service,
                character_service=reloaded_character_service,
                spell_service=reloaded_spell_service,
                item_service=reloaded_item_service,
            )
            reloaded_unit_service.load_unitbook()
            reloaded_allegiance_service = AllegianceService(str(Path(temp_dir) / "allegiancebook.json"), reloaded_context)
            reloaded_allegiance_service.load_allegiancebook()
            reloaded_mission_service = MissionService(str(missionbook_path), reloaded_context, reloaded_allegiance_service, reloaded_unit_service)
            reloaded_mission_service.load_missionbook()

            loaded = reloaded_mission_service.get_mission_by_id(mission.missionId)
            self.assertIsNotNone(loaded)
            self.assertEqual(len(loaded.allegianceConfigs), 1)
            self.assertEqual(loaded.allegianceConfigs[0].unitOptions[0].unitId, goblin_unit.unitId)
            self.assertEqual(loaded.objective.objectiveType.name, "ASSASSINATION")

    def test_invalid_references_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, item_service, race_service, unit_service, allegiance_service, mission_service, _missionbook_path = self._build_services(temp_dir)

            race_service.create_race_from_dict({"name": "Goblin"})
            goblin_race = race_service.get_race("Goblin")
            unit_service.create_unit_from_dict({"baseRaceId": goblin_race.raceId, "name": "Goblin Sneak"})
            raiders = allegiance_service.create_allegiance_from_dict({"name": "Raiders"})
            delivery_item = self._create_delivery_item(item_service)

            with self.assertRaises(ValueError):
                mission_service.create_mission_from_dict(
                    {
                        "name": "Broken Mission",
                        "objective": {"objectiveType": "ESCORT", "escortUnitId": "MissingUnit999"},
                        "allegianceConfigs": [
                            {
                                "allegianceId": raiders.allegianceId,
                                "unitOptions": [{"unitId": "MissingUnit999"}],
                            }
                        ],
                    }
                )

            with self.assertRaises(ValueError):
                mission_service.create_mission_from_dict(
                    {
                        "name": "Broken Mission Two",
                        "objective": {
                            "objectiveType": "DELIVERY",
                            "requiredItemId": delivery_item.itemId,
                            "targetAllegianceId": "MissingAllegiance999",
                        },
                        "allegianceConfigs": [{"allegianceId": "MissingAllegiance999"}],
                    }
                )

    def test_duplicate_names_get_unique_ids(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _context, _item_service, _race_service, _unit_service, _allegiance_service, mission_service, _missionbook_path = self._build_services(temp_dir)
            a = mission_service.create_mission_from_dict({"name": "Ambush", "objective": {"objectiveType": "SURVIVAL", "requiredHoursSurvived": 1.0}})
            b = mission_service.create_mission_from_dict({"name": "Ambush", "objective": {"objectiveType": "SURVIVAL", "requiredHoursSurvived": 2.0}})
            self.assertNotEqual(a.missionId, b.missionId)

    def test_objective_evaluation_uses_mission_statistics(self):
        mission = Mission.from_dict(
            {
                "name": "Rescue Trial",
                "objective": {
                    "objectiveType": "RESCUE",
                    "requiredAlliesEscaped": 2,
                    "requiredEscapeDistance": 5.0,
                },
                "allegianceConfigs": [],
            }
        )
        failing_stats = MissionStatistics(
            totalStartingAllies=3,
            alliesRemaining=1,
            unitAliveStates={"a": True, "b": False, "c": False},
            unitDistancesMoved={"a": 7.0, "b": 8.0, "c": 0.0},
        )
        winning_stats = MissionStatistics(
            totalStartingAllies=3,
            alliesRemaining=2,
            unitAliveStates={"a": True, "b": True, "c": False},
            unitDistancesMoved={"a": 7.0, "b": 5.5, "c": 0.0},
        )
        self.assertEqual(mission.evaluate_objective(failing_stats), MissionObjectiveStatus.FAILURE)
        self.assertEqual(mission.evaluate_objective(winning_stats), MissionObjectiveStatus.SUCCESS)

    def test_delivery_and_elimination_objectives_use_statistics_helpers(self):
        mission = Mission.from_dict(
            {
                "name": "Supply Push",
                "objective": {
                    "objectiveType": "DELIVERY",
                    "requiredItemId": "SupplyCrate7",
                    "targetAllegianceId": "Allies2",
                    "requiredPackagesDelivered": 3,
                },
                "allegianceConfigs": [],
            }
        )
        stats = MissionStatistics(
            totalStartingEnemies=10,
            enemiesRemaining=4,
            deliveredPackageCounts={"SupplyCrate7|Allies2": 3},
        )
        self.assertEqual(mission.evaluate_objective(stats), MissionObjectiveStatus.SUCCESS)
        self.assertAlmostEqual(stats.get_enemies_remaining_percentage(), 40.0)
        self.assertAlmostEqual(stats.enemiesEliminatedFraction, 0.6)


if __name__ == "__main__":
    unittest.main()
