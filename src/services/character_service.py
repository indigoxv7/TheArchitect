import re
from typing import Any

from src.domain.character_io import character_from_state, character_to_state
from src.persistence.character_store import CharacterStore
from src.services.game_context import GameContext


class CharacterService:
    def __init__(self, characters_directory: str, context: GameContext, item_service):
        self.context = context
        self.item_service = item_service
        self.store = CharacterStore(characters_directory)

    @staticmethod
    def _slugify_name(name: str) -> str:
        compact = re.sub(r"\s+", "", str(name or "").strip())
        compact = re.sub(r"[^A-Za-z0-9_\-]", "", compact)
        return compact or "Character"

    def _generate_character_id(self, name: str) -> str:
        prefix = self._slugify_name(name)
        index = len(self.context.all_characters)
        candidate = f"{prefix}{index}"
        while candidate in self.context.all_characters:
            index += 1
            candidate = f"{prefix}{index}"
        return candidate

    def _resolve_item(self, item_identifier: str):
        if not item_identifier:
            return None
        return self.item_service.get_item(item_identifier)

    def load_characters(self):
        self.context.all_characters.clear()
        self.store.ensure_directory()

        for character_id in self.store.list_character_ids():
            payload = self.store.load_character_file(character_id)
            if not isinstance(payload, dict):
                continue

            saved_id = str(payload.get("character_id", character_id)).strip() or character_id
            state = payload.get("character_state", payload)
            if not isinstance(state, dict):
                continue

            try:
                character = character_from_state(
                    state,
                    item_resolver=self._resolve_item,
                    error_item=self.context.error_item,
                )
            except Exception:
                continue

            self.context.all_characters[saved_id] = character

        self.context.characterbook_overview = self.build_characterbook_overview()

    def list_characters(self) -> list[tuple[str, object]]:
        return sorted(
            self.context.all_characters.items(),
            key=lambda pair: (str(getattr(pair[1], "name", "")).lower(), pair[0]),
        )

    def get_character(self, character_id: str):
        return self.context.all_characters.get(character_id)

    def save_character(self, character_id: str):
        character = self.get_character(character_id)
        if character is None:
            raise ValueError(f"Character '{character_id}' does not exist.")

        payload = {
            "format_version": 1,
            "character_id": character_id,
            "character_state": character_to_state(character),
        }
        self.store.save_character_file(character_id, payload)
        self.context.characterbook_overview = self.build_characterbook_overview()

    def save_all(self):
        for character_id in list(self.context.all_characters.keys()):
            self.save_character(character_id)

    def create_character_from_dict(self, payload: dict[str, Any]) -> tuple[str, object]:
        state = dict(payload or {})
        name = str(state.get("name", "")).strip()
        if not name:
            raise ValueError("Character name is required.")

        character_id = self._generate_character_id(name)
        character = character_from_state(
            state,
            item_resolver=self._resolve_item,
            error_item=self.context.error_item,
        )
        self.context.all_characters[character_id] = character
        self.save_character(character_id)
        return character_id, character

    def edit_character_from_patch(self, character_id: str, patch: dict[str, Any]):
        existing = self.get_character(character_id)
        if existing is None:
            raise ValueError(f"Character '{character_id}' does not exist.")

        merged = character_to_state(existing)
        merged.update(patch or {})
        if not str(merged.get("name", "")).strip():
            merged["name"] = existing.name

        updated = character_from_state(
            merged,
            item_resolver=self._resolve_item,
            error_item=self.context.error_item,
        )
        self.context.all_characters[character_id] = updated
        self.save_character(character_id)
        return updated

    def build_characterbook_overview(self, max_lines: int = 20) -> str:
        entries = self.list_characters()
        if not entries:
            return "No characters in characterbook yet."

        lines = []
        for character_id, character in entries[:max_lines]:
            name = getattr(character, "name", "")
            level = getattr(character, "level", 0)
            race_tier = getattr(character, "raceTier", "")
            lines.append(f"- {name} [{character_id}] (Lv {level}, {race_tier})")

        if len(entries) > max_lines:
            lines.append(f"... and {len(entries) - max_lines} more")

        return "\n".join(lines)
