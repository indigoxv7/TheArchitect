from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class GameContext:
    # Discord runtime context
    guild: Any = None

    # Authorization state
    development_admin_whitelist: set[int] = field(default_factory=set)

    # Player runtime state
    existing_players: dict[int, bool] = field(default_factory=dict)
    player_cache: dict[int, object] = field(default_factory=dict)

    # Item runtime state
    all_items: dict[str, object] = field(default_factory=dict)
    all_items_by_name: dict[str, list[str]] = field(default_factory=dict)
    error_item: Optional[object] = None
    itembook_overview: str = "No items in itembook yet."
    max_num_characters: int = 4

    # Character runtime state
    all_characters: dict[str, object] = field(default_factory=dict)
    characterbook_overview: str = "No characters in characterbook yet."

    # Battle runtime state
    active_battles: dict[int, object] = field(default_factory=dict)

    # Menu runtime state
    menus_by_name: dict[str, object] = field(default_factory=dict)
    root_menu: Optional[object] = None
    new_player_menu: Optional[object] = None

    # Global spellbook runtime state
    global_spellbook: dict[str, object] = field(default_factory=dict)
    spellbook_overview: str = "No spells in spellbook yet."

    # Global achievementbook runtime state
    global_achievementbook: dict[str, object] = field(default_factory=dict)
    achievementbook_overview: str = "No achievements in achievementbook yet."

    # Global racebook runtime state
    all_races: dict[str, object] = field(default_factory=dict)
    racebook_overview: str = "No races in racebook yet."
