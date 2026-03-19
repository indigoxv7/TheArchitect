import re

from src.domain.race import Race
from src.domain.unit import Unit
from src.persistence.unitbook_store import UnitbookStore
from src.services.game_context import GameContext


class UnitService:
    def __init__(
        self, unitbook_path: str, context: GameContext, race_service, character_service, spell_service, item_service
    ):
        self.context = context
        self.race_service = race_service
        self.character_service = character_service
        self.spell_service = spell_service
        self.item_service = item_service
        self.store = UnitbookStore(unitbook_path)

    @staticmethod
    def _slugify_name(name: str) -> str:
        compact = re.sub(r"\s+", "", str(name or "").strip())
        compact = re.sub(r"[^A-Za-z0-9_\-]", "", compact)
        return compact or "Unit"

    def _generate_unit_id(self, name: str) -> str:
        prefix = self._slugify_name(name)
        index = len(self.context.all_units)
        candidate = f"{prefix}{index}"
        while candidate in self.context.all_units:
            index += 1
            candidate = f"{prefix}{index}"
        return candidate

    def _resolve_character(self, character_identifier: str):
        key = str(character_identifier or "").strip()
        if not key:
            return None
        return self.character_service.get_character(key)

    def _resolve_spell(self, spell_identifier: str):
        key = str(spell_identifier or "").strip()
        if not key:
            return None
        return self.spell_service.get_spell(key)

    def _resolve_item(self, item_identifier: str):
        key = str(item_identifier or "").strip()
        if not key:
            return None
        return self.item_service.get_item(key)

    def _resolve_character_id(self, character_obj) -> str | None:
        if character_obj is None:
            return None
        for character_id, character in self.character_service.list_characters():
            if character is character_obj:
                return character_id
        target_name = str(getattr(character_obj, "name", "") or "").strip().lower()
        if not target_name:
            return None
        matches = []
        for character_id, character in self.character_service.list_characters():
            if str(getattr(character, "name", "") or "").strip().lower() == target_name:
                matches.append(character_id)
        if len(matches) == 1:
            return matches[0]
        return None

    @staticmethod
    def _resolve_item_id(item_obj) -> str | None:
        if item_obj is None:
            return None
        item_id = str(getattr(item_obj, "itemId", "") or "").strip()
        return item_id or None

    def resolve_base_race(self, unit_or_identifier) -> Race | None:
        unit = unit_or_identifier if isinstance(unit_or_identifier, Unit) else self.get_unit(unit_or_identifier)
        if unit is None:
            return None
        return self.race_service.get_race_by_id(unit.baseRaceId)

    def resolve_effective_race(self, unit_or_identifier) -> Race | None:
        unit = unit_or_identifier if isinstance(unit_or_identifier, Unit) else self.get_unit(unit_or_identifier)
        if unit is None:
            return None
        base_race = self.resolve_base_race(unit)
        if base_race is None:
            return None
        return unit.to_effective_race(base_race)

    def get_effective_name(self, unit_or_identifier) -> str:
        effective = self.resolve_effective_race(unit_or_identifier)
        if effective is None:
            return "<Unknown Unit>"
        return str(getattr(effective, "name", "") or "<Unnamed Unit>")

    def get_unit_label(self, unit: Unit) -> str:
        base_race = self.resolve_base_race(unit)
        base_name = str(getattr(base_race, "name", "Unknown Race") or "Unknown Race")
        return f"{self.get_effective_name(unit)} [{unit.unitId}] ({base_name})"

    @staticmethod
    def parse_unit_id_from_label(label: str) -> str:
        text = str(label or "").strip()
        matches = re.findall(r"\[([^\[\]]+)\]", text)
        if matches:
            return matches[-1].strip()
        return text

    def load_unitbook(self):
        payload = self.store.load()
        raw_units = payload.get("units", [])
        migrated = False

        self.context.all_units.clear()

        for unit_data in raw_units:
            try:
                unit = Unit.from_dict(
                    unit_data,
                    resolve_character=self._resolve_character,
                    resolve_spell=self._resolve_spell,
                    resolve_item=self._resolve_item,
                )
            except Exception:
                continue

            if not unit.unitId:
                unit.unitId = self._generate_unit_id(unit.name or unit.baseRaceId)
                migrated = True

            if unit.unitId in self.context.all_units:
                unit.unitId = self._generate_unit_id(unit.name or unit.baseRaceId)
                migrated = True

            if self.race_service.get_race_by_id(unit.baseRaceId) is None:
                continue

            self.context.all_units[unit.unitId] = unit

        if migrated:
            self.save_unitbook()
        else:
            self.context.unitbook_overview = self.build_unitbook_overview()

    def save_unitbook(self):
        payload = {
            "format_version": 1,
            "units": [
                unit.to_dict(
                    resolve_character_id=self._resolve_character_id,
                    resolve_item_id=self._resolve_item_id,
                )
                for unit in self.list_units()
            ],
        }
        self.store.save(payload)
        self.context.unitbook_overview = self.build_unitbook_overview()

    def list_units(self, race_id: str | None = None) -> list[Unit]:
        units = list(self.context.all_units.values())
        if race_id:
            target = str(race_id or "").strip()
            units = [unit for unit in units if unit.baseRaceId == target]
        return sorted(
            units,
            key=lambda unit: (
                str(unit.baseRaceId or "").lower(),
                self.get_effective_name(unit).lower(),
                unit.unitId,
            ),
        )

    def get_unit_by_id(self, unit_id: str) -> Unit | None:
        return self.context.all_units.get(str(unit_id or "").strip())

    def get_unit(self, identifier: str) -> Unit | None:
        key = str(identifier or "").strip()
        if not key:
            return None

        by_id = self.get_unit_by_id(key)
        if by_id is not None:
            return by_id

        matches = [unit for unit in self.list_units() if self.get_effective_name(unit).lower() == key.lower()]
        if len(matches) == 1:
            return matches[0]
        return None

    def create_unit_from_dict(self, data: dict):
        unit = Unit.from_dict(
            data,
            resolve_character=self._resolve_character,
            resolve_spell=self._resolve_spell,
            resolve_item=self._resolve_item,
        )

        if self.race_service.get_race_by_id(unit.baseRaceId) is None:
            raise ValueError(f"Base race '{unit.baseRaceId}' does not exist.")

        if not unit.unitId:
            unit.unitId = self._generate_unit_id(unit.name or unit.baseRaceId)

        if unit.unitId in self.context.all_units:
            raise ValueError(f"Unit ID '{unit.unitId}' already exists.")

        self.context.all_units[unit.unitId] = unit
        self.save_unitbook()
        return unit

    def edit_unit_from_patch(self, unit_identifier: str, patch: dict):
        existing = self.get_unit(unit_identifier)
        if existing is None:
            raise ValueError(f"Unit '{unit_identifier}' does not exist or is ambiguous.")

        merged = existing.to_dict(
            resolve_character_id=self._resolve_character_id,
            resolve_item_id=self._resolve_item_id,
        )
        merged.update(patch or {})
        merged["unitId"] = existing.unitId
        merged["baseRaceId"] = existing.baseRaceId

        updated = Unit.from_dict(
            merged,
            resolve_character=self._resolve_character,
            resolve_spell=self._resolve_spell,
            resolve_item=self._resolve_item,
        )
        updated.unitId = existing.unitId
        updated.baseRaceId = existing.baseRaceId

        self.context.all_units[updated.unitId] = updated
        self.save_unitbook()
        return updated

    def replace_unit_from_dict(self, unit_identifier: str, data: dict):
        existing = self.get_unit(unit_identifier)
        if existing is None:
            raise ValueError(f"Unit '{unit_identifier}' does not exist or is ambiguous.")

        payload = dict(data or {})
        if not str(payload.get("baseRaceId", "") or "").strip():
            payload["baseRaceId"] = existing.baseRaceId

        updated = Unit.from_dict(
            payload,
            resolve_character=self._resolve_character,
            resolve_spell=self._resolve_spell,
            resolve_item=self._resolve_item,
        )

        if self.race_service.get_race_by_id(updated.baseRaceId) is None:
            raise ValueError(f"Base race '{updated.baseRaceId}' does not exist.")

        updated.unitId = existing.unitId
        self.context.all_units[updated.unitId] = updated
        self.save_unitbook()
        return updated

    def build_unitbook_overview(self, max_lines: int = 20) -> str:
        units = self.list_units()
        if not units:
            return "No units in unitbook yet."

        lines = []
        for unit in units[:max_lines]:
            base_race = self.resolve_base_race(unit)
            base_name = str(getattr(base_race, "name", "Unknown Race") or "Unknown Race")
            lines.append(f"- {self.get_effective_name(unit)} [{unit.unitId}] ({base_name})")

        if len(units) > max_lines:
            lines.append(f"... and {len(units) - max_lines} more")

        return "\n".join(lines)
