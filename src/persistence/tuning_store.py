import json
import os
from typing import Any


class TuningStore:
    def __init__(self, file_path: str):
        self.file_path = str(file_path or "")

    def _ensure_parent_directory(self):
        directory = os.path.dirname(self.file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def load(self) -> dict[str, Any]:
        self._ensure_parent_directory()
        if not os.path.exists(self.file_path):
            return {}
        with open(self.file_path, "r", encoding="utf-8-sig") as file:
            payload = json.load(file)
        return payload if isinstance(payload, dict) else {}

    def save(self, payload: dict[str, Any]):
        self._ensure_parent_directory()
        with open(self.file_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=4, ensure_ascii=False)

