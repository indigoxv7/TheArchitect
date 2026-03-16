from __future__ import annotations

from typing import Any


class CampaignUnlockGroup:
    def __init__(
        self,
        missionIds: list[str] | None = None,
        requiredCompletedMissionIds: list[str] | None = None,
        minimumCharacterLevel: int | None = None,
        unlockId: str = "",
    ):
        self.unlockId = str(unlockId or "").strip()
        self.missionIds = self._normalize_id_list(missionIds)
        self.requiredCompletedMissionIds = self._normalize_id_list(requiredCompletedMissionIds)
        self.minimumCharacterLevel = self._normalize_optional_int(minimumCharacterLevel)

    @staticmethod
    def _normalize_id_list(values: Any) -> list[str]:
        if not isinstance(values, list):
            return []
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            text = str(value or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
        return result

    @staticmethod
    def _normalize_optional_int(value: Any) -> int | None:
        if value in (None, ""):
            return None
        try:
            numeric = int(value)
        except Exception:
            return None
        return max(0, numeric)

    def is_satisfied(self, completed_mission_ids: set[str], highest_character_level: int) -> bool:
        if self.minimumCharacterLevel is not None and highest_character_level < self.minimumCharacterLevel:
            return False
        if not set(self.requiredCompletedMissionIds).issubset(completed_mission_ids):
            return False
        return True

    def describe(self) -> str:
        conditions: list[str] = []
        if self.minimumCharacterLevel is not None:
            conditions.append(f"Any character level >= {self.minimumCharacterLevel}")
        if self.requiredCompletedMissionIds:
            conditions.append("Complete: " + ", ".join(self.requiredCompletedMissionIds))
        if not conditions:
            conditions.append("No conditions")
        unlocked = ", ".join(self.missionIds) if self.missionIds else "<No missions>"
        return f"{' | '.join(conditions)} -> {unlocked}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "unlockId": self.unlockId,
            "missionIds": list(self.missionIds),
            "requiredCompletedMissionIds": list(self.requiredCompletedMissionIds),
            "minimumCharacterLevel": self.minimumCharacterLevel,
        }

    @classmethod
    def from_dict(cls, data: Any) -> "CampaignUnlockGroup":
        if not isinstance(data, dict):
            raise ValueError("Campaign unlock group data must be a dictionary.")
        return cls(
            missionIds=data.get("missionIds", []),
            requiredCompletedMissionIds=data.get("requiredCompletedMissionIds", []),
            minimumCharacterLevel=data.get("minimumCharacterLevel"),
            unlockId=str(data.get("unlockId", "") or ""),
        )


class Campaign:
    def __init__(
        self,
        name: str,
        description: str = "",
        startingMissionIds: list[str] | None = None,
        unlockGroups: list[CampaignUnlockGroup] | None = None,
        campaignId: str = "",
    ):
        self.campaignId = str(campaignId or "").strip()
        self.name = str(name or "").strip()
        self.description = str(description or "")
        self.startingMissionIds = CampaignUnlockGroup._normalize_id_list(startingMissionIds)
        self.unlockGroups = [
            group if isinstance(group, CampaignUnlockGroup) else CampaignUnlockGroup.from_dict(group)
            for group in (unlockGroups or [])
            if group is not None
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaignId": self.campaignId,
            "name": self.name,
            "description": self.description,
            "startingMissionIds": list(self.startingMissionIds),
            "unlockGroups": [group.to_dict() for group in self.unlockGroups],
        }

    @classmethod
    def from_dict(cls, data: Any) -> "Campaign":
        if not isinstance(data, dict):
            raise ValueError("Campaign data must be a dictionary.")

        name = str(data.get("name", "") or "").strip()
        if not name:
            raise ValueError("Campaign data must include a non-empty name.")

        unlock_groups = data.get("unlockGroups", [])
        if not isinstance(unlock_groups, list):
            unlock_groups = []

        return cls(
            name=name,
            description=str(data.get("description", "") or ""),
            startingMissionIds=data.get("startingMissionIds", []),
            unlockGroups=[CampaignUnlockGroup.from_dict(entry) for entry in unlock_groups if isinstance(entry, dict)],
            campaignId=str(data.get("campaignId", "") or ""),
        )


class CampaignProgress:
    def __init__(
        self,
        campaignId: str = "",
        unlockedMissionIds: list[str] | None = None,
        completedMissionIds: list[str] | None = None,
        appliedUnlockIds: list[str] | None = None,
    ):
        self.campaignId = str(campaignId or "").strip()
        self.unlockedMissionIds = CampaignUnlockGroup._normalize_id_list(unlockedMissionIds)
        self.completedMissionIds = CampaignUnlockGroup._normalize_id_list(completedMissionIds)
        self.appliedUnlockIds = CampaignUnlockGroup._normalize_id_list(appliedUnlockIds)
        self.EnsureRuntimeDefaults()

    def EnsureRuntimeDefaults(self):
        self.campaignId = str(getattr(self, "campaignId", "") or "").strip()
        self.unlockedMissionIds = CampaignUnlockGroup._normalize_id_list(getattr(self, "unlockedMissionIds", []))
        self.completedMissionIds = CampaignUnlockGroup._normalize_id_list(getattr(self, "completedMissionIds", []))
        self.appliedUnlockIds = CampaignUnlockGroup._normalize_id_list(getattr(self, "appliedUnlockIds", []))
        for mission_id in self.completedMissionIds:
            if mission_id not in self.unlockedMissionIds:
                self.unlockedMissionIds.append(mission_id)

    def unlock_missions(self, mission_ids: list[str], unlock_id: str = "") -> bool:
        changed = False
        for mission_id in CampaignUnlockGroup._normalize_id_list(mission_ids):
            if mission_id not in self.unlockedMissionIds:
                self.unlockedMissionIds.append(mission_id)
                changed = True
        text = str(unlock_id or "").strip()
        if text and text not in self.appliedUnlockIds:
            self.appliedUnlockIds.append(text)
            changed = True
        return changed

    def mark_mission_completed(self, mission_id: str) -> bool:
        text = str(mission_id or "").strip()
        if not text:
            return False
        changed = False
        if text not in self.completedMissionIds:
            self.completedMissionIds.append(text)
            changed = True
        if text not in self.unlockedMissionIds:
            self.unlockedMissionIds.append(text)
            changed = True
        return changed

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaignId": self.campaignId,
            "unlockedMissionIds": list(self.unlockedMissionIds),
            "completedMissionIds": list(self.completedMissionIds),
            "appliedUnlockIds": list(self.appliedUnlockIds),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "CampaignProgress":
        if not isinstance(data, dict):
            return cls()
        return cls(
            campaignId=str(data.get("campaignId", "") or ""),
            unlockedMissionIds=data.get("unlockedMissionIds", []),
            completedMissionIds=data.get("completedMissionIds", []),
            appliedUnlockIds=data.get("appliedUnlockIds", []),
        )
