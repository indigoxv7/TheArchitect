from __future__ import annotations

from dataclasses import dataclass

import discord

from src.domain.main_character import HobbyInterestLevel
from src.services.menu_runtime.interfaces import OriginalMessage


@dataclass(frozen=True)
class PlayerCharacterFieldSpec:
    key: str
    label: str
    container: str
    attr: str
    kind: str = "text"
    multiline: bool = False


FIELD_SPECS: dict[str, PlayerCharacterFieldSpec] = {
    "name": PlayerCharacterFieldSpec("name", "Name", "character", "name"),
    "description": PlayerCharacterFieldSpec("description", "Description", "character", "description", multiline=True),
    "portraitURL": PlayerCharacterFieldSpec("portraitURL", "Portrait URL", "character", "portraitURL"),
    "footerImageURL": PlayerCharacterFieldSpec("footerImageURL", "Footer Image URL", "character", "footerImageURL"),
    "age": PlayerCharacterFieldSpec("age", "Age", "characterInfo", "age", kind="int"),
    "birthday": PlayerCharacterFieldSpec("birthday", "Birthday", "characterInfo", "birthday"),
    "sex": PlayerCharacterFieldSpec("sex", "Sex", "characterInfo", "sex"),
    "height": PlayerCharacterFieldSpec("height", "Height", "characterInfo", "height"),
    "build": PlayerCharacterFieldSpec("build", "Build", "characterInfo", "build"),
    "skinTone": PlayerCharacterFieldSpec("skinTone", "Skin Tone", "characterInfo", "skinTone"),
    "hairColor": PlayerCharacterFieldSpec("hairColor", "Hair Color", "characterInfo", "hairColor"),
    "eyeColor": PlayerCharacterFieldSpec("eyeColor", "Eye Color", "characterInfo", "eyeColor"),
    "distinguishingMarks": PlayerCharacterFieldSpec(
        "distinguishingMarks", "Distinguishing Marks", "characterInfo", "distinguishingMarks", multiline=True
    ),
    "distinguishingMarksLocation": PlayerCharacterFieldSpec(
        "distinguishingMarksLocation", "Marks Location", "characterInfo", "distinguishingMarksLocation"
    ),
    "background": PlayerCharacterFieldSpec("background", "Background", "characterInfo", "background", multiline=True),
    "occupation": PlayerCharacterFieldSpec("occupation", "Occupation", "characterInfo", "occupation"),
    "job": PlayerCharacterFieldSpec("job", "Job", "characterInfo", "job"),
    "personalityType": PlayerCharacterFieldSpec(
        "personalityType", "Personality Type", "characterInfo", "personalityType"
    ),
    "coreValue": PlayerCharacterFieldSpec("coreValue", "Core Value", "characterInfo", "coreValue"),
    "strength": PlayerCharacterFieldSpec("strength", "Strength", "characterInfo", "strength", multiline=True),
    "flaw": PlayerCharacterFieldSpec("flaw", "Flaw", "characterInfo", "flaw", multiline=True),
    "socialStyle": PlayerCharacterFieldSpec("socialStyle", "Social Style", "characterInfo", "socialStyle"),
    "speechStyle": PlayerCharacterFieldSpec("speechStyle", "Speech Style", "characterInfo", "speechStyle"),
    "goal": PlayerCharacterFieldSpec("goal", "Goal", "characterInfo", "goal", multiline=True),
    "secret": PlayerCharacterFieldSpec("secret", "Secret", "characterInfo", "secret", multiline=True),
    "emotionalTrigger": PlayerCharacterFieldSpec(
        "emotionalTrigger", "Emotional Trigger", "characterInfo", "emotionalTrigger", multiline=True
    ),
    "copingHabit": PlayerCharacterFieldSpec("copingHabit", "Coping Habit", "characterInfo", "copingHabit"),
    "hobbies": PlayerCharacterFieldSpec("hobbies", "Hobbies", "character", "hobbies", kind="hobbies", multiline=True),
}

SECTION_ORDER = [
    "general",
    "identity",
    "appearance",
    "background",
    "personality_a",
    "personality_b",
    "hobbies",
]

SECTION_TITLES = {
    "general": "General",
    "identity": "Identity",
    "appearance": "Appearance",
    "background": "Background",
    "personality_a": "Personality I",
    "personality_b": "Personality II",
    "hobbies": "Hobbies",
}

SECTION_FIELDS = {
    "general": ["name", "description", "portraitURL", "footerImageURL"],
    "identity": ["age", "birthday", "sex", "height", "build"],
    "appearance": ["skinTone", "hairColor", "eyeColor", "distinguishingMarks", "distinguishingMarksLocation"],
    "background": ["background", "occupation", "job"],
    "personality_a": ["personalityType", "coreValue", "strength", "flaw", "socialStyle"],
    "personality_b": ["speechStyle", "goal", "secret", "emotionalTrigger", "copingHabit"],
    "hobbies": ["hobbies"],
}


class PlayerCharacterFieldModal(discord.ui.Modal):
    def __init__(self, runtime, player_id: int, section_key: str, field_key: str):
        spec = FIELD_SPECS[field_key]
        super().__init__(title=f"Edit {spec.label}")
        self.runtime = runtime
        self.player_id = int(player_id)
        self.section_key = str(section_key or "general")
        self.field_key = str(field_key or "")
        current_value = runtime.current_field_text(self.player_id, field_key)
        self.value = discord.ui.TextInput(
            label=spec.label,
            style=discord.TextStyle.paragraph if spec.multiline else discord.TextStyle.short,
            required=False,
            max_length=4000,
            default=current_value[:4000],
        )
        self.add_item(self.value)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await self.runtime.submit_field_edit(
                interaction,
                self.player_id,
                self.section_key,
                self.field_key,
                str(self.value.value or ""),
            )
        except Exception as exc:
            if interaction.response.is_done():
                await interaction.followup.send(f"Failed to update field: {exc}", ephemeral=True)
            else:
                await interaction.response.send_message(f"Failed to update field: {exc}", ephemeral=True)


class PlayerCustomizationHomeView(discord.ui.View):
    def __init__(self, runtime, player_id: int):
        super().__init__(timeout=86400)
        self.add_item(PlayerCharacterReturnMenuButton(runtime, player_id, menu_name="HowToPlayMenu", row=0))
        row = 1
        for index, section_key in enumerate(SECTION_ORDER):
            self.add_item(PlayerCharacterSectionButton(runtime, player_id, section_key, row=row))
            if (index + 1) % 2 == 0:
                row += 1
        self.add_item(PlayerCharacterRandomizeButton(runtime, player_id, row=4))


class PlayerCustomizationSectionView(discord.ui.View):
    def __init__(self, runtime, player_id: int, section_key: str):
        super().__init__(timeout=86400)
        self.add_item(PlayerCharacterBackHomeButton(runtime, player_id, row=0))
        self.add_item(PlayerCharacterReturnMenuButton(runtime, player_id, menu_name="HowToPlayMenu", row=0))
        row = 1
        for field_key in SECTION_FIELDS.get(section_key, []):
            self.add_item(PlayerCharacterFieldButton(runtime, player_id, section_key, field_key, row=row))
            row = 1 if row >= 4 else row + 1


class PlayerCustomizationRandomizeView(discord.ui.View):
    def __init__(self, runtime, player_id: int):
        super().__init__(timeout=86400)
        self.add_item(PlayerCharacterBackHomeButton(runtime, player_id, row=0))
        self.add_item(PlayerCharacterConfirmRandomizeButton(runtime, player_id, row=0))


class PlayerCharacterSectionButton(discord.ui.Button):
    def __init__(self, runtime, player_id: int, section_key: str, row: int = 1):
        super().__init__(label=SECTION_TITLES.get(section_key, section_key.title())[:80], style=discord.ButtonStyle.secondary, row=row)
        self.runtime = runtime
        self.player_id = int(player_id)
        self.section_key = str(section_key or "general")

    async def callback(self, interaction: discord.Interaction):
        await self.runtime.show_section(interaction, self.player_id, self.section_key)


class PlayerCharacterFieldButton(discord.ui.Button):
    def __init__(self, runtime, player_id: int, section_key: str, field_key: str, row: int = 1):
        spec = FIELD_SPECS[field_key]
        super().__init__(label=f"Edit {spec.label}"[:80], style=discord.ButtonStyle.primary, row=row)
        self.runtime = runtime
        self.player_id = int(player_id)
        self.section_key = str(section_key or "general")
        self.field_key = str(field_key or "")

    async def callback(self, interaction: discord.Interaction):
        await self.runtime.open_field_modal(interaction, self.player_id, self.section_key, self.field_key)


class PlayerCharacterRandomizeButton(discord.ui.Button):
    def __init__(self, runtime, player_id: int, row: int = 4):
        super().__init__(label="Randomize", style=discord.ButtonStyle.danger, row=row)
        self.runtime = runtime
        self.player_id = int(player_id)

    async def callback(self, interaction: discord.Interaction):
        await self.runtime.show_randomize_confirm(interaction, self.player_id)


class PlayerCharacterConfirmRandomizeButton(discord.ui.Button):
    def __init__(self, runtime, player_id: int, row: int = 0):
        super().__init__(label="Confirm Randomize", style=discord.ButtonStyle.danger, row=row)
        self.runtime = runtime
        self.player_id = int(player_id)

    async def callback(self, interaction: discord.Interaction):
        await self.runtime.confirm_randomize(interaction, self.player_id)


class PlayerCharacterBackHomeButton(discord.ui.Button):
    def __init__(self, runtime, player_id: int, row: int = 0):
        super().__init__(label="Customization Home", style=discord.ButtonStyle.secondary, row=row)
        self.runtime = runtime
        self.player_id = int(player_id)

    async def callback(self, interaction: discord.Interaction):
        await self.runtime.open_customization(interaction, self.player_id)


class PlayerCharacterReturnMenuButton(discord.ui.Button):
    def __init__(self, runtime, player_id: int, menu_name: str, row: int = 0):
        super().__init__(label="Back", style=discord.ButtonStyle.secondary, row=row)
        self.runtime = runtime
        self.player_id = int(player_id)
        self.menu_name = str(menu_name or "HowToPlayMenu")

    async def callback(self, interaction: discord.Interaction):
        await self.runtime.return_to_menu(interaction, self.player_id, self.menu_name)
