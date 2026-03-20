import re

from src.domain.Allegiance import Allegiance, AllegianceRelationship
from src.persistence.allegiancebook_store import AllegiancebookStore
from src.services.game_context import GameContext


class AllegianceService:
    def __init__(self, allegiancebook_path: str, context: GameContext):
        self.context = context
        self.store = AllegiancebookStore(allegiancebook_path)

    @staticmethod
    def _slugify_name(name: str) -> str:
        compact = re.sub(r"\s+", "", str(name or "").strip())
        compact = re.sub(r"[^A-Za-z0-9_\-]", "", compact)
        return compact or "Allegiance"

    def _generate_allegiance_id(self, name: str) -> str:
        prefix = self._slugify_name(name)
        index = len(self.context.all_allegiances)
        candidate = f"{prefix}{index}"
        while candidate in self.context.all_allegiances:
            index += 1
            candidate = f"{prefix}{index}"
        return candidate

    @staticmethod
    def get_allegiance_label(allegiance: Allegiance) -> str:
        return f"{allegiance.name} [{allegiance.allegianceId}]"

    @staticmethod
    def parse_allegiance_id_from_label(label: str) -> str:
        text = str(label or "").strip()
        if text.endswith("]") and "[" in text:
            return text[text.rfind("[") + 1 : -1].strip()
        return text

    def load_allegiancebook(self):
        payload = self.store.load()
        raw_allegiances = payload.get("allegiances", [])
        migrated = False

        self.context.all_allegiances.clear()
        for raw in raw_allegiances:
            try:
                allegiance = Allegiance.from_dict(raw)
            except Exception:
                continue

            if not allegiance.allegianceId:
                allegiance.allegianceId = self._generate_allegiance_id(allegiance.name)
                migrated = True
            if allegiance.allegianceId in self.context.all_allegiances:
                allegiance.allegianceId = self._generate_allegiance_id(allegiance.name)
                migrated = True

            self.context.all_allegiances[allegiance.allegianceId] = allegiance

        if migrated:
            self.save_allegiancebook()
        else:
            self.context.allegiancebook_overview = self.build_allegiancebook_overview()

    def save_allegiancebook(self):
        payload = {
            "format_version": 1,
            "allegiances": [allegiance.to_dict() for allegiance in self.list_allegiances()],
        }
        self.store.save(payload)
        self.context.allegiancebook_overview = self.build_allegiancebook_overview()

    def list_allegiances(self) -> list[Allegiance]:
        allegiances = list(self.context.all_allegiances.values())
        return sorted(allegiances, key=lambda allegiance: (allegiance.name.lower(), allegiance.allegianceId))

    def get_allegiance_by_id(self, allegiance_id: str) -> Allegiance | None:
        return self.context.all_allegiances.get(str(allegiance_id or "").strip())

    def get_allegiance(self, identifier: str) -> Allegiance | None:
        key = str(identifier or "").strip()
        if not key:
            return None

        by_id = self.get_allegiance_by_id(key)
        if by_id is not None:
            return by_id

        matches = [
            allegiance for allegiance in self.list_allegiances() if allegiance.name.strip().lower() == key.lower()
        ]
        if len(matches) == 1:
            return matches[0]
        return None

    def create_allegiance_from_dict(self, data: dict):
        allegiance = Allegiance.from_dict(data)
        if not allegiance.allegianceId:
            allegiance.allegianceId = self._generate_allegiance_id(allegiance.name)
        if allegiance.allegianceId in self.context.all_allegiances:
            raise ValueError(f"Allegiance ID '{allegiance.allegianceId}' already exists.")
        self.context.all_allegiances[allegiance.allegianceId] = allegiance
        self.save_allegiancebook()
        return allegiance

    def edit_allegiance_from_patch(self, allegiance_identifier: str, patch: dict):
        existing = self.get_allegiance(allegiance_identifier)
        if existing is None:
            raise ValueError(f"Allegiance '{allegiance_identifier}' does not exist or is ambiguous.")

        merged = existing.to_dict()
        merged.update(patch or {})
        if not str(merged.get("name", "")).strip():
            merged["name"] = existing.name
        merged["allegianceId"] = existing.allegianceId

        updated = Allegiance.from_dict(merged)
        updated.allegianceId = existing.allegianceId
        self.context.all_allegiances[updated.allegianceId] = updated
        self.save_allegiancebook()
        return updated

    def get_relationship(self, allegiance_id: str, other_allegiance_id: str) -> AllegianceRelationship:
        allegiance = self.get_allegiance(allegiance_id)
        if allegiance is None:
            return AllegianceRelationship.NEUTRAL
        return allegiance.get_relationship_to(other_allegiance_id)

    def build_allegiancebook_overview(self, max_lines: int = 20) -> str:
        allegiances = self.list_allegiances()
        if not allegiances:
            return "No allegiances in allegiancebook yet."

        lines = []
        for allegiance in allegiances[:max_lines]:
            policy = allegiance.defaultPolicy.value
            relationship_count = len(allegiance.relationships)
            lines.append(f"- {allegiance.name} [{allegiance.allegianceId}] ({policy}, {relationship_count} overrides)")

        if len(allegiances) > max_lines:
            lines.append(f"... and {len(allegiances) - max_lines} more")

        return "\n".join(lines)
