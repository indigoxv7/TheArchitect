from __future__ import annotations

import json
import os
import random
import re
from pathlib import Path

from src.domain.combat.encounter import EncounterDefinition, EncounterEnemyEntry, ReinforcementEntry
from src.domain.combat.enums import EncounterType


class EncounterService:
    def __init__(self, portal_encounter_directory: str, context, race_service, character_service):
        self.portal_encounter_directory = portal_encounter_directory
        self.context = context
        self.race_service = race_service
        self.character_service = character_service
        self._rng = random.Random()
        self._portal_templates: list[EncounterDefinition] = []

    @staticmethod
    def _slugify_name(name: str) -> str:
        compact = re.sub(r"\s+", "", str(name or "").strip())
        compact = re.sub(r"[^A-Za-z0-9_\-]", "", compact)
        return compact or "Encounter"

    def ensure_directory(self):
        os.makedirs(self.portal_encounter_directory, exist_ok=True)

    def load_portal_templates(self):
        self.ensure_directory()
        self._portal_templates = []
        for path in sorted(Path(self.portal_encounter_directory).glob("*.json")):
            with open(path, "r", encoding="utf-8-sig") as file:
                payload = json.load(file)
            if not isinstance(payload, dict):
                continue
            try:
                encounter = EncounterDefinition.from_dict(payload)
            except Exception:
                continue
            if encounter.encounter_type != EncounterType.PORTAL:
                encounter.encounter_type = EncounterType.PORTAL
            self._portal_templates.append(encounter)

    def _party_characters(self, player) -> list:
        get_mission_party = getattr(player, "GetMissionPartyCharacters", None)
        if callable(get_mission_party):
            return list(get_mission_party())
        return list(getattr(player, "characters", []) or [])

    def _party_strength(self, player) -> float:
        total = 0.0
        for character in self._party_characters(player):
            attrs = getattr(character, "finalAttributes", getattr(character, "attributes", None))
            attr_total = 0.0
            if attrs is not None:
                attr_total = (
                    float(getattr(attrs, "physicalPower", 5.0))
                    + float(getattr(attrs, "physicalStamina", 5.0))
                    + float(getattr(attrs, "physicalResistance", 5.0))
                    + float(getattr(attrs, "magicPower", 5.0))
                    + float(getattr(attrs, "magicStamina", 5.0))
                    + float(getattr(attrs, "magicResistance", 5.0))
                ) / 6.0
            total += max(1.0, float(getattr(character, "level", 0) or 0) + attr_total)
        return max(1.0, total)

    def create_scavenging_encounter(self, player) -> EncounterDefinition:
        party_strength = self._party_strength(player)
        race_candidates = [
            race
            for race in self.context.all_races.values()
            if str(getattr(race, "raceId", "") or "")
        ]
        if not race_candidates:
            raise ValueError("At least one race is required for scavenging encounters.")

        non_human = [race for race in race_candidates if str(getattr(race, "raceId", "")) != "Human1"]
        selected_race = self._rng.choice(non_human or race_candidates)
        threat_budget = max(1, round(party_strength / 4.0))
        enemy_count = max(1, min(6, threat_budget + self._rng.choice([0, 1, 1, 2])))
        width = 3 if enemy_count <= 3 else 4
        total_lines = self._rng.choice([5, 6, 7])
        player_front = total_lines // 2
        enemy_front = player_front + 1
        front_shift = self._rng.choice([-1, 0, 0, 1])
        if 0 <= player_front + front_shift < total_lines - 1:
            player_front += front_shift
            enemy_front += front_shift

        enemy_entries = [
            EncounterEnemyEntry(
                kind="race",
                identifier=str(getattr(selected_race, "raceId", "") or "Human1"),
                count=enemy_count,
                use_stack=enemy_count > 1,
                notable=False,
            )
        ]

        if enemy_count >= 3 and getattr(selected_race, "averageSpecimine", None) is not None:
            average_template = getattr(selected_race, "averageSpecimine", None)
            average_id = None
            for character_id, character in self.context.all_characters.items():
                if character is average_template or getattr(character, "name", "") == getattr(average_template, "name", ""):
                    average_id = character_id
                    break
            if average_id:
                enemy_entries.append(
                    EncounterEnemyEntry(
                        kind="character",
                        identifier=average_id,
                        count=1,
                        use_stack=False,
                        notable=True,
                        name_override=f"{selected_race.name} Leader",
                    )
                )

        encounter_name = f"Scavenging - {getattr(selected_race, 'name', 'Unknown') } Patrol"
        return EncounterDefinition(
            encounter_id=f"scavenge_{self._slugify_name(encounter_name)}_{enemy_count}",
            encounter_type=EncounterType.SCAVENGING,
            name=encounter_name,
            terrain=self._rng.choice(["Ruins", "Woodland", "Scrubland", "Roadside", "Broken Village"]),
            width=width,
            total_lines=total_lines,
            objective_text="Survive the engagement and drive off the scavenging force.",
            allow_retreat=True,
            enemy_entries=enemy_entries,
            reinforcements=[],
            player_front_line=player_front,
            enemy_front_line=enemy_front,
        )

    def create_portal_encounter(self, player) -> EncounterDefinition:
        if not self._portal_templates:
            self.load_portal_templates()
        if self._portal_templates:
            template = self._rng.choice(self._portal_templates)
            return EncounterDefinition.from_dict(template.to_dict())

        goblin_id = "Goblin0" if "Goblin0" in self.context.all_races else next(iter(self.context.all_races.keys()), "Human1")
        return EncounterDefinition(
            encounter_id="portal_default_0",
            encounter_type=EncounterType.PORTAL,
            name="Portal Breach",
            terrain="Shattered Threshold",
            width=4,
            total_lines=7,
            objective_text="Break the invading force before they can stabilize the breach.",
            allow_retreat=False,
            enemy_entries=[EncounterEnemyEntry(kind="race", identifier=goblin_id, count=4, use_stack=True)],
            reinforcements=[
                ReinforcementEntry(
                    exchange_number=3,
                    entries=[EncounterEnemyEntry(kind="race", identifier=goblin_id, count=2, use_stack=True)],
                    message="More invaders spill out of the portal.",
                )
            ],
            player_front_line=3,
            enemy_front_line=4,
        )

