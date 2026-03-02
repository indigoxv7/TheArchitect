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
    error_item: Optional[object] = None
    max_num_characters: int = 4

    # Menu runtime state
    menus_by_name: dict[str, object] = field(default_factory=dict)
    root_menu: Optional[object] = None
    new_player_menu: Optional[object] = None

    # Global spellbook runtime state
    global_spellbook: dict[str, object] = field(default_factory=dict)
    spellbook_overview: str = "No spells in spellbook yet."
