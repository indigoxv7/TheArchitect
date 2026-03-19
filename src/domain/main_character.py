import copy
import enum

from src.domain.character import Character
from src.domain.character_util import CharacterStatistics


class HobbyInterestLevel(enum.Enum):
    BURNING_PASSION = "BurningPassion"
    PASSIONATE = "Passionate"
    INTERESTED = "Interested"
    INDIFFERENT = "Indifferent"


class CharacterInfo:
    FIELD_SPECS = [
        ("age", "Age"),
        ("birthday", "Birthday"),
        ("sex", "Sex"),
        ("height", "Height"),
        ("build", "Build"),
        ("skinTone", "Skin Tone"),
        ("hairColor", "Hair Color"),
        ("eyeColor", "Eye Color"),
        ("distinguishingMarks", "Distinguishing Marks"),
        ("distinguishingMarksLocation", "Distinguishing Marks Location"),
        ("background", "Background"),
        ("occupation", "Occupation"),
        ("job", "Job"),
        ("personalityType", "Personality Type"),
        ("coreValue", "Core Value"),
        ("strength", "Strength"),
        ("flaw", "Flaw"),
        ("socialStyle", "Social Style"),
        ("speechStyle", "Speech Style"),
        ("goal", "Goal"),
        ("secret", "Secret"),
        ("emotionalTrigger", "Emotional Trigger"),
        ("copingHabit", "Coping Habit"),
    ]

    def __init__(
        self,
        age: int = 0,
        birthday: str = "",
        sex: str = "",
        height: str = "",
        build: str = "",
        skinTone: str = "",
        hairColor: str = "",
        eyeColor: str = "",
        distinguishingMarks: str = "",
        distinguishingMarksLocation: str = "",
        background: str = "",
        occupation: str = "",
        job: str = "",
        personalityType: str = "",
        coreValue: str = "",
        strength: str = "",
        flaw: str = "",
        socialStyle: str = "",
        speechStyle: str = "",
        goal: str = "",
        secret: str = "",
        emotionalTrigger: str = "",
        copingHabit: str = "",
    ):
        self.age = int(age or 0)
        self.birthday = str(birthday or "")
        self.sex = str(sex or "")
        self.height = str(height or "")
        self.build = str(build or "")
        self.skinTone = str(skinTone or "")
        self.hairColor = str(hairColor or "")
        self.eyeColor = str(eyeColor or "")
        self.distinguishingMarks = str(distinguishingMarks or "")
        self.distinguishingMarksLocation = str(distinguishingMarksLocation or "")
        self.background = str(background or "")
        self.occupation = str(occupation or "")
        self.job = str(job or "")
        self.personalityType = str(personalityType or "")
        self.coreValue = str(coreValue or "")
        self.strength = str(strength or "")
        self.flaw = str(flaw or "")
        self.socialStyle = str(socialStyle or "")
        self.speechStyle = str(speechStyle or "")
        self.goal = str(goal or "")
        self.secret = str(secret or "")
        self.emotionalTrigger = str(emotionalTrigger or "")
        self.copingHabit = str(copingHabit or "")

    def to_dict(self) -> dict[str, object]:
        return {
            "age": int(self.age),
            "birthday": self.birthday,
            "sex": self.sex,
            "height": self.height,
            "build": self.build,
            "skinTone": self.skinTone,
            "hairColor": self.hairColor,
            "eyeColor": self.eyeColor,
            "distinguishingMarks": self.distinguishingMarks,
            "distinguishingMarksLocation": self.distinguishingMarksLocation,
            "background": self.background,
            "occupation": self.occupation,
            "job": self.job,
            "personalityType": self.personalityType,
            "coreValue": self.coreValue,
            "strength": self.strength,
            "flaw": self.flaw,
            "socialStyle": self.socialStyle,
            "speechStyle": self.speechStyle,
            "goal": self.goal,
            "secret": self.secret,
            "emotionalTrigger": self.emotionalTrigger,
            "copingHabit": self.copingHabit,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> "CharacterInfo":
        data = data if isinstance(data, dict) else {}
        return cls(
            age=int(data.get("age", 0) or 0),
            birthday=str(data.get("birthday", "") or ""),
            sex=str(data.get("sex", "") or ""),
            height=str(data.get("height", "") or ""),
            build=str(data.get("build", "") or ""),
            skinTone=str(data.get("skinTone", "") or ""),
            hairColor=str(data.get("hairColor", "") or ""),
            eyeColor=str(data.get("eyeColor", "") or ""),
            distinguishingMarks=str(data.get("distinguishingMarks", "") or ""),
            distinguishingMarksLocation=str(data.get("distinguishingMarksLocation", "") or ""),
            background=str(data.get("background", "") or ""),
            occupation=str(data.get("occupation", "") or ""),
            job=str(data.get("job", "") or ""),
            personalityType=str(data.get("personalityType", "") or ""),
            coreValue=str(data.get("coreValue", "") or ""),
            strength=str(data.get("strength", "") or ""),
            flaw=str(data.get("flaw", "") or ""),
            socialStyle=str(data.get("socialStyle", "") or ""),
            speechStyle=str(data.get("speechStyle", "") or ""),
            goal=str(data.get("goal", "") or ""),
            secret=str(data.get("secret", "") or ""),
            emotionalTrigger=str(data.get("emotionalTrigger", "") or ""),
            copingHabit=str(data.get("copingHabit", "") or ""),
        )


class LLMControlProfile:
    FIELD_SPECS = [
        ("systemNotes", "System Notes"),
        ("voiceNotes", "Voice Notes"),
        ("responseStyleNotes", "Response Style Notes"),
        ("knowledgeBoundaryNotes", "Knowledge Boundary Notes"),
    ]

    def __init__(
        self,
        systemNotes: str = "",
        voiceNotes: str = "",
        responseStyleNotes: str = "",
        knowledgeBoundaryNotes: str = "",
    ):
        self.systemNotes = str(systemNotes or "")
        self.voiceNotes = str(voiceNotes or "")
        self.responseStyleNotes = str(responseStyleNotes or "")
        self.knowledgeBoundaryNotes = str(knowledgeBoundaryNotes or "")

    def to_dict(self) -> dict[str, str]:
        return {
            "systemNotes": self.systemNotes,
            "voiceNotes": self.voiceNotes,
            "responseStyleNotes": self.responseStyleNotes,
            "knowledgeBoundaryNotes": self.knowledgeBoundaryNotes,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> "LLMControlProfile":
        data = data if isinstance(data, dict) else {}
        return cls(
            systemNotes=str(data.get("systemNotes", "") or ""),
            voiceNotes=str(data.get("voiceNotes", "") or ""),
            responseStyleNotes=str(data.get("responseStyleNotes", "") or ""),
            knowledgeBoundaryNotes=str(data.get("knowledgeBoundaryNotes", "") or ""),
        )


class MainCharacter(Character):
    def __init__(
        self,
        name: str,
        characterInfo: CharacterInfo | None = None,
        llmControlProfile: LLMControlProfile | None = None,
        stats: CharacterStatistics | None = None,
        hobbies: list[tuple[str, HobbyInterestLevel]] | list[list[object]] | None = None,
        **kwargs,
    ):
        super().__init__(name=name, **kwargs)
        self.characterInfo = characterInfo if characterInfo is not None else CharacterInfo()
        self.llmControlProfile = llmControlProfile if llmControlProfile is not None else LLMControlProfile()
        self.stats = stats if stats is not None else CharacterStatistics()
        self.hobbies = self._normalize_hobbies(hobbies)

    @staticmethod
    def _normalize_hobbies(
        hobbies: list[tuple[str, HobbyInterestLevel]] | list[list[object]] | None,
    ) -> list[tuple[str, HobbyInterestLevel]]:
        normalized: list[tuple[str, HobbyInterestLevel]] = []
        if not isinstance(hobbies, list):
            return normalized

        for entry in hobbies:
            if not isinstance(entry, (list, tuple)) or len(entry) < 2:
                continue
            hobby_name = str(entry[0] or "").strip()
            if not hobby_name:
                continue

            interest_level = entry[1]
            if isinstance(interest_level, HobbyInterestLevel):
                normalized.append((hobby_name, interest_level))
                continue

            if isinstance(interest_level, str):
                raw_value = interest_level.strip()
                for option in HobbyInterestLevel:
                    if raw_value.upper() == option.name or raw_value.lower() == option.value.lower():
                        normalized.append((hobby_name, option))
                        break
        return normalized

    def EnsureRuntimeDefaults(self):
        super().EnsureRuntimeDefaults()
        if not hasattr(self, "characterInfo") or self.characterInfo is None:
            self.characterInfo = CharacterInfo()
        elif isinstance(self.characterInfo, dict):
            self.characterInfo = CharacterInfo.from_dict(self.characterInfo)
        if not hasattr(self, "llmControlProfile") or self.llmControlProfile is None:
            self.llmControlProfile = LLMControlProfile()
        elif isinstance(self.llmControlProfile, dict):
            self.llmControlProfile = LLMControlProfile.from_dict(self.llmControlProfile)
        if not hasattr(self, "stats") or self.stats is None:
            self.stats = CharacterStatistics()
        elif isinstance(self.stats, dict):
            self.stats = CharacterStatistics(**self.stats)
        if not hasattr(self, "hobbies") or self.hobbies is None:
            self.hobbies = []
        else:
            self.hobbies = self._normalize_hobbies(self.hobbies)

    @classmethod
    def from_character(
        cls,
        base_character: Character,
        generation_data_directory: str | None = None,
        rng=None,
    ) -> "MainCharacter":
        if isinstance(base_character, MainCharacter):
            character_info = copy.deepcopy(base_character.characterInfo)
            llm_profile = copy.deepcopy(base_character.llmControlProfile)
            hobbies = copy.deepcopy(base_character.hobbies)
        else:
            from src.services.character_generation import generate_character_info, generate_hobbies

            character_info = generate_character_info(
                generation_data_directory=generation_data_directory,
                rng=rng,
            )
            llm_profile = LLMControlProfile()
            hobbies = generate_hobbies(
                generation_data_directory=generation_data_directory,
                rng=rng,
            )

        main_character = cls(
            name=str(getattr(base_character, "name", "") or "Generated Main Character"),
            attributes=copy.deepcopy(getattr(base_character, "attributes", None)),
            level=int(getattr(base_character, "level", 0)),
            raceTier=str(getattr(base_character, "raceTier", "Tier I") or "Tier I"),
            affinities=copy.deepcopy(getattr(base_character, "affinities", None)),
            gear=copy.deepcopy(getattr(base_character, "gear", None)),
            achievements=copy.deepcopy(getattr(base_character, "achievements", None)),
            generalSkills=copy.deepcopy(getattr(base_character, "generalSkills", None)),
            spells=copy.deepcopy(getattr(base_character, "spells", None)),
            buffs=copy.deepcopy(getattr(base_character, "buffs", None)),
            stats=copy.deepcopy(getattr(base_character, "stats", None)),
            race=str(getattr(base_character, "race", "Human1") or "Human1"),
            playerInstanceId=str(getattr(base_character, "playerInstanceId", "") or ""),
            characterInfo=character_info,
            llmControlProfile=llm_profile,
            hobbies=hobbies,
        )
        main_character.health = int(getattr(base_character, "health", 100))
        main_character.healthState = getattr(base_character, "healthState", main_character.healthState)
        main_character.activeAchievementTitle = str(
            getattr(base_character, "activeAchievementTitle", "") or ""
        )
        main_character.description = str(getattr(base_character, "description", "") or "")
        main_character.portraitURL = str(getattr(base_character, "portraitURL", "") or "")
        main_character.footerImageURL = str(getattr(base_character, "footerImageURL", "") or "")
        main_character.CalculateBonus()
        return main_character

