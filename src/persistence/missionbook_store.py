import json
import os
from typing import Any


class MissionbookStore:
    def __init__(self, missionbook_path: str):
        self.missionbook_path = missionbook_path

    def _ensure_parent_directory(self):
        directory = os.path.dirname(self.missionbook_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def load(self) -> dict[str, Any]:
        self._ensure_parent_directory()
        if not os.path.exists(self.missionbook_path):
            self.save({"format_version": 1, "missions": []})

        with open(self.missionbook_path, "r", encoding="utf-8-sig") as file:
            payload = json.load(file)

        if isinstance(payload, dict):
            return payload

        return {"format_version": 1, "missions": []}

    def save(self, payload: dict[str, Any]):
        self._ensure_parent_directory()
        with open(self.missionbook_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=4, ensure_ascii=False)
