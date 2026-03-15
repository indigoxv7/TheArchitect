import json
import os
from pathlib import Path
from typing import Any


class ActiveBattleStore:
    def __init__(self, battles_directory: str):
        self.battles_directory = battles_directory

    def ensure_directory(self):
        os.makedirs(self.battles_directory, exist_ok=True)

    def _battle_path(self, player_id: int) -> str:
        return os.path.join(self.battles_directory, f"{int(player_id)}.json")

    def list_player_ids(self) -> list[int]:
        self.ensure_directory()
        result: list[int] = []
        for path in sorted(Path(self.battles_directory).glob("*.json")):
            try:
                result.append(int(path.stem))
            except ValueError:
                continue
        return result

    def load_battle_file(self, player_id: int) -> dict[str, Any] | None:
        path = self._battle_path(player_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8-sig") as file:
            payload = json.load(file)
        if not isinstance(payload, dict):
            return None
        return payload

    def save_battle_file(self, player_id: int, payload: dict[str, Any]):
        self.ensure_directory()
        path = self._battle_path(player_id)
        with open(path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=4, ensure_ascii=False)

    def delete_battle_file(self, player_id: int):
        path = self._battle_path(player_id)
        if os.path.exists(path):
            os.remove(path)
