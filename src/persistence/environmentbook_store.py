import json
from pathlib import Path
from typing import Any


class EnvironmentbookStore:
    FILES = {
        "effects": "effects.json",
        "terrains": "terrains.json",
        "climates": "climates.json",
        "biomes": "biomes.json",
        "node_roles": "node_roles.json",
        "features": "features.json",
        "hooks": "hooks.json",
        "description_packs": "description_packs.json",
        "generation_profiles": "generation_profiles.json",
    }

    def __init__(self, environmentbook_path: str):
        raw_path = Path(environmentbook_path)
        if raw_path.suffix.lower() == ".json":
            if raw_path.parent.name.lower() == "environment":
                self.base_directory = raw_path.parent.parent / "LocationContent"
            else:
                self.base_directory = raw_path.parent / "LocationContent"
        else:
            self.base_directory = raw_path

    def _ensure_directory(self):
        self.base_directory.mkdir(parents=True, exist_ok=True)

    def _file_path(self, key: str) -> Path:
        return self.base_directory / self.FILES[key]

    def load(self) -> dict[str, Any]:
        self._ensure_directory()
        payload = {"format_version": 2}
        for key, filename in self.FILES.items():
            file_path = self.base_directory / filename
            if not file_path.exists():
                payload[key] = []
                continue
            try:
                with file_path.open("r", encoding="utf-8-sig") as file:
                    raw = json.load(file)
            except Exception:
                payload[key] = []
                continue
            payload[key] = raw if isinstance(raw, list) else []
        return payload

    def save(self, payload: dict[str, Any]):
        self._ensure_directory()
        for key, filename in self.FILES.items():
            file_path = self.base_directory / filename
            with file_path.open("w", encoding="utf-8") as file:
                json.dump(list(payload.get(key, []) or []), file, indent=4, ensure_ascii=False)
