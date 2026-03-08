import re

from src.domain.Race import Race
from src.persistence.racebook_store import RacebookStore
from src.services.game_context import GameContext


class RaceService:
    def __init__(self, racebook_path: str, context: GameContext, character_service, spell_service):
        self.context = context
        self.character_service = character_service
        self.spell_service = spell_service
        self.store = RacebookStore(racebook_path)

    @staticmethod
    def _slugify_name(name: str) -> str:
        compact = re.sub(r"\s+", "", str(name or "").strip())
        compact = re.sub(r"[^A-Za-z0-9_\-]", "", compact)
        return compact or "Race"

    def _generate_race_id(self, name: str) -> str:
        prefix = self._slugify_name(name)
        index = len(self.context.all_races)
        candidate = f"{prefix}{index}"
        while candidate in self.context.all_races:
            index += 1
            candidate = f"{prefix}{index}"
        return candidate

    def _resolve_character(self, character_identifier: str):
        key = str(character_identifier or "").strip()
        if not key:
            return None

        by_id = self.character_service.get_character(key)
        if by_id is not None:
            return by_id

        matches = []
        for _character_id, character in self.character_service.list_characters():
            if str(getattr(character, "name", "") or "").strip().lower() == key.lower():
                matches.append(character)

        if len(matches) == 1:
            return matches[0]
        return None

    def _resolve_spell(self, spell_identifier: str):
        key = str(spell_identifier or "").strip()
        if not key:
            return None
        return self.spell_service.get_spell(key)

    def _resolve_character_id(self, character_obj) -> str | None:
        if character_obj is None:
            return None

        for character_id, character in self.character_service.list_characters():
            if character is character_obj:
                return character_id

        target_name = str(getattr(character_obj, "name", "") or "").strip().lower()
        if not target_name:
            return None

        matches = []
        for character_id, character in self.character_service.list_characters():
            if str(getattr(character, "name", "") or "").strip().lower() == target_name:
                matches.append(character_id)

        if len(matches) == 1:
            return matches[0]
        return None

    def resolve_character_id(self, character_obj) -> str | None:
        return self._resolve_character_id(character_obj)

    @staticmethod
    def get_race_label(race: Race) -> str:
        return f"{race.name} [{race.raceId}]"

    @staticmethod
    def parse_race_id_from_label(label: str) -> str:
        text = str(label or "").strip()
        if text.endswith("]") and "[" in text:
            return text[text.rfind("[") + 1 : -1].strip()
        return text

    def load_racebook(self):
        payload = self.store.load()
        raw_races = payload.get("races", [])
        migrated = False

        self.context.all_races.clear()

        for race_data in raw_races:
            try:
                race = Race.from_dict(
                    race_data,
                    resolve_character=self._resolve_character,
                    resolve_spell=self._resolve_spell,
                )
            except Exception:
                continue

            if not race.raceId:
                race.raceId = self._generate_race_id(race.name)
                migrated = True

            if race.raceId in self.context.all_races:
                race.raceId = self._generate_race_id(race.name)
                migrated = True

            self.context.all_races[race.raceId] = race

        if migrated:
            self.save_racebook()
        else:
            self.context.racebook_overview = self.build_racebook_overview()

    def save_racebook(self):
        races = [race.to_dict(resolve_character_id=self._resolve_character_id) for race in self.list_races()]
        payload = {"format_version": 1, "races": races}
        self.store.save(payload)
        self.context.racebook_overview = self.build_racebook_overview()

    def list_races(self) -> list[Race]:
        races = list(self.context.all_races.values())
        return sorted(races, key=lambda race: (str(race.name or "").lower(), race.raceId))

    def get_race_by_id(self, race_id: str) -> Race | None:
        return self.context.all_races.get(str(race_id or "").strip())

    def get_race(self, identifier: str) -> Race | None:
        key = str(identifier or "").strip()
        if not key:
            return None

        by_id = self.get_race_by_id(key)
        if by_id is not None:
            return by_id

        matches = [race for race in self.list_races() if str(race.name or "").strip().lower() == key.lower()]
        if len(matches) == 1:
            return matches[0]
        return None

    def create_race_from_dict(self, data: dict):
        race = Race.from_dict(
            data,
            resolve_character=self._resolve_character,
            resolve_spell=self._resolve_spell,
        )

        if not race.raceId:
            race.raceId = self._generate_race_id(race.name)

        if race.raceId in self.context.all_races:
            raise ValueError(f"Race ID '{race.raceId}' already exists.")

        self.context.all_races[race.raceId] = race
        self.save_racebook()

    def edit_race_from_patch(self, race_identifier: str, patch: dict):
        existing = self.get_race(race_identifier)
        if existing is None:
            raise ValueError(f"Race '{race_identifier}' does not exist or is ambiguous.")

        merged = existing.to_dict(resolve_character_id=self._resolve_character_id)
        merged.update(patch or {})
        if not str(merged.get("name", "")).strip():
            merged["name"] = existing.name

        merged["raceId"] = existing.raceId

        updated = Race.from_dict(
            merged,
            resolve_character=self._resolve_character,
            resolve_spell=self._resolve_spell,
        )
        updated.raceId = existing.raceId

        self.context.all_races[updated.raceId] = updated
        self.save_racebook()

    def build_racebook_overview(self, max_lines: int = 20) -> str:
        races = self.list_races()
        if not races:
            return "No races in racebook yet."

        lines = []
        for race in races[:max_lines]:
            avg_name = "None"
            if race.averageSpecimine is not None:
                avg_name = str(getattr(race.averageSpecimine, "name", "") or "None")
            lines.append(f"- {race.name} [{race.raceId}] ({race.size.name}, avg: {avg_name})")

        if len(races) > max_lines:
            lines.append(f"... and {len(races) - max_lines} more")

        return "\n".join(lines)