from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.domain.combat.enums import BattleTeam, EncounterType, enum_from_name


@dataclass
class EncounterEnemyEntry:
    kind: str
    identifier: str
    count: int = 1
    use_stack: bool = True
    notable: bool = False
    name_override: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "identifier": self.identifier,
            "count": int(self.count),
            "use_stack": bool(self.use_stack),
            "notable": bool(self.notable),
            "name_override": self.name_override,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EncounterEnemyEntry":
        data = data if isinstance(data, dict) else {}
        return cls(
            kind=str(data.get("kind", "race") or "race"),
            identifier=str(data.get("identifier", "") or ""),
            count=max(1, int(data.get("count", 1) or 1)),
            use_stack=bool(data.get("use_stack", True)),
            notable=bool(data.get("notable", False)),
            name_override=str(data.get("name_override", "") or ""),
        )


@dataclass
class ReinforcementEntry:
    exchange_number: int
    team: BattleTeam = BattleTeam.ENEMY
    entries: list[EncounterEnemyEntry] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "exchange_number": int(self.exchange_number),
            "team": self.team.name,
            "entries": [entry.to_dict() for entry in self.entries],
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ReinforcementEntry":
        data = data if isinstance(data, dict) else {}
        return cls(
            exchange_number=max(1, int(data.get("exchange_number", 1) or 1)),
            team=enum_from_name(BattleTeam, data.get("team"), BattleTeam.ENEMY),
            entries=[
                EncounterEnemyEntry.from_dict(entry)
                for entry in data.get("entries", []) or []
                if isinstance(entry, dict)
            ],
            message=str(data.get("message", "") or ""),
        )


@dataclass
class EncounterDefinition:
    encounter_id: str
    encounter_type: EncounterType
    name: str
    terrain: str
    width: int
    total_lines: int
    objective_text: str
    allow_retreat: bool = True
    enemy_entries: list[EncounterEnemyEntry] = field(default_factory=list)
    reinforcements: list[ReinforcementEntry] = field(default_factory=list)
    player_front_line: int = 0
    enemy_front_line: int = 0
    context_tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "encounter_id": self.encounter_id,
            "encounter_type": self.encounter_type.name,
            "name": self.name,
            "terrain": self.terrain,
            "width": int(self.width),
            "total_lines": int(self.total_lines),
            "objective_text": self.objective_text,
            "allow_retreat": bool(self.allow_retreat),
            "enemy_entries": [entry.to_dict() for entry in self.enemy_entries],
            "reinforcements": [entry.to_dict() for entry in self.reinforcements],
            "player_front_line": int(self.player_front_line),
            "enemy_front_line": int(self.enemy_front_line),
            "context_tags": [str(tag or "").strip().lower() for tag in self.context_tags if str(tag or "").strip()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EncounterDefinition":
        data = data if isinstance(data, dict) else {}
        total_lines = max(4, int(data.get("total_lines", 6) or 6))
        default_player_front = total_lines // 2
        default_enemy_front = default_player_front + 1
        return cls(
            encounter_id=str(data.get("encounter_id", "") or ""),
            encounter_type=enum_from_name(
                EncounterType,
                data.get("encounter_type"),
                EncounterType.SCAVENGING,
            ),
            name=str(data.get("name", "Encounter") or "Encounter"),
            terrain=str(data.get("terrain", "Open Ground") or "Open Ground"),
            width=max(1, int(data.get("width", 3) or 3)),
            total_lines=total_lines,
            objective_text=str(data.get("objective_text", "") or ""),
            allow_retreat=bool(data.get("allow_retreat", True)),
            enemy_entries=[
                EncounterEnemyEntry.from_dict(entry)
                for entry in data.get("enemy_entries", []) or []
                if isinstance(entry, dict)
            ],
            reinforcements=[
                ReinforcementEntry.from_dict(entry)
                for entry in data.get("reinforcements", []) or []
                if isinstance(entry, dict)
            ],
            player_front_line=int(data.get("player_front_line", default_player_front) or default_player_front),
            enemy_front_line=int(data.get("enemy_front_line", default_enemy_front) or default_enemy_front),
            context_tags=[str(tag or "").strip().lower() for tag in data.get("context_tags", []) or [] if str(tag or "").strip()],
        )
