from __future__ import annotations

import csv
import importlib.util
import re
from functools import lru_cache
from pathlib import Path

from src.domain.MainCharacter import HobbyInterestLevel


DEFAULT_GENERATION_DATA_DIRECTORY = Path(__file__).resolve().parents[2] / "GameData" / "CharacterGenerationData"

TRAIT_FILE_MAP = {
    "background": "background.csv",
    "build": "build.csv",
    "skinTone": "skin_tone.csv",
    "hairColor": "hair_color.csv",
    "eyeColor": "eye_color.csv",
    "distinguishingMarks": "distinguishing_marks.csv",
    "occupation": "occupation.csv",
    "personalityType": "personality_type.csv",
    "coreValue": "core_value.csv",
    "strength": "strength.csv",
    "flaw": "flaw.csv",
    "socialStyle": "social_style.csv",
    "speechStyle": "speech_style.csv",
    "goal": "goal.csv",
    "secret": "secret.csv",
    "emotionalTrigger": "emotional_trigger.csv",
    "copingHabit": "coping_habit.csv",
}

ATTRIBUTE_FIELDS = (
    "physicalPower",
    "physicalStamina",
    "physicalResistance",
    "magicPower",
    "magicStamina",
    "magicResistance",
)

PHYSICAL_ATTRIBUTE_FIELDS = (
    "physicalPower",
    "physicalStamina",
    "physicalResistance",
)

BUILD_MODIFIERS = {
    "underweight": {field: -1 for field in PHYSICAL_ATTRIBUTE_FIELDS},
    "slim": {"physicalStamina": 1},
    "average": {},
    "fit": {field: 2 for field in PHYSICAL_ATTRIBUTE_FIELDS},
    "muscular": {field: 3 for field in PHYSICAL_ATTRIBUTE_FIELDS},
    "overweight": {"physicalResistance": 1, "physicalStamina": -1},
    "obese": {field: -2 for field in PHYSICAL_ATTRIBUTE_FIELDS},
}

HOBBY_COUNT_OPTIONS = (
    (0, 15.0),
    (1, 18.0),
    (2, 30.15),
    (3, 20.10),
    (4, 10.05),
    (5, 6.70),
)

HOBBY_STYLE_OPTIONS = (
    ("Casual dabbler", 30.0),
    ("Balanced hobbyist", 45.0),
    ("Enthusiast", 20.0),
    ("Obsessive", 5.0),
)

HOBBY_INTEREST_OPTIONS = {
    "Casual dabbler": (
        (HobbyInterestLevel.BURNING_PASSION, 2.0),
        (HobbyInterestLevel.PASSIONATE, 13.0),
        (HobbyInterestLevel.INTERESTED, 45.0),
        (HobbyInterestLevel.INDIFFERENT, 40.0),
    ),
    "Balanced hobbyist": (
        (HobbyInterestLevel.BURNING_PASSION, 4.0),
        (HobbyInterestLevel.PASSIONATE, 21.0),
        (HobbyInterestLevel.INTERESTED, 50.0),
        (HobbyInterestLevel.INDIFFERENT, 25.0),
    ),
    "Enthusiast": (
        (HobbyInterestLevel.BURNING_PASSION, 8.0),
        (HobbyInterestLevel.PASSIONATE, 32.0),
        (HobbyInterestLevel.INTERESTED, 45.0),
        (HobbyInterestLevel.INDIFFERENT, 15.0),
    ),
    "Obsessive": (
        (HobbyInterestLevel.BURNING_PASSION, 15.0),
        (HobbyInterestLevel.PASSIONATE, 40.0),
        (HobbyInterestLevel.INTERESTED, 35.0),
        (HobbyInterestLevel.INDIFFERENT, 10.0),
    ),
}

SINGLE_HOBBY_INDIFFERENT_WEIGHT = 3.0
NO_HOBBY_ENTRY = ("No particular hobby", HobbyInterestLevel.INDIFFERENT)


@lru_cache(maxsize=1)
def default_generation_directory() -> Path:
    return DEFAULT_GENERATION_DATA_DIRECTORY.resolve()


@lru_cache(maxsize=8)
def load_age_height_module(module_path_text: str):
    module_path = Path(module_path_text)
    spec = importlib.util.spec_from_file_location("character_generation_age_height", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load generation helper from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=128)
def load_weighted_options(csv_path_text: str) -> tuple[tuple[str, float], ...]:
    csv_path = Path(csv_path_text)
    raw_lines = csv_path.read_text(encoding="utf-8-sig").splitlines()
    lines = [line for line in raw_lines if line.strip()]
    if not lines:
        return tuple()

    reader = csv.DictReader(lines)
    options: list[tuple[str, float]] = []
    for row in reader:
        option = str(row.get("option", "") or "").strip()
        raw_weight = row.get("weight", 0)
        overflow = row.get(None) if isinstance(row.get(None), list) else []

        if overflow:
            overflow_parts = [str(part or "").strip() for part in overflow if str(part or "").strip()]
            merged_option_parts = [part for part in (option, str(raw_weight or "").strip()) if part]
            if overflow_parts:
                merged_option_parts.extend(overflow_parts[:-1])
                raw_weight = overflow_parts[-1]
            option = ", ".join(merged_option_parts)

        option = option.strip()
        if not option:
            continue
        try:
            weight = float(raw_weight or 0)
        except Exception:
            weight = 0.0
        if weight <= 0:
            continue
        options.append((option, weight))
    return tuple(options)


def slugify(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", str(value or "").strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized


def choose_weighted_option(options, rng):
    if not options:
        return ""
    choices = [option for option, _weight in options]
    weights = [weight for _option, weight in options]
    return rng.choices(choices, weights=weights, k=1)[0]


def choose_weighted_unique_options(
    options: tuple[tuple[str, float], ...],
    count: int,
    rng,
) -> list[str]:
    remaining = list(options)
    selected: list[str] = []
    while remaining and len(selected) < max(0, int(count)):
        chosen = choose_weighted_option(tuple(remaining), rng)
        chosen_text = str(chosen or "").strip()
        if not chosen_text:
            break
        selected.append(chosen_text)
        remaining = [entry for entry in remaining if str(entry[0] or "").strip() != chosen_text]
    return selected


def resolve_generation_directory(generation_data_directory: str | None) -> Path:
    if generation_data_directory:
        return Path(generation_data_directory).resolve()
    return default_generation_directory()
