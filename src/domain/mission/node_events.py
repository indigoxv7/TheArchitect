from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class MissionNodeEventType(Enum):
    TREASURE = "Treasure"
    CLUE = "Clue"


@dataclass
class MissionNodeEvent:
    eventType: MissionNodeEventType
    title: str
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "eventType": self.eventType.name,
            "title": str(self.title or ""),
            "description": str(self.description or ""),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "MissionNodeEvent":
        if not isinstance(data, dict):
            raise ValueError("Mission node event data must be a dictionary.")
        event_type_name = str(data.get("eventType", MissionNodeEventType.TREASURE.name) or MissionNodeEventType.TREASURE.name)
        event_type = MissionNodeEventType[event_type_name] if event_type_name in MissionNodeEventType.__members__ else MissionNodeEventType.TREASURE
        return cls(
            eventType=event_type,
            title=str(data.get("title", "") or ""),
            description=str(data.get("description", "") or ""),
        )
