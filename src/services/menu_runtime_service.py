from abc import ABC, abstractmethod

import discord

from src.bot.views.menu_view import SimpleMenu
from src.services.game_context import GameContext
from src.services.menu_service import MenuService, RenderedMenu
from src.services.player_service import PlayerService
from src.ui.menu_functions import Menu, MenuContext, MenuState


class MenuInterface(ABC):
    @property
    @abstractmethod
    def user_id(self) -> int:
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
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


class OriginalMessage:
    def __init__(self, player):
        self.player = player
        self.message = None
        self.menuContext = MenuContext()

    def setMessageObject(self, message: discord.Message):
        self.message = message


class MenuRuntimeService:
    def __init__(self, menu_service: MenuService, player_service: PlayerService, context: GameContext):
        self.menu_service = menu_service
        self.player_service = player_service
        self.context = context

    def build_discord_embed(self, rendered: RenderedMenu):
        embed = discord.Embed(title=rendered.title, description=rendered.description)
        embed.set_footer(text=rendered.footer)
        if rendered.imageURL:
            embed.set_image(url=rendered.imageURL)
        return embed

    def build_view(self, menu: Menu, original_message: OriginalMessage):
        visible_children = self.menu_service.get_visible_child_menus(menu, original_message)
        return SimpleMenu(
            current_menu=menu,
            original_message=original_message,
            visible_children=visible_children,
            on_select=self.update_menu,
        )

    async def display_menu(self, interaction: discord.Interaction, menu: Menu):
        interface = DiscordMenuInterface(interaction, self)
        await self.display_menu_with_interface(interface, menu)

    async def display_menu_with_interface(self, interface: MenuInterface, menu: Menu):
        player = await self.player_service.get_player(interface.user_id)
        original_message = OriginalMessage(player)

        active_menu = menu
        if player.isNewPlayer:
            original_message.menuContext.menuState = MenuState.NEW_PLAYER
            active_menu = self.context.new_player_menu
            player.isNewPlayer = False

        self.menu_service.update_menu_values(original_message, active_menu)
        rendered = self.menu_service.build_rendered_menu(active_menu, original_message, interface.display_name)
        await interface.send_initial(rendered, active_menu, original_message)
        return original_message, active_menu

    async def update_menu(self, interaction: discord.Interaction, menu: Menu, original_message: OriginalMessage):
        interface = DiscordMenuInterface(interaction, self)
        await self.update_menu_with_interface(interface, menu, original_message)

    async def update_menu_with_interface(self, interface: MenuInterface, menu: Menu, original_message: OriginalMessage):
        if interface.user_id != original_message.player.discordID:
            await interface.send_ephemeral("You can only interact with your own menus. use /menu to open your menu.")
            return menu

        await interface.before_update()
        self.menu_service.update_menu_values(original_message, menu)
        rendered = self.menu_service.build_rendered_menu(menu, original_message, interface.display_name)
        await interface.send_update(rendered, menu, original_message)
        return menu


class DiscordMenuInterface(MenuInterface):
    def __init__(self, interaction: discord.Interaction, runtime: MenuRuntimeService):
        self.interaction = interaction
        self.runtime = runtime

    @property
    def user_id(self) -> int:
        return self.interaction.user.id

    @property
    def display_name(self) -> str:
        return self.interaction.user.nick or self.interaction.user.display_name

    async def send_ephemeral(self, content: str):
        await self.interaction.response.send_message(content=content, ephemeral=True)

    async def before_update(self):
        await self.interaction.response.defer()

    async def send_initial(self, rendered: RenderedMenu, menu: Menu, original_message: OriginalMessage):
        embed = self.runtime.build_discord_embed(rendered)
        view = self.runtime.build_view(menu, original_message)
        await self.interaction.response.send_message(embed=embed, view=view)
        original_message.setMessageObject(await self.interaction.original_response())

    async def send_update(self, rendered: RenderedMenu, menu: Menu, original_message: OriginalMessage):
        embed = self.runtime.build_discord_embed(rendered)
        view = self.runtime.build_view(menu, original_message)
        await original_message.message.edit(embed=embed, view=view)


class ConsoleMenuInterface(MenuInterface):
    def __init__(self, user_id: int, display_name: str = "IntegrationTester"):
        self._user_id = user_id
        self._display_name = display_name

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def display_name(self) -> str:
        return self._display_name

    async def send_ephemeral(self, content: str):
        print(f"[EPHEMERAL] {content}")

    async def before_update(self):
        return

    @staticmethod
    def _safe_text(text):
        return str(text).encode("ascii", "backslashreplace").decode("ascii")

    def _print_render(self, rendered: RenderedMenu):
        print("[MENU]")
        print(f"Title: {self._safe_text(rendered.title)}")
        print(f"Body:\n{self._safe_text(rendered.description)}")
        print(f"Footer: {self._safe_text(rendered.footer)}")
        if rendered.imageURL:
            print(f"Image: {self._safe_text(rendered.imageURL)}")
        if rendered.hasBack:
            print("Button: back")
        for button in rendered.buttons:
            safe_label = self._safe_text(button.label)
            safe_emoji = self._safe_text(button.emoji)
            print(f"Button: {button.targetMenuName} label='{safe_label}' emoji='{safe_emoji}'")
        print("")

    async def send_initial(self, rendered: RenderedMenu, menu: Menu, original_message: OriginalMessage):
        self._print_render(rendered)

    async def send_update(self, rendered: RenderedMenu, menu: Menu, original_message: OriginalMessage):
        self._print_render(rendered)
