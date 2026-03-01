import json
import os


class WhitelistStore:
    def __init__(self, whitelist_path: str, default_admin_id: int = 191980469670248448):
        self.whitelist_path = whitelist_path
        self.default_admin_id = int(default_admin_id)

    def ensure_exists(self):
        if os.path.exists(self.whitelist_path):
            return
        with open(self.whitelist_path, "w", encoding="utf-8") as file:
            json.dump([self.default_admin_id], file, indent=4)

    def load_ids(self) -> list[int]:
        self.ensure_exists()
        with open(self.whitelist_path, "r", encoding="utf-8-sig") as file:
            raw_list = json.load(file)

        admin_ids: list[int] = []
        for value in raw_list:
            try:
                admin_ids.append(int(value))
            except (TypeError, ValueError):
                continue

        return admin_ids
