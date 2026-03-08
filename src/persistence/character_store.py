import json
import os
from pathlib import Path
from typing import Any


class CharacterStore:
    def __init__(self, characters_directory: str):
        self.characters_directory = characters_directory

    def ensure_directory(self):
        os.makedirs(self.characters_directory, exist_ok=True)

    def _character_path(self, character_id: str) -> str:
        safe_id = str(character_id).strip()
        return os.path.join(self.characters_directory, f"{safe_id}.json")

    def list_character_ids(self) -> list[str]:
        self.ensure_directory()
        ids: list[str] = []
        for path in sorted(Path(self.characters_directory).glob("*.json")):
            ids.append(path.stem)
        return ids

    def load_character_file(self, character_id: str) -> dict[str, Any] | None:
        path = self._character_path(character_id)
        if not os.path.exists(path):
            return None

        with open(path, "r", encoding="utf-8-sig") as file:
            payload = json.load(file)

        if not isinstance(payload, dict):
            return None
        return payload

    def save_character_file(self, character_id: str, payload: dict[str, Any]):
        self.ensure_directory()
        path = self._character_path(character_id)
        with open(path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=4, ensure_ascii=False)

    def delete_character_file(self, character_id: str):
        path = self._character_path(character_id)
        if os.path.exists(path):
            os.remove(path)
