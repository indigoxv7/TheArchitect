import tempfile
import unittest
from pathlib import Path

from src.domain.gear_options import GearOptions
from src.domain.mission import MissionTemplate
from src.services.character_service import CharacterService
from src.services.game_context import GameContext
from src.services.item_service import ItemService
from src.services.mission_unit_populator import MissionUnitPopulator
from src.services.power_rating_service import PowerRatingService
from src.services.race_service import RaceService
from src.services.spell_service import SpellService
from src.services.unit_service import UnitService


class TestMissionUnitPopulator(unittest.TestCase):
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
        power_rating_service = PowerRatingService(
            spell_service=spell_service,
            item_service=item_service,
            race_service=race_service,
            sample_count=25,
            seed=1337,
        )
        return item_service, spell_service, character_service, race_service, unit_service, power_rating_service

    def _seed_unit_data(self, item_service, spell_service, character_service, race_service, unit_service):
        item_service.create_item_from_dict(
            {
                "name": "Rusty Blade",
                "itemClass": "Weapon",
                "slot": "PRIMARY_WEAPON",
                "itemType": "MELEE_WEAPON",
                "damageType": ["SLASHING"],
                "damageMin": 7,
                "damageMax": 9,
                "powerLevel": 8.0,
                "statBonuses": [],
            }
        )
        item_service.create_item_from_dict(
            {
                "name": "War Pike",
                "itemClass": "Weapon",
                "slot": "PRIMARY_WEAPON",
                "itemType": "MELEE_WEAPON",
                "damageType": ["PIERCING"],
                "damageMin": 12,
                "damageMax": 16,
                "powerLevel": 14.0,
                "statBonuses": [],
            }
        )
        item_service.create_item_from_dict(
            {
                "name": "Scrap Vest",
                "itemClass": "Armor",
                "slot": "BODY",
                "itemType": "ARMOR",
                "maxArmor": 8,
                "currentArmor": 8,
                "powerLevel": 4.0,
                "statBonuses": [],
            }
        )
        weak_weapon = item_service.get_item("Rusty Blade")
        strong_weapon = item_service.get_item("War Pike")

        spell_service.create_spell_from_dict(
            {
                "name": "Hex",
                "level": 1,
                "power": 5,
                "powerLevel": 6.0,
                "affinity": "Mana",
                "casting_time": 1,
                "range": 30,
                "components": {"verbal": True, "somatic": True, "material": False},
                "duration": 0,
                "description": "A weak curse.",
            }
        )
        spell_service.create_spell_from_dict(
            {
                "name": "Flare Lance",
                "level": 1,
                "power": 9,
                "powerLevel": 11.0,
                "affinity": "Mana",
                "casting_time": 1,
                "range": 40,
                "components": {"verbal": True, "somatic": True, "material": False},
                "duration": 0,
                "description": "A strong magical strike.",
            }
        )

        average_id, _ = character_service.create_character_from_dict({"name": "Average Goblin", "level": 1})
        race_service.create_race_from_dict(
            {
                "name": "Goblin",
                "averageSpecimineCharacterId": average_id,
                "minAverageAttributes": {
                    "physicalPower": 4,
                    "physicalStamina": 4,
                    "physicalResistance": 4,
                    "magicPower": 4,
                    "magicStamina": 4,
                    "magicResistance": 4,
                },
                "maxAverageAttributes": {
                    "physicalPower": 7,
                    "physicalStamina": 7,
                    "physicalResistance": 7,
                    "magicPower": 7,
                    "magicStamina": 7,
                    "magicResistance": 7,
                },
            }
        )
        goblin = race_service.get_race("Goblin")
        weak_unit = unit_service.create_unit_from_dict(
            {
                "baseRaceId": goblin.raceId,
                "name": "Goblin Raider",
                "gearOptions": {"primaryWeaponOptions": [weak_weapon.itemId]},
                "spellList": [[], ["Hex"]],
            }
        )
        strong_unit = unit_service.create_unit_from_dict(
            {
                "baseRaceId": goblin.raceId,
                "name": "Goblin Champion",
                "gearOptions": {"primaryWeaponOptions": [strong_weapon.itemId]},
                "spellList": [[], ["Flare Lance"]],
            }
        )
        return weak_unit, strong_unit

    def test_gear_options_round_trip_preserves_nothing_option(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            item_service, spell_service, character_service, race_service, unit_service, _power_rating_service = (
                self._build_services(temp_dir)
            )
            self._seed_unit_data(item_service, spell_service, character_service, race_service, unit_service)
            armor = item_service.get_item("Scrap Vest")
            gear_options = GearOptions.from_dict(
                {"bodyOptions": [armor.itemId, GearOptions.NONE_OPTION_ID]},
                resolve_item=item_service.get_item,
            )

            self.assertEqual(getattr(gear_options.bodyOptions[0], "itemId", ""), armor.itemId)
            self.assertIsNone(gear_options.bodyOptions[1])
            self.assertEqual(
                gear_options.to_dict(resolve_item_id=lambda item: getattr(item, "itemId", ""))["bodyOptions"],
                [armor.itemId, GearOptions.NONE_OPTION_ID],
            )

    def test_populator_generates_required_units_first(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            services = self._build_services(temp_dir)
            weak_unit, _strong_unit = self._seed_unit_data(*services[:5])
            populator = MissionUnitPopulator(services[4], services[5])
            mission = MissionTemplate.from_dict(
                {
                    "name": "Required Preview",
                    "objective": {"objectiveType": "SURVIVAL", "requiredHoursSurvived": 1.0},
                    "allegianceConfigs": [
                        {
                            "allegianceId": "Raiders1",
                            "powerPointCap": 200,
                            "levelMin": 1,
                            "levelMax": 1,
                            "unitOptions": [
                                {
                                    "unitId": weak_unit.unitId,
                                    "capacityMin": 2,
                                    "capacityMax": 2,
                                    "eliteChance": 1.0,
                                    "isBoss": False,
                                }
                            ],
                        }
                    ],
                }
            )

            preview = populator.populate(mission, seed=11)
            allegiance = preview.allegiances[0]
            group = allegiance.groups[0]

            self.assertEqual(group.count, 2)
            self.assertTrue(all(entry.isRequired for entry in group.units))
            self.assertTrue(all(entry.isElite for entry in group.units))
            self.assertTrue(all(entry.pointsSpent > 0 for entry in group.units))
            self.assertTrue(
                all(getattr(entry.character.gear, "primaryWeapon", None) is not None for entry in group.units)
            )
            self.assertTrue(all(getattr(entry.character, "spells", []) for entry in group.units))
            self.assertEqual(allegiance.unusedPoints, allegiance.powerPointCap - allegiance.pointsSpent)

    def test_populator_leaves_unused_points_when_no_unit_is_affordable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            services = self._build_services(temp_dir)
            _weak_unit, strong_unit = self._seed_unit_data(*services[:5])
            populator = MissionUnitPopulator(services[4], services[5])

            roomy_template = MissionTemplate.from_dict(
                {
                    "name": "Roomy Preview",
                    "objective": {"objectiveType": "SURVIVAL", "requiredHoursSurvived": 1.0},
                    "allegianceConfigs": [
                        {
                            "allegianceId": "Raiders1",
                            "powerPointCap": 999,
                            "levelMin": 1,
                            "levelMax": 1,
                            "unitOptions": [{"unitId": strong_unit.unitId, "capacityMax": 1}],
                        }
                    ],
                }
            )
            sampled_cost = populator.populate(roomy_template, seed=21).allegiances[0].groups[0].units[0].pointsSpent
            tight_cap = max(0, sampled_cost - 1)

            tight_template = MissionTemplate.from_dict(
                {
                    "name": "Tight Preview",
                    "objective": {"objectiveType": "SURVIVAL", "requiredHoursSurvived": 1.0},
                    "allegianceConfigs": [
                        {
                            "allegianceId": "Raiders1",
                            "powerPointCap": tight_cap,
                            "levelMin": 1,
                            "levelMax": 1,
                            "unitOptions": [{"unitId": strong_unit.unitId, "capacityMax": 1}],
                        }
                    ],
                }
            )

            preview = populator.populate(tight_template, seed=21)
            allegiance = preview.allegiances[0]
            self.assertEqual(allegiance.generatedUnits, [])
            self.assertEqual(allegiance.unusedPoints, tight_cap)
            self.assertEqual(allegiance.pointsSpent, 0)

    def test_populator_respects_unit_caps_across_multiple_options(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            services = self._build_services(temp_dir)
            weak_unit, strong_unit = self._seed_unit_data(*services[:5])
            populator = MissionUnitPopulator(services[4], services[5])
            mission = MissionTemplate.from_dict(
                {
                    "name": "Cap Preview",
                    "objective": {"objectiveType": "SURVIVAL", "requiredHoursSurvived": 1.0},
                    "allegianceConfigs": [
                        {
                            "allegianceId": "Raiders1",
                            "powerPointCap": 999,
                            "levelMin": 1,
                            "levelMax": 1,
                            "unitOptions": [
                                {"unitId": weak_unit.unitId, "capacityMax": 1},
                                {"unitId": strong_unit.unitId, "capacityMax": 2, "isBoss": True},
                            ],
                        }
                    ],
                }
            )

            preview = populator.populate(mission, seed=7)
            allegiance = preview.allegiances[0]
            counts = {group.unitId: group.count for group in allegiance.groups}

            self.assertEqual(counts[weak_unit.unitId], 1)
            self.assertEqual(counts[strong_unit.unitId], 2)
            self.assertEqual(sum(group.pointsSpent for group in allegiance.groups), allegiance.pointsSpent)
            self.assertTrue(
                any(entry.isBoss for entry in allegiance.generatedUnits if entry.unitId == strong_unit.unitId)
            )

    def test_populator_can_choose_nothing_for_optional_body_armor(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            item_service, spell_service, character_service, race_service, unit_service, power_rating_service = (
                self._build_services(temp_dir)
            )
            self._seed_unit_data(item_service, spell_service, character_service, race_service, unit_service)
            goblin = race_service.get_race("Goblin")
            weak_weapon = item_service.get_item("Rusty Blade")
            armor = item_service.get_item("Scrap Vest")
            unit = unit_service.create_unit_from_dict(
                {
                    "baseRaceId": goblin.raceId,
                    "name": "Goblin Fighter",
                    "gearOptions": {
                        "primaryWeaponOptions": [weak_weapon.itemId],
                        "bodyOptions": [armor.itemId, GearOptions.NONE_OPTION_ID],
                    },
                }
            )
            populator = MissionUnitPopulator(unit_service, power_rating_service)
            mission = MissionTemplate.from_dict(
                {
                    "name": "Armor Mix Preview",
                    "objective": {"objectiveType": "SURVIVAL", "requiredHoursSurvived": 1.0},
                    "allegianceConfigs": [
                        {
                            "allegianceId": "Raiders1",
                            "powerPointCap": 999,
                            "levelMin": 1,
                            "levelMax": 1,
                            "unitOptions": [{"unitId": unit.unitId, "capacityMax": 8}],
                        }
                    ],
                }
            )

            preview = populator.populate(mission, seed=5)
            bodies = [getattr(entry.character.gear, "body", None) for entry in preview.allegiances[0].generatedUnits]

            self.assertEqual(len(bodies), 8)
            self.assertTrue(any(body is None for body in bodies))
            self.assertTrue(any(body is not None for body in bodies))


if __name__ == "__main__":
    unittest.main()
