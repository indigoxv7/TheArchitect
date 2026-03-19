from __future__ import annotations

import copy
import random

from src.domain.character import Character
from src.domain.character_util import BodyPart
from src.domain.main_character import CharacterInfo, MainCharacter
from src.domain.race import Race
from src.services.character_generation.attributes import apply_build_modifier, randomize_attributes_point_buy
from src.services.character_generation.names import generate_character_name, is_placeholder_main_character_name
from src.services.character_generation.traits import generate_character_info, generate_hobbies


def generate_character_from_race(
    name: str = "Generated Character",
    race: Race | None = None,
    rng: random.Random | None = None,
) -> Character:
    rng = rng if rng is not None else random.Random()
    template = race.averageSpecimine if race is not None and race.averageSpecimine is not None else None

    character = Character(
        name=str(name or "Generated Character"),
        attributes=copy.deepcopy(getattr(template, "attributes", None)),
        level=int(getattr(template, "level", 0) or 0),
        raceTier=str(getattr(template, "raceTier", "Tier I") or "Tier I"),
        affinities=copy.deepcopy(getattr(template, "affinities", None)),
        gear=copy.deepcopy(getattr(template, "gear", None)),
        achievements=copy.deepcopy(getattr(template, "achievements", None)),
        generalSkills=copy.deepcopy(getattr(template, "generalSkills", None)),
        spells=copy.deepcopy(getattr(template, "spells", None)),
        buffs=copy.deepcopy(getattr(template, "buffs", None)),
        race=str(getattr(race, "raceId", "") or getattr(template, "race", "Human1") or "Human1"),
    )
    character.health = int(getattr(template, "health", 100) or 100)
    character.healthState = copy.deepcopy(getattr(template, "healthState", character.healthState))
    character.activeAchievementTitle = str(getattr(template, "activeAchievementTitle", "") or "")
    character.description = str(getattr(template, "description", "") or "")
    character.portraitURL = str(getattr(template, "portraitURL", "") or "")
    character.footerImageURL = str(getattr(template, "footerImageURL", "") or "")
    character.playerInstanceId = ""

    if race is not None:
        character.race = str(race.raceId or character.race or "Human1")
        character.attributes = randomize_attributes_point_buy(
            race,
            starting_attributes=getattr(template, "attributes", character.attributes),
            rng=rng,
        )

    character.CalculateBonus()
    character.health = character.GetMaxHealth()
    character.RefreshHealthState()
    return character


def generate_main_character_from_scratch(
    name: str = "Generated Main Character",
    race: Race | None = None,
    generation_data_directory: str | None = None,
    rng: random.Random | None = None,
    character_info: CharacterInfo | None = None,
) -> MainCharacter:
    rng = rng if rng is not None else random.Random()
    info = copy.deepcopy(character_info) if character_info is not None else generate_character_info(
        generation_data_directory=generation_data_directory,
        rng=rng,
    )
    race_name = str(getattr(race, "name", "") or "").strip()
    resolved_name = str(name or "").strip()
    if is_placeholder_main_character_name(resolved_name, race_name=race_name):
        resolved_name = generate_character_name(
            getattr(info, "sex", ""),
            rng,
            generation_data_directory=generation_data_directory,
        )

    base_character = generate_character_from_race(name=resolved_name, race=race, rng=rng)
    hobbies = generate_hobbies(
        generation_data_directory=generation_data_directory,
        rng=rng,
    )
    if not str(getattr(info, "distinguishingMarksLocation", "") or "").strip():
        info.distinguishingMarksLocation = rng.choice(list(BodyPart)).name

    main_character = MainCharacter.from_character(
        base_character,
        generation_data_directory=generation_data_directory,
        rng=rng,
    )
    main_character.name = resolved_name
    main_character.characterInfo = info
    main_character.hobbies = hobbies

    minimums = getattr(race, "minAverageAttributes", None) if race is not None else None
    maximums = getattr(race, "maxAverageAttributes", None) if race is not None else None
    main_character.attributes = apply_build_modifier(
        main_character.attributes,
        info.build,
        minimum_attributes=minimums,
        maximum_attributes=maximums,
    )
    main_character.CalculateBonus()
    return main_character


def generate_character(
    name: str = "Generated Character",
    race: Race | None = None,
    rng: random.Random | None = None,
) -> Character:
    return generate_character_from_race(name=name, race=race, rng=rng)


def generate_main_character(
    name: str = "Generated Main Character",
    generation_data_directory: str | None = None,
    rng: random.Random | None = None,
    race: Race | None = None,
    character_info: CharacterInfo | None = None,
) -> MainCharacter:
    return generate_main_character_from_scratch(
        name=name,
        race=race,
        generation_data_directory=generation_data_directory,
        rng=rng,
        character_info=character_info,
    )

