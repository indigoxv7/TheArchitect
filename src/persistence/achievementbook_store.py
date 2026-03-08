import json
import os
from typing import Any


class AchievementbookStore:
    def __init__(self, achievementbook_path: str):
        self.achievementbook_path = achievementbook_path

    def _ensure_parent_directory(self):
        directory = os.path.dirname(self.achievementbook_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def load(self) -> dict[str, Any]:
        self._ensure_parent_directory()
        if not os.path.exists(self.achievementbook_path):
            self.save({"format_version": 1, "achievements": []})

        with open(self.achievementbook_path, "r", encoding="utf-8-sig") as file:
            payload = json.load(file)

        if isinstance(payload, dict):
            return payload

        return {"format_version": 1, "achievements": []}

    def save(self, payload: dict[str, Any]):
        self._ensure_parent_directory()
        with open(self.achievementbook_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=4, ensure_ascii=False)
