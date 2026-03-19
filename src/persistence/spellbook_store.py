import json
import os
from typing import Any


class SpellbookStore:
    def __init__(self, spellbook_path: str):
        self.spellbook_path = spellbook_path

    def _ensure_parent_directory(self):
        directory = os.path.dirname(self.spellbook_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def load(self) -> dict[str, Any]:
        self._ensure_parent_directory()
        if not os.path.exists(self.spellbook_path):
            self.save({"format_version": 1, "spells": []})

        with open(self.spellbook_path, "r", encoding="utf-8-sig") as f:
            payload = json.load(f)

        if isinstance(payload, dict):
            return payload

        return {"format_version": 1, "spells": []}

    def save(self, payload: dict[str, Any]):
        self._ensure_parent_directory()
        with open(self.spellbook_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)
