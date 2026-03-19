from __future__ import annotations

from abc import ABC, abstractmethod

import discord

from src.services.menu_service import RenderedMenu
from src.ui.menu import Menu, MenuContext


class MenuInterface(ABC):
    @property
    @abstractmethod
    def user_id(self) -> int:
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        pass

    @property
    @abstractmethod
    def supports_modals(self) -> bool:
        pass

    @property
    @abstractmethod
    def discord_interaction(self) -> discord.Interaction | None:
        pass

    @abstractmethod
    async def send_ephemeral(self, content: str):
        pass

    @abstractmethod
    async def before_update(self):
        pass

    @abstractmethod
    async def send_initial(self, rendered: RenderedMenu, menu: Menu, original_message: "OriginalMessage"):
        pass

    @abstractmethod
    async def send_update(self, rendered: RenderedMenu, menu: Menu, original_message: "OriginalMessage"):
        pass

    @abstractmethod
    async def send_modal(self, modal: discord.ui.Modal):
        pass


class OriginalMessage:
    def __init__(self, player, is_developer_admin: bool = False):
        self.player = player
        self.message = None
        self.menuContext = MenuContext()
        self.is_developer_admin = is_developer_admin

    def setMessageObject(self, message: discord.Message):
        self.message = message
