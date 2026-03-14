import csv
import importlib.util
import random
import re
from datetime import date
from functools import lru_cache
from pathlib import Path

from src.domain.MainCharacter import CharacterInfo, MainCharacter

DEFAULT_GENERATION_DATA_DIRECTORY = (
    Path(__file__).resolve().parents[2] / "GameData" / "CharacterGenerationData"
)

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


@lru_cache(maxsize=1)
def _default_generation_directory() -> Path:
    return DEFAULT_GENERATION_DATA_DIRECTORY.resolve()


@lru_cache(maxsize=8)
def _load_age_height_module(module_path_text: str):
    module_path = Path(module_path_text)
    spec = importlib.util.spec_from_file_location("character_generation_age_height", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load generation helper from {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=128)
def _load_weighted_options(csv_path_text: str) -> tuple[tuple[str, float], ...]:
    csv_path = Path(csv_path_text)
    raw_lines = csv_path.read_text(encoding="utf-8-sig").splitlines()
    lines = [line for line in raw_lines if line.strip()]
    if not lines:
        return tuple()

    reader = csv.DictReader(lines)
    options: list[tuple[str, float]] = []
    for row in reader:
        option = str(row.get("option", "") or "").strip()
        if not option:
            continue
        try:
            weight = float(row.get("weight", 0) or 0)
        except Exception:
            weight = 0.0
        if weight <= 0:
            continue
        options.append((option, weight))
    return tuple(options)


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", str(value or "").strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized


def _choose_weighted_option(options: tuple[tuple[str, float], ...], rng) -> str:
    if not options:
        return ""
    choices = [option for option, _weight in options]
    weights = [weight for _option, weight in options]
    return rng.choices(choices, weights=weights, k=1)[0]


def _format_height_inches(height_inches: float) -> str:
    feet = int(height_inches // 12)
    inches = round(float(height_inches) - (feet * 12), 1)
    if float(inches).is_integer():
        inches_text = str(int(inches))
    else:
        inches_text = f"{inches:.1f}"
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


def _resolve_generation_directory(generation_data_directory: str | None) -> Path:
    if generation_data_directory:
        return Path(generation_data_directory).resolve()
    return _default_generation_directory()


def _generate_trait(field_name: str, generation_directory: Path, rng) -> str:
    filename = TRAIT_FILE_MAP[field_name]
    options = _load_weighted_options(str(generation_directory / filename))
    return _choose_weighted_option(options, rng)


def _generate_job(occupation: str, generation_directory: Path, rng) -> str:
    if not occupation:
        return ""

    job_file = generation_directory / "JobsByOccupation" / f"{_slugify(occupation)}.csv"
    if not job_file.exists():
        return occupation

    options = _load_weighted_options(str(job_file))
    return _choose_weighted_option(options, rng)


def generate_character_info(
    generation_data_directory: str | None = None,
    rng: random.Random | None = None,
) -> CharacterInfo:
    rng = rng if rng is not None else random.Random()
    generation_directory = _resolve_generation_directory(generation_data_directory)
    age_height_module = _load_age_height_module(str(generation_directory / "Age and Height.py"))

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


def generate_main_character(
    name: str = "Generated Main Character",
    generation_data_directory: str | None = None,
    rng: random.Random | None = None,
) -> MainCharacter:
    character_info = generate_character_info(
        generation_data_directory=generation_data_directory,
        rng=rng,
    )
    return MainCharacter(name=str(name or "Generated Main Character"), characterInfo=character_info)