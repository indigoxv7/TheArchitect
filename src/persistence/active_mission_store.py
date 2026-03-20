import json
import os
from pathlib import Path
from typing import Any


class ActiveMissionStore:
    def __init__(self, missions_directory: str):
        self.missions_directory = missions_directory

    def ensure_directory(self):
        os.makedirs(self.missions_directory, exist_ok=True)

    def _mission_path(self, player_id: int) -> str:
        return os.path.join(self.missions_directory, f"{int(player_id)}.json")

    def list_player_ids(self) -> list[int]:
        self.ensure_directory()
        result: list[int] = []
        for path in sorted(Path(self.missions_directory).glob("*.json")):
            try:
                result.append(int(path.stem))
            except ValueError:
                continue
        return result

    def load_mission_file(self, player_id: int) -> dict[str, Any] | None:
        path = self._mission_path(player_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8-sig") as file:
            payload = json.load(file)
        return payload if isinstance(payload, dict) else None

    def save_mission_file(self, player_id: int, payload: dict[str, Any]):
        self.ensure_directory()
        path = self._mission_path(player_id)
        with open(path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=4, ensure_ascii=False)

    def delete_mission_file(self, player_id: int):
        path = self._mission_path(player_id)
        if os.path.exists(path):
            os.remove(path)
