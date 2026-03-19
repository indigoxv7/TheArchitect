import re

from src.domain.mission import DeliveryObjective, EscortObjective, MissionTemplate
from src.persistence.missionbook_store import MissionbookStore
from src.services.game_context import GameContext


class MissionService:
    def __init__(self, missionbook_path: str, context: GameContext, allegiance_service, unit_service):
        self.context = context
        self.allegiance_service = allegiance_service
        self.unit_service = unit_service
        self.store = MissionbookStore(missionbook_path)

    @staticmethod
    def _slugify_name(name: str) -> str:
        compact = re.sub(r"\s+", "", str(name or "").strip())
        compact = re.sub(r"[^A-Za-z0-9_\-]", "", compact)
        return compact or "Mission"

    def _generate_mission_id(self, name: str) -> str:
        prefix = self._slugify_name(name)
        index = len(self.context.all_missions)
        candidate = f"{prefix}{index}"
        while candidate in self.context.all_missions:
            index += 1
            candidate = f"{prefix}{index}"
        return candidate

    @staticmethod
    def get_mission_label(mission: MissionTemplate) -> str:
        return f"{mission.name} [{mission.missionId}]"

    @staticmethod
    def parse_mission_id_from_label(label: str) -> str:
        text = str(label or "").strip()
        if text.endswith("]") and "[" in text:
            return text[text.rfind("[") + 1 : -1].strip()
        return text

    def _validate_mission(self, mission: MissionTemplate):
        if not getattr(mission, "objective", None):
            raise ValueError("Mission must include an objective.")

        if isinstance(mission.objective, DeliveryObjective):
            if not mission.objective.requiredItemId:
                raise ValueError("Delivery missions must specify an item to deliver.")
            if self.allegiance_service.get_allegiance_by_id(mission.objective.targetAllegianceId) is None:
                raise ValueError(f"Delivery target allegiance '{mission.objective.targetAllegianceId}' does not exist.")
            if self.context.all_items.get(mission.objective.requiredItemId) is None:
                raise ValueError(f"Delivery item '{mission.objective.requiredItemId}' does not exist.")
        if isinstance(mission.objective, EscortObjective):
            escort_unit_id = str(mission.objective.escortUnitId or "").strip()
            if not escort_unit_id:
                raise ValueError("Escort missions must specify a unit to escort.")
            if self.unit_service.get_unit_by_id(escort_unit_id) is None:
                raise ValueError(f"Escort unit '{escort_unit_id}' does not exist.")

        seen_allegiances: set[str] = set()
        for config in mission.allegianceConfigs:
            allegiance_id = str(config.allegianceId or "").strip()
            if not allegiance_id:
                raise ValueError("Each mission allegiance entry must include an allegiance.")
            if allegiance_id in seen_allegiances:
                raise ValueError(f"Mission already includes allegiance '{allegiance_id}'.")
            if self.allegiance_service.get_allegiance_by_id(allegiance_id) is None:
                raise ValueError(f"Allegiance '{allegiance_id}' does not exist.")
            seen_allegiances.add(allegiance_id)

            seen_units: set[str] = set()
            for option in config.unitOptions:
                unit_id = str(option.unitId or "").strip()
                if not unit_id:
                    raise ValueError(f"Mission allegiance '{allegiance_id}' includes a unit option with no unit.")
                if unit_id in seen_units:
                    raise ValueError(f"Mission allegiance '{allegiance_id}' includes duplicate unit '{unit_id}'.")
                if self.unit_service.get_unit_by_id(unit_id) is None:
                    raise ValueError(f"Unit '{unit_id}' does not exist.")
                if (
                    option.capacityMin is not None
                    and option.capacityMax is not None
                    and option.capacityMin > option.capacityMax
                ):
                    raise ValueError(f"Unit '{unit_id}' has capacity min greater than max.")
                seen_units.add(unit_id)

    def load_missionbook(self):
        payload = self.store.load()
        raw_missions = payload.get("missions", [])
        migrated = False

        self.context.all_missions.clear()
        for raw in raw_missions:
            try:
                mission = MissionTemplate.from_dict(raw)
                self._validate_mission(mission)
            except Exception:
                continue

            if not mission.missionId:
                mission.missionId = self._generate_mission_id(mission.name)
                migrated = True
            if mission.missionId in self.context.all_missions:
                mission.missionId = self._generate_mission_id(mission.name)
                migrated = True

            self.context.all_missions[mission.missionId] = mission

        if migrated:
            self.save_missionbook()
        else:
            self.context.missionbook_overview = self.build_missionbook_overview()

    def save_missionbook(self):
        payload = {
            "format_version": 2,
            "missions": [mission.to_dict() for mission in self.list_missions()],
        }
        self.store.save(payload)
        self.context.missionbook_overview = self.build_missionbook_overview()

    def list_missions(self) -> list[MissionTemplate]:
        missions = list(self.context.all_missions.values())
        return sorted(missions, key=lambda mission: (mission.name.lower(), mission.missionId))

    def get_mission_by_id(self, mission_id: str) -> MissionTemplate | None:
        return self.context.all_missions.get(str(mission_id or "").strip())

    def get_mission(self, identifier: str) -> MissionTemplate | None:
        key = str(identifier or "").strip()
        if not key:
            return None

        by_id = self.get_mission_by_id(key)
        if by_id is not None:
            return by_id

        matches = [mission for mission in self.list_missions() if mission.name.strip().lower() == key.lower()]
        if len(matches) == 1:
            return matches[0]
        return None

    def create_mission_from_dict(self, data: dict):
        mission = MissionTemplate.from_dict(data)
        self._validate_mission(mission)
        if not mission.missionId:
            mission.missionId = self._generate_mission_id(mission.name)
        if mission.missionId in self.context.all_missions:
            raise ValueError(f"Mission ID '{mission.missionId}' already exists.")
        self.context.all_missions[mission.missionId] = mission
        self.save_missionbook()
        return mission

    def edit_mission_from_patch(self, mission_identifier: str, patch: dict):
        existing = self.get_mission(mission_identifier)
        if existing is None:
            raise ValueError(f"Mission '{mission_identifier}' does not exist or is ambiguous.")

        merged = existing.to_dict()
        merged.update(patch or {})
        if not str(merged.get("name", "")).strip():
            merged["name"] = existing.name
        merged["missionId"] = existing.missionId

        updated = MissionTemplate.from_dict(merged)
        updated.missionId = existing.missionId
        self._validate_mission(updated)
        self.context.all_missions[updated.missionId] = updated
        self.save_missionbook()
        return updated

    def build_missionbook_overview(self, max_lines: int = 20) -> str:
        missions = self.list_missions()
        if not missions:
            return "No missions in missionbook yet."

        lines = []
        for mission in missions[:max_lines]:
            objective_name = getattr(getattr(mission, "objective", None), "objectiveType", None)
            objective_text = getattr(objective_name, "value", "No Objective")
            lines.append(
                f"- {mission.name} [{mission.missionId}] ({objective_text}, {len(mission.allegianceConfigs)} allegiances)"
            )

        if len(missions) > max_lines:
            lines.append(f"... and {len(missions) - max_lines} more")

        return "\n".join(lines)
