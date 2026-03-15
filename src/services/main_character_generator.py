import csv
import copy
import importlib.util
import random
import re
from datetime import date
from functools import lru_cache
from pathlib import Path

from src.domain.Character import Character
from src.domain.CharacterUtil import Attributes, BodyPart
from src.domain.MainCharacter import CharacterInfo, MainCharacter
from src.domain.Race import Race

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


def _coerce_int(value, default: int = 5) -> int:
    try:
        return int(round(float(value)))
    except Exception:
        return int(default)


def _attributes_to_int_dict(attributes: Attributes | None, default: int = 5) -> dict[str, int]:
    attributes = attributes if attributes is not None else Attributes()
    return {field: _coerce_int(getattr(attributes, field, default), default) for field in ATTRIBUTE_FIELDS}


def _attributes_from_int_dict(values: dict[str, int]) -> Attributes:
    return Attributes(
        physicalPower=_coerce_int(values.get("physicalPower", 5), 5),
        physicalStamina=_coerce_int(values.get("physicalStamina", 5), 5),
        physicalResistance=_coerce_int(values.get("physicalResistance", 5), 5),
        magicPower=_coerce_int(values.get("magicPower", 5), 5),
        magicStamina=_coerce_int(values.get("magicStamina", 5), 5),
        magicResistance=_coerce_int(values.get("magicResistance", 5), 5),
    )


def _clamp_attribute_dict(values: dict[str, int], minimums: dict[str, int], maximums: dict[str, int]) -> dict[str, int]:
    clamped = {}
    for field in ATTRIBUTE_FIELDS:
        low = minimums.get(field, values.get(field, 5))
        high = maximums.get(field, values.get(field, 5))
        if high < low:
            high = low
        clamped[field] = max(low, min(high, values.get(field, 5)))
    return clamped


def _normalize_build_key(build_value: str) -> str:
    return str(build_value or "").strip().lower().replace("-", " ").replace("_", " ")


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


def randomize_attributes_point_buy(
    race: Race | None,
    starting_attributes: Attributes | None = None,
    rng: random.Random | None = None,
) -> Attributes:
    rng = rng if rng is not None else random.Random()
    base_attributes = starting_attributes
    if base_attributes is None and race is not None and getattr(race, 'averageSpecimine', None) is not None:
        base_attributes = getattr(race.averageSpecimine, 'attributes', None)
    current = _attributes_to_int_dict(base_attributes, default=5)

    minimums = _attributes_to_int_dict(getattr(race, 'minAverageAttributes', None), default=0) if race is not None else {field: 0 for field in ATTRIBUTE_FIELDS}
    maximums = _attributes_to_int_dict(getattr(race, 'maxAverageAttributes', None), default=99) if race is not None else {field: 99 for field in ATTRIBUTE_FIELDS}
    current = _clamp_attribute_dict(current, minimums, maximums)

    removable_total = sum(max(0, current[field] - minimums[field]) for field in ATTRIBUTE_FIELDS)
    if removable_total <= 0:
        return _attributes_from_int_dict(current)

    transfer_count = rng.randint(1, removable_total)
    unspent_points = 0
    for _ in range(transfer_count):
        donors = [field for field in ATTRIBUTE_FIELDS if current[field] > minimums[field]]
        if not donors:
            break
        donor = rng.choice(donors)
        current[donor] -= 1
        unspent_points += 1

    while unspent_points > 0:
        recipients = [field for field in ATTRIBUTE_FIELDS if current[field] < maximums[field]]
        if not recipients:
            break
        recipient = rng.choice(recipients)
        current[recipient] += 1
        unspent_points -= 1

    return _attributes_from_int_dict(_clamp_attribute_dict(current, minimums, maximums))


def apply_build_modifier(
    attributes: Attributes,
    build_value: str,
    minimum_attributes: Attributes | None = None,
    maximum_attributes: Attributes | None = None,
) -> Attributes:
    values = _attributes_to_int_dict(attributes, default=5)
    minimums = _attributes_to_int_dict(minimum_attributes, default=-999)
    maximums = _attributes_to_int_dict(maximum_attributes, default=999)

    modifier = BUILD_MODIFIERS.get(_normalize_build_key(build_value), {})
    for field, delta in modifier.items():
        values[field] = values.get(field, 5) + int(delta)

    return _attributes_from_int_dict(_clamp_attribute_dict(values, minimums, maximums))


def generate_character_from_race(
    name: str = "Generated Character",
    race: Race | None = None,
    rng: random.Random | None = None,
) -> Character:
    rng = rng if rng is not None else random.Random()
    template = race.averageSpecimine if race is not None and race.averageSpecimine is not None else None

    character = Character(
        name=str(name or "Generated Character"),
        attributes=copy.deepcopy(getattr(template, 'attributes', None)),
        level=int(getattr(template, 'level', 0) or 0),
        raceTier=str(getattr(template, 'raceTier', 'Tier I') or 'Tier I'),
        affinities=copy.deepcopy(getattr(template, 'affinities', None)),
        gear=copy.deepcopy(getattr(template, 'gear', None)),
        achievements=copy.deepcopy(getattr(template, 'achievements', None)),
        generalSkills=copy.deepcopy(getattr(template, 'generalSkills', None)),
        spells=copy.deepcopy(getattr(template, 'spells', None)),
        buffs=copy.deepcopy(getattr(template, 'buffs', None)),
        race=str(getattr(race, 'raceId', '') or getattr(template, 'race', 'Human1') or 'Human1'),
    )
    character.health = int(getattr(template, 'health', 100) or 100)
    character.healthState = copy.deepcopy(getattr(template, 'healthState', character.healthState))
    character.activeAchievementTitle = str(getattr(template, 'activeAchievementTitle', '') or '')
    character.description = str(getattr(template, 'description', '') or '')
    character.portraitURL = str(getattr(template, 'portraitURL', '') or '')
    character.footerImageURL = str(getattr(template, 'footerImageURL', '') or '')
    character.playerInstanceId = ''

    if race is not None:
        character.race = str(race.raceId or character.race or 'Human1')
        character.attributes = randomize_attributes_point_buy(
            race,
            starting_attributes=getattr(template, 'attributes', character.attributes),
            rng=rng,
        )

    character.CalculateBonus()
    return character


def generate_main_character_from_scratch(
    name: str = "Generated Main Character",
    race: Race | None = None,
    generation_data_directory: str | None = None,
    rng: random.Random | None = None,
    character_info: CharacterInfo | None = None,
) -> MainCharacter:
    rng = rng if rng is not None else random.Random()
    base_character = generate_character_from_race(name=name, race=race, rng=rng)
    info = copy.deepcopy(character_info) if character_info is not None else generate_character_info(
        generation_data_directory=generation_data_directory,
        rng=rng,
    )
    if not str(getattr(info, 'distinguishingMarksLocation', '') or '').strip():
        info.distinguishingMarksLocation = rng.choice(list(BodyPart)).name

    main_character = MainCharacter.from_character(
        base_character,
        generation_data_directory=generation_data_directory,
        rng=rng,
    )
    main_character.characterInfo = info

    minimums = getattr(race, 'minAverageAttributes', None) if race is not None else None
    maximums = getattr(race, 'maxAverageAttributes', None) if race is not None else None
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
