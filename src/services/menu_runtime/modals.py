from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from src.services.menu_runtime.fields import COMPONENT_FIELD_EDIT_CONFIG, ITEM_FIELD_EDIT_CONFIG, SPELL_FIELD_EDIT_CONFIG
from src.ui.menu import Menu

if TYPE_CHECKING:
    from src.services.menu_runtime.interfaces import OriginalMessage
    from src.services.menu_runtime.service import MenuRuntimeService


class FieldEditModal(discord.ui.Modal):
    def __init__(
        self,
        runtime: "MenuRuntimeService",
        original_message: "OriginalMessage",
        return_menu: Menu,
        draft_attr: str,
        field_key: str,
        field_label: str,
        parser,
        title: str,
    ):
        super().__init__(title=title)
        self.runtime = runtime
        self.original_message = original_message
        self.return_menu = return_menu
        self.draft_attr = draft_attr
        self.field_key = field_key
        self.field_label = field_label
        self.parser = parser
        self.value = discord.ui.TextInput(
            label=field_label,
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=4000,
        )
        self.add_item(self.value)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            parsed = self.parser(self.value.value)
            draft = getattr(self.original_message.menuContext, self.draft_attr)
            draft[self.field_key] = parsed
        except Exception as exc:
            await interaction.response.send_message(f"Invalid value: {exc}", ephemeral=True)
            return

        await interaction.response.defer()
        self.runtime._refresh_spellbook_overview()
        self.runtime._refresh_itembook_overview()
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


class SpellSelectModal(discord.ui.Modal, title="Edit Existing Spell"):
    spell_name = discord.ui.TextInput(
        label="Existing Spell Name",
        style=discord.TextStyle.short,
        required=True,
        max_length=100,
    )

    def __init__(self, runtime: "MenuRuntimeService", original_message: "OriginalMessage"):
        super().__init__()
        self.runtime = runtime
        self.original_message = original_message

    async def on_submit(self, interaction: discord.Interaction):
        spell_name = str(self.spell_name.value).strip()
        spell = self.runtime.spell_service.get_spell(spell_name)
        if spell is None:
            await interaction.response.send_message(f"Spell '{spell_name}' does not exist.", ephemeral=True)
            return

        self.runtime._start_spell_draft(self.original_message.menuContext, source_spell_name=spell.name)
        self.runtime._populate_spell_draft_from_spell(self.original_message.menuContext, spell)
        self.runtime._refresh_spellbook_overview()

        first_menu = self.runtime.context.menus_by_name.get("spellCreateNameMenu")
        if first_menu is None:
            self.runtime._clear_spell_draft(self.original_message.menuContext)
            await interaction.response.send_message("Spell editor menu is not configured.", ephemeral=True)
            return

        self.runtime.menu_service.update_menu_values(self.original_message, first_menu)
        rendered = self.runtime.menu_service.build_rendered_menu(
            first_menu,
            self.original_message,
            getattr(interaction.user, "display_name", interaction.user.name),
        )

        await interaction.response.defer()
        await self.original_message.message.edit(
            embed=self.runtime.build_discord_embed(rendered),
            view=self.runtime.build_view(first_menu, self.original_message),
        )


class ItemSelectModal(discord.ui.Modal, title="Edit Existing Item"):
    item_name = discord.ui.TextInput(
        label="Existing Item Name",
        style=discord.TextStyle.short,
        required=True,
        max_length=100,
    )

    def __init__(self, runtime: "MenuRuntimeService", original_message: "OriginalMessage"):
        super().__init__()
        self.runtime = runtime
        self.original_message = original_message

    async def on_submit(self, interaction: discord.Interaction):
        item_name = str(self.item_name.value).strip()
        item = self.runtime.item_service.get_item(item_name)
        if item is None:
            matches = self.runtime.item_service.get_items_by_name(item_name)
            if len(matches) > 1:
                await interaction.response.send_message(
                    f"Item name '{item_name}' is ambiguous. Use the item ID instead.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(f"Item '{item_name}' does not exist.", ephemeral=True)
            return

        self.runtime._start_item_draft(self.original_message.menuContext, source_item_id=item.itemId)
        self.runtime._populate_item_draft_from_item(self.original_message.menuContext, item)
        self.runtime._refresh_itembook_overview()

        first_menu = self.runtime.context.menus_by_name.get("itemCreateNameMenu")
        if first_menu is None:
            self.runtime._clear_item_draft(self.original_message.menuContext)
            await interaction.response.send_message("Item editor menu is not configured.", ephemeral=True)
            return

        self.runtime.menu_service.update_menu_values(self.original_message, first_menu)
        rendered = self.runtime.menu_service.build_rendered_menu(
            first_menu,
            self.original_message,
            getattr(interaction.user, "display_name", interaction.user.name),
        )

        await interaction.response.defer()
        await self.original_message.message.edit(
            embed=self.runtime.build_discord_embed(rendered),
            view=self.runtime.build_view(first_menu, self.original_message),
        )


def build_field_edit_modal(runtime: "MenuRuntimeService", menu: Menu, original_message: "OriginalMessage") -> discord.ui.Modal:
    if menu.uniqueName in SPELL_FIELD_EDIT_CONFIG:
        draft_attr = "spellDraft"
        field_key, field_label, parser = SPELL_FIELD_EDIT_CONFIG[menu.uniqueName]
        modal_title = "Edit Spell Field"
    elif menu.uniqueName in ITEM_FIELD_EDIT_CONFIG:
        draft_attr, field_key, field_label, parser = ITEM_FIELD_EDIT_CONFIG[menu.uniqueName]
        modal_title = "Edit Item Field"
    else:
        draft_attr, field_key, field_label, parser = COMPONENT_FIELD_EDIT_CONFIG[menu.uniqueName]
        modal_title = "Edit Field"

    return_menu = menu.parent if menu.parent is not None else menu
    return FieldEditModal(
        runtime=runtime,
        original_message=original_message,
        return_menu=return_menu,
        draft_attr=draft_attr,
        field_key=field_key,
        field_label=field_label,
        parser=parser,
        title=modal_title,
    )
