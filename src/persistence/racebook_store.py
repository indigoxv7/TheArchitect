import json
import os
from typing import Any


class RacebookStore:
    def __init__(self, racebook_path: str):
        self.racebook_path = racebook_path

    def _ensure_parent_directory(self):
        directory = os.path.dirname(self.racebook_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def load(self) -> dict[str, Any]:
        self._ensure_parent_directory()
        if not os.path.exists(self.racebook_path):
            self.save({"format_version": 1, "races": []})

        with open(self.racebook_path, "r", encoding="utf-8-sig") as f:
            payload = json.load(f)

        if isinstance(payload, dict):
            return payload

        return {"format_version": 1, "races": []}

    def save(self, payload: dict[str, Any]):
        self._ensure_parent_directory()
        with open(self.racebook_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)