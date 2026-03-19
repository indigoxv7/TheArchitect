from __future__ import annotations

import random
from datetime import date
from pathlib import Path

from src.domain.character_util import BodyPart
from src.domain.main_character import CharacterInfo, HobbyInterestLevel
from src.services.character_generation.data import (
    HOBBY_COUNT_OPTIONS,
    HOBBY_INTEREST_OPTIONS,
    HOBBY_STYLE_OPTIONS,
    NO_HOBBY_ENTRY,
    SINGLE_HOBBY_INDIFFERENT_WEIGHT,
    TRAIT_FILE_MAP,
    choose_weighted_option,
    choose_weighted_unique_options,
    load_age_height_module,
    load_weighted_options,
    resolve_generation_directory,
    slugify,
)


def _interest_options_for_profile(
    hobby_profile: str,
    hobby_count: int,
) -> tuple[tuple[HobbyInterestLevel, float], ...]:
    base_options = HOBBY_INTEREST_OPTIONS.get(hobby_profile, HOBBY_INTEREST_OPTIONS["Balanced hobbyist"])
    if int(hobby_count or 0) != 1:
        return base_options

    adjusted: list[tuple[HobbyInterestLevel, float]] = []
    indifferent_shift = 0.0
    for interest_level, weight in base_options:
        if interest_level == HobbyInterestLevel.INDIFFERENT:
            trimmed_weight = min(weight, SINGLE_HOBBY_INDIFFERENT_WEIGHT)
            indifferent_shift = max(0.0, weight - trimmed_weight)
            adjusted.append((interest_level, trimmed_weight))
        else:
            adjusted.append((interest_level, weight))

    if indifferent_shift > 0:
        adjusted = [
            (
                interest_level,
                weight + indifferent_shift if interest_level == HobbyInterestLevel.INTERESTED else weight,
            )
            for interest_level, weight in adjusted
        ]
    return tuple(adjusted)


def _format_height_inches(height_inches: float) -> str:
    feet = int(height_inches // 12)
    inches = round(float(height_inches) - (feet * 12), 1)
    inches_text = str(int(inches)) if float(inches).is_integer() else f"{inches:.1f}"
    return f"{feet}'{inches_text}\""


def _generate_birthday(age: int, rng) -> str:
    today = date.today()
    while True:
        month = rng.randint(1, 12)
        day = rng.randint(1, 31)
        try:
            birthday_this_year = date(today.year, month, day)
            break
        except ValueError:
            continue

    birth_year = today.year - int(age)
    if birthday_this_year > today:
        birth_year -= 1

    birthday = date(birth_year, month, day)
    return f"{birthday.strftime('%B')} {birthday.day}, {birthday.year}"


def _generate_trait(field_name: str, generation_directory: Path, rng) -> str:
    filename = TRAIT_FILE_MAP[field_name]
    options = load_weighted_options(str(generation_directory / filename))
    return choose_weighted_option(options, rng)


def _generate_job(occupation: str, generation_directory: Path, rng) -> str:
    if not occupation:
        return ""

    job_file = generation_directory / "JobsByOccupation" / f"{slugify(occupation)}.csv"
    if not job_file.exists():
        return occupation

    options = load_weighted_options(str(job_file))
    return choose_weighted_option(options, rng)


def generate_hobbies(
    generation_data_directory: str | None = None,
    rng: random.Random | None = None,
) -> list[tuple[str, HobbyInterestLevel]]:
    rng = rng if rng is not None else random.Random()
    generation_directory = resolve_generation_directory(generation_data_directory)
    hobby_options = load_weighted_options(str(generation_directory / "hobbies.csv"))
    hobby_count = int(choose_weighted_option(HOBBY_COUNT_OPTIONS, rng) or 0)

    if hobby_count <= 0 or not hobby_options:
        return [NO_HOBBY_ENTRY]

    hobby_profile = str(choose_weighted_option(HOBBY_STYLE_OPTIONS, rng) or "Balanced hobbyist")
    selected_hobbies = choose_weighted_unique_options(hobby_options, hobby_count, rng)
    if not selected_hobbies:
        return [NO_HOBBY_ENTRY]

    hobbies: list[tuple[str, HobbyInterestLevel]] = []
    has_burning_passion = False
    interest_options = _interest_options_for_profile(hobby_profile, len(selected_hobbies))
    for hobby_name in selected_hobbies:
        interest_level = choose_weighted_option(interest_options, rng)
        if not isinstance(interest_level, HobbyInterestLevel):
            interest_level = HobbyInterestLevel.INTERESTED
        if interest_level == HobbyInterestLevel.BURNING_PASSION:
            if has_burning_passion:
                interest_level = HobbyInterestLevel.PASSIONATE
            else:
                has_burning_passion = True
        hobbies.append((hobby_name, interest_level))

    return hobbies or [NO_HOBBY_ENTRY]


def generate_character_info(
    generation_data_directory: str | None = None,
    rng: random.Random | None = None,
) -> CharacterInfo:
    rng = rng if rng is not None else random.Random()
    generation_directory = resolve_generation_directory(generation_data_directory)
    age_height_module = load_age_height_module(str(generation_directory / "Age and Height.py"))

    sex = rng.choices(["Male", "Female"], weights=[49.5, 50.5], k=1)[0]
    age = int(age_height_module.generate_age(18, 80, rng=rng))
    birthday = _generate_birthday(age, rng)
    height_inches = float(age_height_module.generate_height_inches(sex, rng=rng))
    occupation = _generate_trait("occupation", generation_directory, rng)

    return CharacterInfo(
        age=age,
        birthday=birthday,
        sex=sex,
        height=_format_height_inches(height_inches),
        build=_generate_trait("build", generation_directory, rng),
        skinTone=_generate_trait("skinTone", generation_directory, rng),
        hairColor=_generate_trait("hairColor", generation_directory, rng),
        eyeColor=_generate_trait("eyeColor", generation_directory, rng),
        distinguishingMarks=_generate_trait("distinguishingMarks", generation_directory, rng),
        distinguishingMarksLocation=rng.choice(list(BodyPart)).name,
        background=_generate_trait("background", generation_directory, rng),
        occupation=occupation,
        job=_generate_job(occupation, generation_directory, rng),
        personalityType=_generate_trait("personalityType", generation_directory, rng),
        coreValue=_generate_trait("coreValue", generation_directory, rng),
        strength=_generate_trait("strength", generation_directory, rng),
        flaw=_generate_trait("flaw", generation_directory, rng),
        socialStyle=_generate_trait("socialStyle", generation_directory, rng),
        speechStyle=_generate_trait("speechStyle", generation_directory, rng),
        goal=_generate_trait("goal", generation_directory, rng),
        secret=_generate_trait("secret", generation_directory, rng),
        emotionalTrigger=_generate_trait("emotionalTrigger", generation_directory, rng),
        copingHabit=_generate_trait("copingHabit", generation_directory, rng),
    )

