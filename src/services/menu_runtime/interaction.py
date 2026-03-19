from __future__ import annotations

import discord

from src.bot.views.menu_view import SimpleMenu
from src.services.menu_runtime.interfaces import MenuInterface, OriginalMessage
from src.services.menu_runtime.modals import ItemSelectModal, SpellSelectModal, build_field_edit_modal
from src.services.menu_service import RenderedMenu
from src.ui.menu import Menu, MenuState


class MenuRuntimeInteractionMixin:
    def build_discord_embed(self, rendered: RenderedMenu):
        embed = discord.Embed(title=rendered.title, description=rendered.description)
        embed.set_footer(text=rendered.footer)
        if rendered.thumbnailURL:
            embed.set_thumbnail(url=rendered.thumbnailURL)
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

    def build_spell_select_modal(self, original_message: OriginalMessage) -> discord.ui.Modal:
        return SpellSelectModal(self, original_message)

    def build_item_select_modal(self, original_message: OriginalMessage) -> discord.ui.Modal:
        return ItemSelectModal(self, original_message)

    def build_field_edit_modal(self, menu: Menu, original_message: OriginalMessage) -> discord.ui.Modal:
        return build_field_edit_modal(self, menu, original_message)

    async def _handle_special_menu_action(self, interface: MenuInterface, menu: Menu, original_message: OriginalMessage):
        return await self._special_action_router.handle(interface, menu, original_message)

    async def display_menu(self, interaction: discord.Interaction, menu: Menu):
        interface = DiscordMenuInterface(interaction, self)
        await self.display_menu_with_interface(interface, menu)

    async def display_menu_with_interface(self, interface: MenuInterface, menu: Menu):
        player = await self.player_service.get_player(interface.user_id)
        self.player_service.sync_player_name(player, interface.display_name, persist=True)
        original_message = OriginalMessage(
            player,
            is_developer_admin=self.whitelist_service.is_admin(interface.user_id),
        )

        active_menu = menu
        if player.isNewPlayer:
            original_message.menuContext.menuState = MenuState.NEW_PLAYER
            active_menu = self.context.new_player_menu
            player.isNewPlayer = False

        self._refresh_spellbook_overview()
        self._refresh_itembook_overview()
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

        special_result = await self._handle_special_menu_action(interface, menu, original_message)
        if special_result is not None:
            target_menu, should_render, response_consumed = special_result
            if not should_render:
                return target_menu
            menu = target_menu
            if not response_consumed:
                await interface.before_update()
        else:
            response_consumed = False
            if menu.uniqueName == "spellbookMenu" and original_message.menuContext.spellDraftActive:
                was_edit = bool(original_message.menuContext.spellDraftSourceName)
                self._clear_spell_draft(original_message.menuContext)
                await interface.send_ephemeral("Spell edit cancelled." if was_edit else "Spell creation cancelled.")
                response_consumed = True
            if menu.uniqueName == "itembookMenu" and original_message.menuContext.itemDraftActive:
                was_edit = bool(
                    getattr(original_message.menuContext, "itemDraftSourceId", None)
                    or original_message.menuContext.itemDraftSourceName
                )
                self._clear_item_draft(original_message.menuContext)
                await interface.send_ephemeral("Item edit cancelled." if was_edit else "Item creation cancelled.")
                response_consumed = True
            if menu.uniqueName == "mainMenu" and original_message.menuContext.attributesDraftActive:
                self._clear_attributes_draft(original_message.menuContext)
                await interface.send_ephemeral("Attributes editor cancelled.")
                response_consumed = True
            if menu.uniqueName == "mainMenu" and original_message.menuContext.gearDraftActive:
                self._clear_gear_draft(original_message.menuContext)
                await interface.send_ephemeral("Gear editor cancelled.")
                response_consumed = True
            if menu.uniqueName == "mainMenu" and original_message.menuContext.bonusDraftActive:
                self._clear_bonus_draft(original_message.menuContext)
                await interface.send_ephemeral("Bonus editor cancelled.")
                response_consumed = True
            if menu.uniqueName == "mainMenu" and original_message.menuContext.achievementDraftActive:
                self._clear_achievement_draft(original_message.menuContext)
                await interface.send_ephemeral("Achievement editor cancelled.")
                response_consumed = True
            if not response_consumed:
                await interface.before_update()

        self._refresh_spellbook_overview()
        self._refresh_itembook_overview()
        self.menu_service.update_menu_values(original_message, menu)
        rendered = self.menu_service.build_rendered_menu(menu, original_message, interface.display_name)
        await interface.send_update(rendered, menu, original_message)
        return menu


class DiscordMenuInterface(MenuInterface):
    def __init__(self, interaction: discord.Interaction, runtime):
        self.interaction = interaction
        self.runtime = runtime

    @property
    def user_id(self) -> int:
        return self.interaction.user.id

    @property
    def display_name(self) -> str:
        return self.interaction.user.nick or self.interaction.user.display_name

    @property
    def supports_modals(self) -> bool:
        return True

    @property
    def discord_interaction(self) -> discord.Interaction | None:
        return self.interaction

    async def send_ephemeral(self, content: str):
        if self.interaction.response.is_done():
            await self.interaction.followup.send(content=content, ephemeral=True)
        else:
            await self.interaction.response.send_message(content=content, ephemeral=True)

    async def before_update(self):
        if not self.interaction.response.is_done():
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

    async def send_modal(self, modal: discord.ui.Modal):
        await self.interaction.response.send_modal(modal)


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

    @property
    def supports_modals(self) -> bool:
        return False

    @property
    def discord_interaction(self) -> discord.Interaction | None:
        return None

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
        if rendered.thumbnailURL:
            print(f"Thumbnail: {self._safe_text(rendered.thumbnailURL)}")
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

    async def send_modal(self, modal: discord.ui.Modal):
        raise RuntimeError("Console menu interface does not support modals.")
