import copy

from src.domain.Character import Character


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


class MainCharacter(Character):
    def __init__(self, name: str, characterInfo: CharacterInfo | None = None, **kwargs):
        super().__init__(name=name, **kwargs)
        self.characterInfo = characterInfo if characterInfo is not None else CharacterInfo()

    @classmethod
    def from_character(
        cls,
        base_character: Character,
        generation_data_directory: str | None = None,
        rng=None,
    ) -> "MainCharacter":
        if isinstance(base_character, MainCharacter):
            character_info = copy.deepcopy(base_character.characterInfo)
        else:
            from src.services.main_character_generator import generate_main_character

            generated = generate_main_character(
                name=str(getattr(base_character, "name", "") or "Generated Main Character"),
                generation_data_directory=generation_data_directory,
                rng=rng,
            )
            character_info = copy.deepcopy(generated.characterInfo)

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
            party=int(getattr(base_character, "party", 0)),
            buffs=copy.deepcopy(getattr(base_character, "buffs", None)),
            stats=copy.deepcopy(getattr(base_character, "stats", None)),
            race=str(getattr(base_character, "race", "Human1") or "Human1"),
            characterInfo=character_info,
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