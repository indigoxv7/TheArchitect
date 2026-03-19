import json
import os
from pathlib import Path


class ExistingPlayersRosterStore:
    def __init__(self, roster_path: str, player_save_directory: str):
        self.roster_path = roster_path
        self.player_save_directory = player_save_directory

    def ensure_save_directory(self):
        os.makedirs(self.player_save_directory, exist_ok=True)

    def load_roster(self) -> dict[int, bool]:
        with open(self.roster_path, "r", encoding="utf-8-sig") as file:
            keys = json.load(file)
        return {int(key): False for key in keys}

    def save_roster(self, existing_players: dict[int, bool]):
        with open(self.roster_path, "w", encoding="utf-8") as file:
            json.dump(list(existing_players.keys()), file)

    def discover_save_ids(self) -> set[int]:
        self.ensure_save_directory()
        ids: set[int] = set()
        for save_path in Path(self.player_save_directory).glob("*.json"):
            try:
                ids.add(int(save_path.stem))
            except ValueError:
                continue
        return ids

    def roster_exists(self) -> bool:
        return os.path.exists(self.roster_path)
