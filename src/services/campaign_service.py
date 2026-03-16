import re

from src.domain.Campaign import Campaign, CampaignProgress
from src.persistence.campaignbook_store import CampaignbookStore
from src.services.game_context import GameContext


class CampaignService:
    def __init__(self, campaignbook_path: str, context: GameContext, mission_service):
        self.context = context
        self.mission_service = mission_service
        self.store = CampaignbookStore(campaignbook_path)

    @staticmethod
    def _slugify_name(name: str) -> str:
        compact = re.sub(r"\s+", "", str(name or "").strip())
        compact = re.sub(r"[^A-Za-z0-9_\-]", "", compact)
        return compact or "Campaign"

    def _generate_campaign_id(self, name: str) -> str:
        prefix = self._slugify_name(name)
        index = len(self.context.all_campaigns)
        candidate = f"{prefix}{index}"
        while candidate in self.context.all_campaigns:
            index += 1
            candidate = f"{prefix}{index}"
        return candidate

    @staticmethod
    def _generate_unlock_id(campaign: Campaign, index: int) -> str:
        prefix = re.sub(r"[^A-Za-z0-9_\-]", "", str(campaign.campaignId or campaign.name or "Campaign"))
        prefix = prefix or "Campaign"
        return f"{prefix}Unlock{index}"

    @staticmethod
    def get_campaign_label(campaign: Campaign) -> str:
        return f"{campaign.name} [{campaign.campaignId}]"

    @staticmethod
    def parse_campaign_id_from_label(label: str) -> str:
        text = str(label or "").strip()
        if text.endswith("]") and "[" in text:
            return text[text.rfind("[") + 1 : -1].strip()
        return text

    def _validate_campaign(self, campaign: Campaign):
        if not str(campaign.name or "").strip():
            raise ValueError("Campaign name is required.")

        known_mission_ids = {mission.missionId for mission in self.mission_service.list_missions()}

        for mission_id in campaign.startingMissionIds:
            if mission_id not in known_mission_ids:
                raise ValueError(f"Starting mission '{mission_id}' does not exist.")

        seen_unlock_ids: set[str] = set()
        for index, group in enumerate(campaign.unlockGroups):
            if not group.unlockId:
                group.unlockId = self._generate_unlock_id(campaign, index)
            elif group.unlockId in seen_unlock_ids:
                group.unlockId = self._generate_unlock_id(campaign, index)
            seen_unlock_ids.add(group.unlockId)

            if not group.missionIds:
                raise ValueError(f"Unlock group '{group.unlockId}' must unlock at least one mission.")

            for mission_id in group.missionIds:
                if mission_id not in known_mission_ids:
                    raise ValueError(f"Unlock group '{group.unlockId}' references missing mission '{mission_id}'.")
            for mission_id in group.requiredCompletedMissionIds:
                if mission_id not in known_mission_ids:
                    raise ValueError(f"Unlock group '{group.unlockId}' requires missing mission '{mission_id}'.")

    def load_campaignbook(self):
        payload = self.store.load()
        raw_campaigns = payload.get("campaigns", [])
        migrated = False

        self.context.all_campaigns.clear()
        for raw in raw_campaigns:
            try:
                campaign = Campaign.from_dict(raw)
                if not campaign.campaignId:
                    campaign.campaignId = self._generate_campaign_id(campaign.name)
                    migrated = True
                self._validate_campaign(campaign)
            except Exception:
                continue

            if campaign.campaignId in self.context.all_campaigns:
                campaign.campaignId = self._generate_campaign_id(campaign.name)
                self._validate_campaign(campaign)
                migrated = True

            self.context.all_campaigns[campaign.campaignId] = campaign

        if migrated:
            self.save_campaignbook()
        else:
            self.context.campaignbook_overview = self.build_campaignbook_overview()

    def save_campaignbook(self):
        payload = {
            "format_version": 1,
            "campaigns": [campaign.to_dict() for campaign in self.list_campaigns()],
        }
        self.store.save(payload)
        self.context.campaignbook_overview = self.build_campaignbook_overview()

    def list_campaigns(self) -> list[Campaign]:
        campaigns = list(self.context.all_campaigns.values())
        return sorted(campaigns, key=lambda campaign: (campaign.name.lower(), campaign.campaignId))

    def get_campaign_by_id(self, campaign_id: str) -> Campaign | None:
        return self.context.all_campaigns.get(str(campaign_id or "").strip())

    def get_campaign(self, identifier: str) -> Campaign | None:
        key = str(identifier or "").strip()
        if not key:
            return None

        by_id = self.get_campaign_by_id(key)
        if by_id is not None:
            return by_id

        matches = [campaign for campaign in self.list_campaigns() if campaign.name.strip().lower() == key.lower()]
        if len(matches) == 1:
            return matches[0]
        return None

    def create_campaign_from_dict(self, data: dict):
        campaign = Campaign.from_dict(data)
        if not campaign.campaignId:
            campaign.campaignId = self._generate_campaign_id(campaign.name)
        self._validate_campaign(campaign)
        if campaign.campaignId in self.context.all_campaigns:
            raise ValueError(f"Campaign ID '{campaign.campaignId}' already exists.")
        self.context.all_campaigns[campaign.campaignId] = campaign
        self.save_campaignbook()
        return campaign

    def edit_campaign_from_patch(self, campaign_identifier: str, patch: dict):
        existing = self.get_campaign(campaign_identifier)
        if existing is None:
            raise ValueError(f"Campaign '{campaign_identifier}' does not exist or is ambiguous.")

        merged = existing.to_dict()
        merged.update(patch or {})
        if not str(merged.get("name", "")).strip():
            merged["name"] = existing.name
        merged["campaignId"] = existing.campaignId

        updated = Campaign.from_dict(merged)
        updated.campaignId = existing.campaignId
        self._validate_campaign(updated)
        self.context.all_campaigns[updated.campaignId] = updated
        self.save_campaignbook()
        return updated

    @staticmethod
    def _player_highest_character_level(player) -> int:
        highest = 0
        for character in getattr(player, "characters", []) or []:
            try:
                highest = max(highest, int(getattr(character, "level", 0) or 0))
            except Exception:
                continue
        return highest

    @staticmethod
    def _coerce_progress(progress, campaign_id: str) -> CampaignProgress:
        if isinstance(progress, CampaignProgress):
            progress.EnsureRuntimeDefaults()
            progress.campaignId = campaign_id
            return progress
        if isinstance(progress, dict):
            coerced = CampaignProgress.from_dict(progress)
            coerced.campaignId = campaign_id
            return coerced
        return CampaignProgress(campaignId=campaign_id)

    def get_player_campaign_progress(self, player, campaign_id: str, create_if_missing: bool = True) -> CampaignProgress | None:
        campaign = self.get_campaign_by_id(campaign_id)
        if campaign is None:
            return None

        progress_map = getattr(player, "campaignProgressById", None)
        if not isinstance(progress_map, dict):
            progress_map = {}
            player.campaignProgressById = progress_map

        existing = progress_map.get(campaign_id)
        if existing is None and not create_if_missing:
            return None

        progress = self._coerce_progress(existing, campaign_id)
        progress_map[campaign_id] = progress
        return progress

    def refresh_player_campaign_progress(self, player, campaign_id: str | None = None, rebuild: bool = False) -> bool:
        changed = False
        campaign_ids = [campaign_id] if campaign_id else [campaign.campaignId for campaign in self.list_campaigns()]
        highest_level = self._player_highest_character_level(player)

        if not hasattr(player, "campaignProgressById") or not isinstance(player.campaignProgressById, dict):
            player.campaignProgressById = {}
            changed = True

        for current_campaign_id in campaign_ids:
            campaign = self.get_campaign_by_id(current_campaign_id)
            if campaign is None:
                continue

            progress = self.get_player_campaign_progress(player, current_campaign_id, create_if_missing=True)
            if progress is None:
                continue

            before_state = progress.to_dict()
            if rebuild:
                progress.unlockedMissionIds = []
                progress.appliedUnlockIds = []
            progress.campaignId = current_campaign_id
            progress.EnsureRuntimeDefaults()

            for mission_id in campaign.startingMissionIds:
                if mission_id not in progress.unlockedMissionIds:
                    progress.unlockedMissionIds.append(mission_id)
            for mission_id in progress.completedMissionIds:
                if mission_id not in progress.unlockedMissionIds:
                    progress.unlockedMissionIds.append(mission_id)

            completed_ids = set(progress.completedMissionIds)
            for group in campaign.unlockGroups:
                if group.is_satisfied(completed_ids, highest_level):
                    progress.unlock_missions(group.missionIds, unlock_id=group.unlockId)

            if progress.to_dict() != before_state:
                changed = True

        return changed

    def ensure_player_progress(self, player) -> bool:
        return self.refresh_player_campaign_progress(player, rebuild=False)

    def mark_mission_completed(self, player, campaign_id: str, mission_id: str) -> bool:
        progress = self.get_player_campaign_progress(player, campaign_id, create_if_missing=True)
        if progress is None:
            return False
        changed = progress.mark_mission_completed(mission_id)
        changed = self.refresh_player_campaign_progress(player, campaign_id=campaign_id, rebuild=False) or changed
        return changed

    def build_campaignbook_overview(self, max_lines: int = 20) -> str:
        campaigns = self.list_campaigns()
        if not campaigns:
            return "No campaigns in campaignbook yet."

        lines = []
        for campaign in campaigns[:max_lines]:
            lines.append(
                f"- {campaign.name} [{campaign.campaignId}] ({len(campaign.startingMissionIds)} starting, {len(campaign.unlockGroups)} unlock groups)"
            )

        if len(campaigns) > max_lines:
            lines.append(f"... and {len(campaigns) - max_lines} more")

        return "\n".join(lines)
