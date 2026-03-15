import json
import os
from typing import Any


class EnvironmentbookStore:
    def __init__(self, environmentbook_path: str):
        self.environmentbook_path = environmentbook_path

    def _ensure_parent_directory(self):
        directory = os.path.dirname(self.environmentbook_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def load(self) -> dict[str, Any]:
        self._ensure_parent_directory()
        if not os.path.exists(self.environmentbook_path):
            self.save(
                {
                    "format_version": 1,
                    "effects": [],
                    "terrains": [],
                    "climates": [],
                    "biomes": [],
                }
            )

        with open(self.environmentbook_path, 'r', encoding='utf-8-sig') as file:
            payload = json.load(file)

        if isinstance(payload, dict):
            return payload

        return {
            "format_version": 1,
            "effects": [],
            "terrains": [],
            "climates": [],
            "biomes": [],
        }

    def save(self, payload: dict[str, Any]):
        self._ensure_parent_directory()
        with open(self.environmentbook_path, 'w', encoding='utf-8') as file:
            json.dump(payload, file, indent=4, ensure_ascii=False)
