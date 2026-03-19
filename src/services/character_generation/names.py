from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from src.services.character_generation.data import (
    choose_weighted_option,
    load_weighted_options,
    resolve_generation_directory,
)


FIRST_NAMES_FEMALE_FILE = "first_names_female.csv"
FIRST_NAMES_MALE_FILE = "first_names_male.csv"
LAST_NAMES_FILE = "last_names.csv"


def is_placeholder_main_character_name(name: str, race_name: str | None = None) -> bool:
    normalized = str(name or "").strip().casefold()
    if not normalized:
        return True
    if normalized == "generated main character":
        return True
    if race_name and normalized == f"{str(race_name).strip()} main character".casefold():
        return True
    return False


def load_first_name_options(
    sex: str,
    generation_data_directory: str | None = None,
) -> tuple[tuple[str, float], ...]:
    generation_directory = resolve_generation_directory(generation_data_directory)
    normalized_sex = str(sex or "").strip().casefold()
    if normalized_sex == "female":
        return _load_name_options(generation_directory, FIRST_NAMES_FEMALE_FILE)
    if normalized_sex == "male":
        return _load_name_options(generation_directory, FIRST_NAMES_MALE_FILE)
    return _load_name_options(generation_directory, FIRST_NAMES_MALE_FILE) + _load_name_options(
        generation_directory,
        FIRST_NAMES_FEMALE_FILE,
    )


def load_last_name_options(
    generation_data_directory: str | None = None,
) -> tuple[tuple[str, float], ...]:
    generation_directory = resolve_generation_directory(generation_data_directory)
    return _load_name_options(generation_directory, LAST_NAMES_FILE)


def generate_character_name(
    sex: str,
    rng,
    generation_data_directory: str | None = None,
) -> str:
    first_name = str(
        choose_weighted_option(load_first_name_options(sex, generation_data_directory), rng) or "Generated"
    ).strip()
    surname = str(choose_weighted_option(load_last_name_options(generation_data_directory), rng) or "Traveler").strip()
    full_name = f"{first_name} {surname}".strip()
    return full_name or "Generated Main Character"


@lru_cache(maxsize=32)
def _load_name_options(
    generation_directory: Path,
    filename: str,
) -> tuple[tuple[str, float], ...]:
    weighted_options = load_weighted_options(str(generation_directory / filename))
    normalized: list[tuple[str, float]] = []
    for option, weight in weighted_options:
        name = _normalize_person_name(option)
        if name:
            normalized.append((name, float(weight)))
    return tuple(normalized)


def _normalize_person_name(value: str) -> str:
    text = " ".join(str(value or "").replace("_", " ").split())
    return text.title()
