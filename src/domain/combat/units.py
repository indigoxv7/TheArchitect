from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.domain.race import CreatureSize
from src.domain.combat.enums import BattleTeam, CombatRole, enum_from_name, lane_width_for_size
from src.domain.combat_timing import (
    ExertionLevel,
    speed_factor_from_attributes,
    stamina_limit_from_physical_stamina,
    stamina_regen_per_second_from_physical_stamina,
)


@dataclass
class CombatUnitState:
    unit_id: str
    name: str
    team: BattleTeam
    role: CombatRole
    size: CreatureSize
    level: int
    health: float
    max_health: float
    health_state: str
    line: int = 0
    lane_start: int = 0
    lane_width: int = 1
    starting_line: int = 0
    character_instance_id: str = ""
    is_player_owned: bool = False
    is_boss: bool = False
    is_elite: bool = False
    template_character_id: str = ""
    race_id: str = "Human1"
    physical_power: float = 5.0
    physical_stamina: float = 5.0
    physical_resistance: float = 5.0
    magic_power: float = 5.0
    magic_stamina: float = 5.0
    magic_resistance: float = 5.0
    speed: float = 1.0
    stamina_current: float = 75.0
    stamina_limit: float = 75.0
    stamina_regen_per_second: float = 2.5
    stamina_last_update_time: float = 0.0
    next_action_time: float = 0.0
    exertion_level: str = ExertionLevel.FRESH.name
    primary_weapon_item_id: str = ""
    offhand_item_id: str = ""
    inventory_item_ids: list[str] = field(default_factory=list)
    spell_names: list[str] = field(default_factory=list)
    status_tokens: list[str] = field(default_factory=list)
    notable: bool = True

    @property
    def alive(self) -> bool:
        return float(self.health) > 0.0 and self.health_state != "DEAD"

    def to_dict(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "name": self.name,
            "team": self.team.name,
            "role": self.role.name,
            "size": self.size.name,
            "level": int(self.level),
            "health": float(self.health),
            "max_health": float(self.max_health),
            "health_state": self.health_state,
            "line": int(self.line),
            "lane_start": int(self.lane_start),
            "lane_width": int(self.lane_width),
            "starting_line": int(self.starting_line),
            "character_instance_id": self.character_instance_id,
            "is_player_owned": bool(self.is_player_owned),
            "is_boss": bool(self.is_boss),
            "is_elite": bool(self.is_elite),
            "template_character_id": self.template_character_id,
            "race_id": self.race_id,
            "physical_power": float(self.physical_power),
            "physical_stamina": float(self.physical_stamina),
            "physical_resistance": float(self.physical_resistance),
            "magic_power": float(self.magic_power),
            "magic_stamina": float(self.magic_stamina),
            "magic_resistance": float(self.magic_resistance),
            "speed": float(self.speed),
            "stamina_current": float(self.stamina_current),
            "stamina_limit": float(self.stamina_limit),
            "stamina_regen_per_second": float(self.stamina_regen_per_second),
            "stamina_last_update_time": float(self.stamina_last_update_time),
            "next_action_time": float(self.next_action_time),
            "exertion_level": self.exertion_level,
            "primary_weapon_item_id": self.primary_weapon_item_id,
            "offhand_item_id": self.offhand_item_id,
            "inventory_item_ids": list(self.inventory_item_ids),
            "spell_names": list(self.spell_names),
            "status_tokens": list(self.status_tokens),
            "notable": bool(self.notable),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "CombatUnitState":
        data = data if isinstance(data, dict) else {}
        size = enum_from_name(CreatureSize, data.get("size"), CreatureSize.STANDARD)
        physical_power = float(data.get("physical_power", 5.0) or 5.0)
        physical_stamina = float(data.get("physical_stamina", 5.0) or 5.0)
        magic_power = float(data.get("magic_power", 5.0) or 5.0)
        default_stamina_limit = stamina_limit_from_physical_stamina(physical_stamina)
        default_speed = speed_factor_from_attributes(physical_power, magic_power)
        default_regen = stamina_regen_per_second_from_physical_stamina(physical_stamina)
        return cls(
            unit_id=str(data.get("unit_id", "") or ""),
            name=str(data.get("name", "Unit") or "Unit"),
            team=enum_from_name(BattleTeam, data.get("team"), BattleTeam.ALLY),
            role=enum_from_name(CombatRole, data.get("role"), CombatRole.FRONTLINE),
            size=size,
            level=int(data.get("level", 0) or 0),
            health=float(data.get("health", 100.0) or 100.0),
            max_health=max(1.0, float(data.get("max_health", 100.0) or 100.0)),
            health_state=str(data.get("health_state", "HEALTHY") or "HEALTHY"),
            line=int(data.get("line", 0) or 0),
            lane_start=int(data.get("lane_start", 0) or 0),
            lane_width=max(1, int(data.get("lane_width", lane_width_for_size(size)) or lane_width_for_size(size))),
            starting_line=int(data.get("starting_line", data.get("line", 0)) or 0),
            character_instance_id=str(data.get("character_instance_id", "") or ""),
            is_player_owned=bool(data.get("is_player_owned", False)),
            is_boss=bool(data.get("is_boss", False)),
            is_elite=bool(data.get("is_elite", False)),
            template_character_id=str(data.get("template_character_id", "") or ""),
            race_id=str(data.get("race_id", "Human1") or "Human1"),
            physical_power=physical_power,
            physical_stamina=physical_stamina,
            physical_resistance=float(data.get("physical_resistance", 5.0) or 5.0),
            magic_power=magic_power,
            magic_stamina=float(data.get("magic_stamina", 5.0) or 5.0),
            magic_resistance=float(data.get("magic_resistance", 5.0) or 5.0),
            speed=float(data.get("speed", default_speed) or default_speed),
            stamina_current=float(data.get("stamina_current", default_stamina_limit) or default_stamina_limit),
            stamina_limit=float(data.get("stamina_limit", default_stamina_limit) or default_stamina_limit),
            stamina_regen_per_second=float(data.get("stamina_regen_per_second", default_regen) or default_regen),
            stamina_last_update_time=float(data.get("stamina_last_update_time", 0.0) or 0.0),
            next_action_time=float(data.get("next_action_time", 0.0) or 0.0),
            exertion_level=str(data.get("exertion_level", ExertionLevel.FRESH.name) or ExertionLevel.FRESH.name),
            primary_weapon_item_id=str(data.get("primary_weapon_item_id", "") or ""),
            offhand_item_id=str(data.get("offhand_item_id", "") or ""),
            inventory_item_ids=[str(item) for item in data.get("inventory_item_ids", []) or []],
            spell_names=[str(item) for item in data.get("spell_names", []) or []],
            status_tokens=[str(item) for item in data.get("status_tokens", []) or []],
            notable=bool(data.get("notable", True)),
        )


@dataclass
class EnemyStackState:
    stack_id: str
    name: str
    team: BattleTeam
    role: CombatRole
    size: CreatureSize
    count: int
    max_count: int
    unit_health: float
    total_health: float
    health_state: str
    line: int = 0
    lane_start: int = 0
    lane_width: int = 1
    starting_line: int = 0
    template_character_id: str = ""
    is_boss: bool = False
    is_elite: bool = False
    race_id: str = ""
    level: int = 0
    physical_power: float = 5.0
    physical_stamina: float = 5.0
    physical_resistance: float = 5.0
    magic_power: float = 5.0
    magic_stamina: float = 5.0
    magic_resistance: float = 5.0
    speed: float = 1.0
    stamina_current: float = 75.0
    stamina_limit: float = 75.0
    stamina_regen_per_second: float = 2.5
    stamina_last_update_time: float = 0.0
    next_action_time: float = 0.0
    exertion_level: str = ExertionLevel.FRESH.name
    primary_weapon_item_id: str = ""
    offhand_item_id: str = ""
    spell_names: list[str] = field(default_factory=list)
    status_tokens: list[str] = field(default_factory=list)

    @property
    def current_count(self) -> int:
        if self.total_health <= 0.0 or self.unit_health <= 0.0:
            return 0
        return max(0, min(self.max_count, int((self.total_health + self.unit_health - 1) // self.unit_health)))

    @property
    def alive(self) -> bool:
        return self.current_count > 0 and self.health_state != "DEAD"

    @property
    def health(self) -> float:
        return float(self.total_health)

    @property
    def max_health(self) -> float:
        return float(self.max_count) * float(self.unit_health)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stack_id": self.stack_id,
            "name": self.name,
            "team": self.team.name,
            "role": self.role.name,
            "size": self.size.name,
            "count": int(self.count),
            "max_count": int(self.max_count),
            "unit_health": float(self.unit_health),
            "total_health": float(self.total_health),
            "health_state": self.health_state,
            "line": int(self.line),
            "lane_start": int(self.lane_start),
            "lane_width": int(self.lane_width),
            "starting_line": int(self.starting_line),
            "template_character_id": self.template_character_id,
            "is_boss": bool(self.is_boss),
            "is_elite": bool(self.is_elite),
            "race_id": self.race_id,
            "level": int(self.level),
            "physical_power": float(self.physical_power),
            "physical_stamina": float(self.physical_stamina),
            "physical_resistance": float(self.physical_resistance),
            "magic_power": float(self.magic_power),
            "magic_stamina": float(self.magic_stamina),
            "magic_resistance": float(self.magic_resistance),
            "speed": float(self.speed),
            "stamina_current": float(self.stamina_current),
            "stamina_limit": float(self.stamina_limit),
            "stamina_regen_per_second": float(self.stamina_regen_per_second),
            "stamina_last_update_time": float(self.stamina_last_update_time),
            "next_action_time": float(self.next_action_time),
            "exertion_level": self.exertion_level,
            "primary_weapon_item_id": self.primary_weapon_item_id,
            "offhand_item_id": self.offhand_item_id,
            "spell_names": list(self.spell_names),
            "status_tokens": list(self.status_tokens),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EnemyStackState":
        data = data if isinstance(data, dict) else {}
        size = enum_from_name(CreatureSize, data.get("size"), CreatureSize.STANDARD)
        physical_power = float(data.get("physical_power", 5.0) or 5.0)
        physical_stamina = float(data.get("physical_stamina", 5.0) or 5.0)
        magic_power = float(data.get("magic_power", 5.0) or 5.0)
        default_stamina_limit = stamina_limit_from_physical_stamina(physical_stamina)
        default_speed = speed_factor_from_attributes(physical_power, magic_power)
        default_regen = stamina_regen_per_second_from_physical_stamina(physical_stamina)
        return cls(
            stack_id=str(data.get("stack_id", "") or ""),
            name=str(data.get("name", "Enemy Stack") or "Enemy Stack"),
            team=enum_from_name(BattleTeam, data.get("team"), BattleTeam.ENEMY),
            role=enum_from_name(CombatRole, data.get("role"), CombatRole.FRONTLINE),
            size=size,
            count=max(1, int(data.get("count", 1) or 1)),
            max_count=max(1, int(data.get("max_count", 1) or 1)),
            unit_health=max(1.0, float(data.get("unit_health", 100.0) or 100.0)),
            total_health=max(0.0, float(data.get("total_health", 100.0) or 100.0)),
            health_state=str(data.get("health_state", "HEALTHY") or "HEALTHY"),
            line=int(data.get("line", 0) or 0),
            lane_start=int(data.get("lane_start", 0) or 0),
            lane_width=max(1, int(data.get("lane_width", lane_width_for_size(size)) or lane_width_for_size(size))),
            starting_line=int(data.get("starting_line", data.get("line", 0)) or 0),
            template_character_id=str(data.get("template_character_id", "") or ""),
            is_boss=bool(data.get("is_boss", False)),
            is_elite=bool(data.get("is_elite", False)),
            race_id=str(data.get("race_id", "") or ""),
            level=int(data.get("level", 0) or 0),
            physical_power=physical_power,
            physical_stamina=physical_stamina,
            physical_resistance=float(data.get("physical_resistance", 5.0) or 5.0),
            magic_power=magic_power,
            magic_stamina=float(data.get("magic_stamina", 5.0) or 5.0),
            magic_resistance=float(data.get("magic_resistance", 5.0) or 5.0),
            speed=float(data.get("speed", default_speed) or default_speed),
            stamina_current=float(data.get("stamina_current", default_stamina_limit) or default_stamina_limit),
            stamina_limit=float(data.get("stamina_limit", default_stamina_limit) or default_stamina_limit),
            stamina_regen_per_second=float(data.get("stamina_regen_per_second", default_regen) or default_regen),
            stamina_last_update_time=float(data.get("stamina_last_update_time", 0.0) or 0.0),
            next_action_time=float(data.get("next_action_time", 0.0) or 0.0),
            exertion_level=str(data.get("exertion_level", ExertionLevel.FRESH.name) or ExertionLevel.FRESH.name),
            primary_weapon_item_id=str(data.get("primary_weapon_item_id", "") or ""),
            offhand_item_id=str(data.get("offhand_item_id", "") or ""),
            spell_names=[str(item) for item in data.get("spell_names", []) or []],
            status_tokens=[str(item) for item in data.get("status_tokens", []) or []],
        )
