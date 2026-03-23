from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class AdminServices:
    spell_service: object
    item_service: object
    character_service: object
    achievement_service: object
    player_service: object
    race_service: object
    unit_service: object
    allegiance_service: object
    mission_service: object
    campaign_service: object
    environment_service: object
    memory_service: object
    power_rating_service: object
    combat_simulator_service: object
    openai_service: object | None = None
    local_scene_service: object | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
