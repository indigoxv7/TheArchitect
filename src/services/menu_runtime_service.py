import json
from abc import ABC, abstractmethod

import discord

from src.bot.views.menu_view import SimpleMenu
from src.services.game_context import GameContext
from src.services.menu_service import MenuService, RenderedMenu
from src.services.player_service import PlayerService
from src.services.spell_service import SpellService
from src.services.whitelist_service import AdminWhitelistService
from src.ui.menu_functions import Menu, MenuContext, MenuState


SPELL_FIELD_DEFAULTS = {
    "name": "",
    "level": "",
    "power": "",
    "affinity": "",
    "casting_time": "",
    "range": "",
    "component_verbal": "",
    "component_somatic": "",
    "component_material": "",
    "duration": "",
    "description": "",
    "higher_level": "",
}


def _parse_non_empty_text(value: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError("Value cannot be empty.")
    return text


def _parse_level(value: str) -> int:
    text = str(value).strip()
    level = int(text)
    if level < 0:
        raise ValueError("Level must be >= 0.")
    return level


def _parse_bool_yes_no(value: str) -> bool:
    text = str(value).strip().lower()
    if text in {"y", "yes", "true", "1"}:
        return True
    if text in {"n", "no", "false", "0"}:
        return False
    raise ValueError("Use yes/no.")


def _parse_material(value: str):
    text = str(value).strip()
    if not text:
        return False
    if text.lower() in {"none", "false", "no"}:
        return False
    return text


def _parse_optional_text(value: str):
    text = str(value).strip()
    return text if text else ""


FIELD_EDIT_CONFIG = {
    "spellSetNameAction": ("name", "Spell Name", _parse_non_empty_text),
    "spellSetLevelAction": ("level", "Spell Level", _parse_level),
    "spellSetPowerAction": ("power", "Power", _parse_non_empty_text),
    "spellSetAffinityAction": ("affinity", "Affinity", _parse_non_empty_text),
    "spellSetCastingTimeAction": ("casting_time", "Casting Time", _parse_non_empty_text),
    "spellSetRangeAction": ("range", "Range", _parse_non_empty_text),
    "spellSetVerbalAction": ("component_verbal", "Verbal Component (yes/no)", _parse_bool_yes_no),
    "spellSetSomaticAction": ("component_somatic", "Somatic Component (yes/no)", _parse_bool_yes_no),
    "spellSetMaterialAction": ("component_material", "Material Component (text or none)", _parse_material),
    "spellSetDurationAction": ("duration", "Duration", _parse_non_empty_text),
    "spellSetDescriptionAction": ("description", "Description", _parse_non_empty_text),
    "spellSetHigherLevelAction": ("higher_level", "Higher Level Text (optional)", _parse_optional_text),
}


class FieldEditModal(discord.ui.Modal, title="Edit Spell Field"):
    value = discord.ui.TextInput(
        label="Value",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000,
    )

    def __init__(self, runtime: "MenuRuntimeService", original_message: "OriginalMessage", return_menu: Menu, field_key: str, field_label: str, parser):
        super().__init__()
        self.runtime = runtime
        self.original_message = original_message
        self.return_menu = return_menu
        self.field_key = field_key
        self.field_label = field_label
        self.parser = parser
        self.value.label = field_label

    async def on_submit(self, interaction: discord.Interaction):
        try:
            parsed = self.parser(str(self.value))
            self.original_message.menuContext.spellDraft[self.field_key] = parsed
        except Exception as exc:
            await interaction.response.send_message(f"Invalid value: {exc}", ephemeral=True)
            return

        await interaction.response.defer()
        self.runtime._refresh_spellbook_overview()
        self.runtime.menu_service.update_menu_values(self.original_message, self.return_menu)
        rendered = self.runtime.menu_service.build_rendered_menu(
            self.return_menu,
            self.original_message,
            getattr(interaction.user, "display_name", interaction.user.name),
        )
        await self.original_message.message.edit(
            embed=self.runtime.build_discord_embed(rendered),
            view=self.runtime.build_view(self.return_menu, self.original_message),
        )


class SpellEditModal(discord.ui.Modal, title="Edit Existing Spell"):
    spell_name = discord.ui.TextInput(
        label="Existing Spell Name",
        style=discord.TextStyle.short,
        required=True,
        max_length=100,
    )
    spell_patch_json = discord.ui.TextInput(
        label="Patch JSON",
        style=discord.TextStyle.paragraph,
        placeholder='{"level":2,"power":"2d8"}',
        required=True,
        max_length=4000,
    )

    def __init__(self, spell_service: SpellService):
        super().__init__()
        self.spell_service = spell_service

    async def on_submit(self, interaction: discord.Interaction):
        try:
            spell_name = str(self.spell_name).strip()
            patch = json.loads(str(self.spell_patch_json))
            self.spell_service.edit_spell_from_patch(spell_name, patch)
            await interaction.response.send_message("Spell updated successfully.", ephemeral=True)
        except Exception as exc:
            await interaction.response.send_message(f"Failed to edit spell: {exc}", ephemeral=True)


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
    def __init__(self, player, is_developer_admin: bool = False):
        self.player = player
        self.message = None
        self.menuContext = MenuContext()
        self.is_developer_admin = is_developer_admin

    def setMessageObject(self, message: discord.Message):
        self.message = message


class MenuRuntimeService:
    def __init__(
        self,
        menu_service: MenuService,
        player_service: PlayerService,
        whitelist_service: AdminWhitelistService,
        spell_service: SpellService,
        context: GameContext,
    ):
        self.menu_service = menu_service
        self.player_service = player_service
        self.whitelist_service = whitelist_service
        self.spell_service = spell_service
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

    @staticmethod
    def _build_spell_payload_from_draft(draft: dict) -> dict:
        return {
            "name": draft.get("name", ""),
            "level": draft.get("level", 0),
            "power": draft.get("power", ""),
            "affinity": draft.get("affinity", ""),
            "casting_time": draft.get("casting_time", ""),
            "range": draft.get("range", ""),
            "components": {
                "verbal": bool(draft.get("component_verbal", False)),
                "somatic": bool(draft.get("component_somatic", False)),
                "material": draft.get("component_material", False),
            },
            "duration": draft.get("duration", ""),
            "description": draft.get("description", ""),
            "higher_level": draft.get("higher_level", ""),
        }

    @staticmethod
    def _start_spell_draft(menu_context: MenuContext):
        menu_context.spellDraft = dict(SPELL_FIELD_DEFAULTS)
        menu_context.spellDraftActive = True

    @staticmethod
    def _clear_spell_draft(menu_context: MenuContext):
        menu_context.spellDraft = {}
        menu_context.spellDraftActive = False

    def _refresh_spellbook_overview(self):
        self.context.spellbook_overview = self.spell_service.build_spellbook_overview()

    async def _handle_special_menu_action(self, interface: "MenuInterface", menu: Menu, original_message: OriginalMessage):
        # returns (target_menu, should_render_menu, response_already_consumed)
        if menu.uniqueName == "spellCreateAction":
            self._start_spell_draft(original_message.menuContext)
            return self.context.menus_by_name.get("spellCreateNameMenu", menu), True, False

        if menu.uniqueName == "spellCreateSaveAction":
            if not original_message.is_developer_admin:
                await interface.send_ephemeral("You are not authorized to save spells.")
                return menu.parent if menu.parent is not None else menu, False, True

            payload = self._build_spell_payload_from_draft(original_message.menuContext.spellDraft)
            try:
                self.spell_service.create_spell_from_dict(payload)
                await interface.send_ephemeral("Spell saved.")
            except Exception as exc:
                await interface.send_ephemeral(f"Failed to save spell: {exc}")
            self._clear_spell_draft(original_message.menuContext)
            self._refresh_spellbook_overview()
            return self.context.menus_by_name.get("spellbookMenu", menu), True, True

        if menu.uniqueName == "spellCreateCancelAction":
            self._clear_spell_draft(original_message.menuContext)
            self._refresh_spellbook_overview()
            await interface.send_ephemeral("Spell creation cancelled.")
            return self.context.menus_by_name.get("spellbookMenu", menu), True, True

        if menu.uniqueName == "spellEditAction":
            if not original_message.is_developer_admin:
                await interface.send_ephemeral("You are not authorized to edit spells.")
                return menu.parent if menu.parent is not None else menu, False, True
            if isinstance(interface, DiscordMenuInterface):
                await interface.interaction.response.send_modal(SpellEditModal(self.spell_service))
            else:
                await interface.send_ephemeral("Spell edit modal is available in Discord UI only.")
            self._refresh_spellbook_overview()
            return menu.parent if menu.parent is not None else menu, False, True

        if menu.uniqueName in FIELD_EDIT_CONFIG:
            if not original_message.is_developer_admin:
                await interface.send_ephemeral("You are not authorized to edit spells.")
                return menu.parent if menu.parent is not None else menu, False, True

            if isinstance(interface, DiscordMenuInterface):
                field_key, field_label, parser = FIELD_EDIT_CONFIG[menu.uniqueName]
                return_menu = menu.parent if menu.parent is not None else menu
                await interface.interaction.response.send_modal(
                    FieldEditModal(
                        runtime=self,
                        original_message=original_message,
                        return_menu=return_menu,
                        field_key=field_key,
                        field_label=field_label,
                        parser=parser,
                    )
                )
            else:
                await interface.send_ephemeral("Field edit modal is available in Discord UI only.")
            return menu.parent if menu.parent is not None else menu, False, True

        return None

    async def display_menu(self, interaction: discord.Interaction, menu: Menu):
        interface = DiscordMenuInterface(interaction, self)
        await self.display_menu_with_interface(interface, menu)

    async def display_menu_with_interface(self, interface: MenuInterface, menu: Menu):
        player = await self.player_service.get_player(interface.user_id)
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
            if menu.uniqueName == "spellbookMenu" and original_message.menuContext.spellDraftActive:
                self._clear_spell_draft(original_message.menuContext)
                await interface.send_ephemeral("Spell creation cancelled.")
            await interface.before_update()

        self._refresh_spellbook_overview()
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

