import json
import os
from typing import Any


class CampaignbookStore:
    def __init__(self, campaignbook_path: str):
        self.campaignbook_path = campaignbook_path

    def _ensure_parent_directory(self):
        directory = os.path.dirname(self.campaignbook_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def load(self) -> dict[str, Any]:
        self._ensure_parent_directory()
        if not os.path.exists(self.campaignbook_path):
            self.save({"format_version": 1, "campaigns": []})

        with open(self.campaignbook_path, "r", encoding="utf-8-sig") as file:
            payload = json.load(file)

        if isinstance(payload, dict):
            return payload

        return {"format_version": 1, "campaigns": []}

    def save(self, payload: dict[str, Any]):
        self._ensure_parent_directory()
        with open(self.campaignbook_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=4, ensure_ascii=False)
