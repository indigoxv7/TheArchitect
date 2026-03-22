from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class GameContext:
    guild: Any = None
    development_admin_whitelist: set[int] = field(default_factory=set)

    existing_players: dict[int, bool] = field(default_factory=dict)
    player_cache: dict[int, object] = field(default_factory=dict)

    all_items: dict[str, object] = field(default_factory=dict)
    all_items_by_name: dict[str, list[str]] = field(default_factory=dict)
    error_item: Optional[object] = None
    itembook_overview: str = "No items in itembook yet."
    max_num_characters: int = 4

    all_characters: dict[str, object] = field(default_factory=dict)
    characterbook_overview: str = "No characters in characterbook yet."

    active_battles: dict[int, object] = field(default_factory=dict)
    active_missions: dict[int, object] = field(default_factory=dict)

    menus_by_name: dict[str, object] = field(default_factory=dict)
    root_menu: Optional[object] = None
    new_player_menu: Optional[object] = None

    global_spellbook: dict[str, object] = field(default_factory=dict)
    spellbook_overview: str = "No spells in spellbook yet."

    global_achievementbook: dict[str, object] = field(default_factory=dict)
    achievementbook_overview: str = "No achievements in achievementbook yet."

    all_races: dict[str, object] = field(default_factory=dict)
    racebook_overview: str = "No races in racebook yet."

    all_units: dict[str, object] = field(default_factory=dict)
    unitbook_overview: str = "No units in unitbook yet."

    all_allegiances: dict[str, object] = field(default_factory=dict)
    allegiancebook_overview: str = "No allegiances in allegiancebook yet."

    all_missions: dict[str, object] = field(default_factory=dict)
    missionbook_overview: str = "No missions in missionbook yet."

    all_campaigns: dict[str, object] = field(default_factory=dict)
    campaignbook_overview: str = "No campaigns in campaignbook yet."

    all_environment_effects: dict[str, object] = field(default_factory=dict)
    effectbook_overview: str = "No effects in effectbook yet."
    all_terrains: dict[str, object] = field(default_factory=dict)
    terrainbook_overview: str = "No terrains in terrainbook yet."
    all_climates: dict[str, object] = field(default_factory=dict)
    climatebook_overview: str = "No climates in climatebook yet."
    all_biomes: dict[str, object] = field(default_factory=dict)
    biomebook_overview: str = "No biomes in biomebook yet."
    all_node_roles: dict[str, object] = field(default_factory=dict)
    node_rolebook_overview: str = "No node roles yet."
    all_feature_templates: dict[str, object] = field(default_factory=dict)
    featurebook_overview: str = "No features yet."
    all_hook_templates: dict[str, object] = field(default_factory=dict)
    hookbook_overview: str = "No hooks yet."
    all_description_packs: dict[str, object] = field(default_factory=dict)
    description_packbook_overview: str = "No description packs yet."
    all_generation_profiles: dict[str, object] = field(default_factory=dict)
    generation_profilebook_overview: str = "No generation profiles yet."
