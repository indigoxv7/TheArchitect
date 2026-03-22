from __future__ import annotations

from dataclasses import dataclass

import discord

from src.bot.views.player_character_view import (
    FIELD_SPECS,
    SECTION_FIELDS,
    SECTION_ORDER,
    SECTION_TITLES,
    PlayerCharacterFieldModal,
    PlayerCustomizationHomeView,
    PlayerCustomizationRandomizeView,
    PlayerCustomizationSectionView,
)
from src.domain.main_character import HobbyInterestLevel
from src.services.menu_runtime.interfaces import OriginalMessage


@dataclass(frozen=True)
class SectionPreview:
    title: str
    body: str


class PlayerCharacterRuntimeService:
    def __init__(self, player_service, whitelist_service=None, menu_runtime_service=None):
        self.player_service = player_service
        self.whitelist_service = whitelist_service
        self.menu_runtime_service = menu_runtime_service

    def set_menu_runtime_service(self, menu_runtime_service):
        self.menu_runtime_service = menu_runtime_service

    @staticmethod
    def _display_name(interaction: discord.Interaction) -> str:
        return str(getattr(interaction.user, "nick", None) or interaction.user.display_name or interaction.user.name)

    @staticmethod
    def _truncate(value: str, limit: int = 240) -> str:
        text = str(value or "").strip()
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    async def _load_owned_player(self, interaction: discord.Interaction, player_id: int):
        if int(interaction.user.id) != int(player_id):
            if interaction.response.is_done():
                await interaction.followup.send("You can only customize your own player character.", ephemeral=True)
            else:
                await interaction.response.send_message(
                    "You can only customize your own player character.",
                    ephemeral=True,
                )
            return None
        player = await self.player_service.get_player(int(player_id))
        changed = self.player_service.ensure_player_character(player, preferred_name=self._display_name(interaction))
        if changed:
            self.player_service.persist_player(player)
        return player

    async def _edit_message(self, interaction: discord.Interaction, *, embed: discord.Embed, view: discord.ui.View):
        kwargs = {"embed": embed, "view": view, "attachments": []}
        if interaction.response.is_done():
            if interaction.message is not None:
                await interaction.message.edit(**kwargs)
            else:
                await interaction.followup.send(**kwargs, ephemeral=True)
        else:
            await interaction.response.edit_message(**kwargs)

    def _player_character(self, player):
        self.player_service.ensure_player_character(player, preferred_name=getattr(player, "playerName", ""))
        return getattr(player, "playerCharacter", None)

    def _field_value(self, player_character, field_key: str):
        spec = FIELD_SPECS[field_key]
        if spec.kind == "hobbies":
            return list(getattr(player_character, "hobbies", []) or [])
        container = player_character if spec.container == "character" else getattr(player_character, spec.container)
        return getattr(container, spec.attr, "")

    def _set_field_value(self, player_character, field_key: str, value):
        spec = FIELD_SPECS[field_key]
        if spec.kind == "hobbies":
            player_character.hobbies = value
            return
        container = player_character if spec.container == "character" else getattr(player_character, spec.container)
        setattr(container, spec.attr, value)

    @staticmethod
    def _interest_label(interest) -> str:
        if isinstance(interest, HobbyInterestLevel):
            return interest.value
        return str(interest or "").strip()

    def _format_hobbies(self, hobbies) -> str:
        entries = list(hobbies or [])
        if not entries:
            return "No particular hobby | Indifferent"
        lines = []
        for hobby_name, interest in entries:
            name = str(hobby_name or "").strip()
            if not name:
                continue
            lines.append(f"{name} | {self._interest_label(interest)}")
        return "\n".join(lines) if lines else "No particular hobby | Indifferent"

    def _display_value(self, player_character, field_key: str) -> str:
        spec = FIELD_SPECS[field_key]
        value = self._field_value(player_character, field_key)
        if spec.kind == "hobbies":
            return self._format_hobbies(value)
        if spec.kind == "int":
            return str(int(value or 0))
        text = str(value or "").strip()
        return text or "Not set"

    def current_field_text(self, player_id: int, field_key: str) -> str:
        player = self.player_service.get_player_sync(int(player_id))
        if player is None:
            return ""
        player_character = self._player_character(player)
        if player_character is None:
            return ""
        value = self._field_value(player_character, field_key)
        if FIELD_SPECS[field_key].kind == "hobbies":
            return self._format_hobbies(value)
        return str(value or "")

    @staticmethod
    def _parse_hobbies(text: str) -> list[tuple[str, HobbyInterestLevel]]:
        lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
        if not lines:
            return [("No particular hobby", HobbyInterestLevel.INDIFFERENT)]

        result: list[tuple[str, HobbyInterestLevel]] = []
        seen: set[str] = set()
        for line in lines:
            if "|" in line:
                hobby_name, raw_interest = [part.strip() for part in line.split("|", 1)]
            else:
                hobby_name, raw_interest = line.strip(), HobbyInterestLevel.INTERESTED.value
            normalized_name = str(hobby_name or "").strip()
            if not normalized_name:
                continue
            lowered_name = normalized_name.lower()
            if lowered_name in seen:
                continue
            interest = None
            normalized_interest = str(raw_interest or "").strip().replace(" ", "").replace("_", "")
            for option in HobbyInterestLevel:
                if normalized_interest.lower() in {
                    option.name.replace("_", "").lower(),
                    option.value.replace(" ", "").replace("_", "").lower(),
                }:
                    interest = option
                    break
            if interest is None:
                raise ValueError(
                    f"Unknown hobby interest '{raw_interest}'. Use BurningPassion, Passionate, Interested, or Indifferent."
                )
            seen.add(lowered_name)
            result.append((normalized_name, interest))

        return result or [("No particular hobby", HobbyInterestLevel.INDIFFERENT)]

    def _coerce_field_input(self, player, field_key: str, raw_value: str):
        spec = FIELD_SPECS[field_key]
        text = str(raw_value or "").strip()
        if field_key == "name":
            return text or str(getattr(player, "playerName", "") or "Player")
        if spec.kind == "hobbies":
            return self._parse_hobbies(raw_value)
        if spec.kind == "int":
            if not text:
                return 0
            value = int(text)
            return max(0, value)
        return text

    def _apply_character_media(self, embed: discord.Embed, player_character):
        portrait_url = str(getattr(player_character, "portraitURL", "") or "").strip()
        footer_image_url = str(getattr(player_character, "footerImageURL", "") or "").strip()
        if portrait_url:
            embed.set_thumbnail(url=portrait_url)
        if footer_image_url:
            embed.set_image(url=footer_image_url)

    def _section_preview(self, player_character, section_key: str) -> SectionPreview:
        lines = []
        for field_key in SECTION_FIELDS.get(section_key, []):
            spec = FIELD_SPECS[field_key]
            value = self._display_value(player_character, field_key)
            if field_key == "description":
                value = self._truncate(value, 120)
            elif field_key == "hobbies":
                value = self._truncate(value.replace("\n", "; "), 180)
            else:
                value = self._truncate(value, 80)
            lines.append(f"{spec.label}: {value}")
        return SectionPreview(title=SECTION_TITLES.get(section_key, section_key.title()), body="\n".join(lines) or "Nothing set.")

    def _build_home_embed(self, player, player_character) -> discord.Embed:
        embed = discord.Embed(
            title="Customize Player Character",
            description=(
                f"Current name: **{getattr(player_character, 'name', 'Player')}**\n\n"
                "This character is for roleplay and memory context. It does not appear in your owned characters "
                "and cannot be selected for missions."
            ),
        )
        for section_key in SECTION_ORDER:
            preview = self._section_preview(player_character, section_key)
            embed.add_field(name=preview.title, value=preview.body, inline=False)
        embed.set_footer(text="Choose a section to edit. Randomize will replace the current character details.")
        self._apply_character_media(embed, player_character)
        return embed

    def _build_section_embed(self, player, player_character, section_key: str) -> discord.Embed:
        title = SECTION_TITLES.get(section_key, section_key.title())
        embed = discord.Embed(
            title=f"Customize Player Character | {title}",
            description=f"Editing **{getattr(player_character, 'name', 'Player')}**.",
        )
        if section_key == "hobbies":
            embed.add_field(
                name="Formatting",
                value="One hobby per line. Use `Hobby | Interested` or `Hobby | BurningPassion`.",
                inline=False,
            )
        for field_key in SECTION_FIELDS.get(section_key, []):
            spec = FIELD_SPECS[field_key]
            embed.add_field(name=spec.label, value=self._display_value(player_character, field_key), inline=False)
        embed.set_footer(text="Use the buttons below to edit fields for this section.")
        self._apply_character_media(embed, player_character)
        return embed

    def _build_randomize_embed(self, player_character) -> discord.Embed:
        embed = discord.Embed(
            title="Randomize Player Character",
            description=(
                "This will randomize all existing character details for this player character.\n\n"
                f"The character name will be reset to your Discord name instead of **{getattr(player_character, 'name', 'Player')}**."
            ),
        )
        embed.set_footer(text="Choose Back to cancel, or Confirm Randomize to replace the current details.")
        self._apply_character_media(embed, player_character)
        return embed

    async def _render_menu(self, interaction: discord.Interaction, player, menu_name: str):
        if self.menu_runtime_service is None:
            await interaction.response.send_message("Menu runtime is unavailable.", ephemeral=True)
            return
        menu = self.menu_runtime_service.context.menus_by_name.get(str(menu_name or ""))
        if menu is None:
            await interaction.response.send_message("That menu is unavailable.", ephemeral=True)
            return
        original_message = OriginalMessage(
            player,
            is_developer_admin=(
                self.whitelist_service.is_admin(interaction.user.id) if self.whitelist_service is not None else False
            ),
        )
        if interaction.message is not None:
            original_message.setMessageObject(interaction.message)
        self.menu_runtime_service.menu_service.update_menu_values(original_message, menu)
        rendered = self.menu_runtime_service.menu_service.build_rendered_menu(
            menu,
            original_message,
            self._display_name(interaction),
        )
        await self._edit_message(
            interaction,
            embed=self.menu_runtime_service.build_discord_embed(rendered),
            view=self.menu_runtime_service.build_view(menu, original_message),
        )

    async def open_customization(self, interaction: discord.Interaction, player_id: int):
        player = await self._load_owned_player(interaction, player_id)
        if player is None:
            return
        player_character = self._player_character(player)
        embed = self._build_home_embed(player, player_character)
        view = PlayerCustomizationHomeView(self, int(player_id))
        await self._edit_message(interaction, embed=embed, view=view)

    async def show_section(self, interaction: discord.Interaction, player_id: int, section_key: str):
        player = await self._load_owned_player(interaction, player_id)
        if player is None:
            return
        player_character = self._player_character(player)
        embed = self._build_section_embed(player, player_character, section_key)
        view = PlayerCustomizationSectionView(self, int(player_id), section_key)
        await self._edit_message(interaction, embed=embed, view=view)

    async def show_randomize_confirm(self, interaction: discord.Interaction, player_id: int):
        player = await self._load_owned_player(interaction, player_id)
        if player is None:
            return
        player_character = self._player_character(player)
        embed = self._build_randomize_embed(player_character)
        view = PlayerCustomizationRandomizeView(self, int(player_id))
        await self._edit_message(interaction, embed=embed, view=view)

    async def confirm_randomize(self, interaction: discord.Interaction, player_id: int):
        player = await self._load_owned_player(interaction, player_id)
        if player is None:
            return
        self.player_service.randomize_player_character(player, preferred_name=self._display_name(interaction))
        refreshed_player = self.player_service.get_player_sync(int(player_id)) or player
        embed = self._build_home_embed(refreshed_player, self._player_character(refreshed_player))
        view = PlayerCustomizationHomeView(self, int(player_id))
        await self._edit_message(interaction, embed=embed, view=view)

    async def return_to_menu(self, interaction: discord.Interaction, player_id: int, menu_name: str):
        player = await self._load_owned_player(interaction, player_id)
        if player is None:
            return
        await self._render_menu(interaction, player, menu_name)

    async def open_field_modal(self, interaction: discord.Interaction, player_id: int, section_key: str, field_key: str):
        player = await self._load_owned_player(interaction, player_id)
        if player is None:
            return
        if field_key not in FIELD_SPECS:
            await interaction.response.send_message("That field is unavailable.", ephemeral=True)
            return
        await interaction.response.send_modal(PlayerCharacterFieldModal(self, player_id, section_key, field_key))

    async def submit_field_edit(
        self,
        interaction: discord.Interaction,
        player_id: int,
        section_key: str,
        field_key: str,
        raw_value: str,
    ):
        player = await self._load_owned_player(interaction, player_id)
        if player is None:
            return
        player_character = self._player_character(player)
        coerced = self._coerce_field_input(player, field_key, raw_value)
        self._set_field_value(player_character, field_key, coerced)
        self.player_service.persist_player(player)
        if not interaction.response.is_done():
            await interaction.response.defer()
        await self.show_section(interaction, player_id, section_key)
