from __future__ import annotations

from src.services.game_context import GameContext
from src.services.item_service import ItemService
from src.services.menu_runtime.actions import MenuSpecialActionRouter
from src.services.menu_runtime.drafts import MenuRuntimeDraftMixin
from src.services.menu_runtime.interaction import MenuRuntimeInteractionMixin
from src.services.menu_service import MenuService
from src.services.player_service import PlayerService
from src.services.spell_service import SpellService
from src.services.whitelist_service import AdminWhitelistService


class MenuRuntimeService(MenuRuntimeDraftMixin, MenuRuntimeInteractionMixin):
    def __init__(
        self,
        menu_service: MenuService,
        player_service: PlayerService,
        whitelist_service: AdminWhitelistService,
        spell_service: SpellService,
        item_service: ItemService,
        context: GameContext,
        battle_runtime_service=None,
        mission_runtime_service=None,
        player_character_runtime_service=None,
    ):
        self.menu_service = menu_service
        self.player_service = player_service
        self.whitelist_service = whitelist_service
        self.spell_service = spell_service
        self.item_service = item_service
        self.context = context
        self.battle_runtime_service = battle_runtime_service
        self.mission_runtime_service = mission_runtime_service
        self.player_character_runtime_service = player_character_runtime_service
        self._special_action_router = MenuSpecialActionRouter(self)
