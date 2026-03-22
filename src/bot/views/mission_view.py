from __future__ import annotations

import discord

from src.domain.mission import MissionRunStatus


class MissionMenuView(discord.ui.View):
    def __init__(self, runtime, player_id: int, player, page: int = 0):
        super().__init__(timeout=86400)
        self.runtime = runtime
        self.player_id = int(player_id)
        available = runtime.list_available_missions(player)
        current_items, page_index, total_pages = runtime._paginate(available, page, runtime.MISSION_BUTTONS_PER_PAGE)
        self.page_index = page_index
        self.total_pages = total_pages

        active_mission = runtime.get_active_mission(player_id)
        if active_mission is not None:
            self.add_item(ResumeMissionButton(runtime, player_id, row=0))

        row = 1
        for entry in current_items:
            self.add_item(MissionChoiceButton(runtime, player_id, entry, row=row))
            row = 1 if row >= 4 else row + 1

        if total_pages > 1:
            self.add_item(PageButton(runtime, player_id, page_index - 1, "Prev", mode="menu", row=4, disabled=page_index <= 0))
            self.add_item(PageButton(runtime, player_id, page_index + 1, "Next", mode="menu", row=4, disabled=page_index >= total_pages - 1))


class MissionPreparationView(discord.ui.View):
    def __init__(self, runtime, player_id: int, mission, draft, page: int = 0):
        super().__init__(timeout=86400)
        self.runtime = runtime
        self.player_id = int(player_id)
        characters = list(getattr(runtime.player_service.get_player_sync(player_id), "characters", []) or [])
        current_items, page_index, total_pages = runtime._paginate(characters, page, runtime.CHARACTER_BUTTONS_PER_PAGE)
        self.add_item(BackToMissionMenuButton(runtime, player_id, row=0))
        self.add_item(StartMissionButton(runtime, player_id, row=0, disabled=not bool(draft.selectedCharacterInstanceIds)))

        row = 1
        for character in current_items:
            self.add_item(CharacterChoiceButton(runtime, player_id, character, row=row))
            row = 1 if row >= 4 else row + 1

        if total_pages > 1:
            self.add_item(PageButton(runtime, player_id, page_index - 1, "Prev", mode="prep", row=4, disabled=page_index <= 0))
            self.add_item(PageButton(runtime, player_id, page_index + 1, "Next", mode="prep", row=4, disabled=page_index >= total_pages - 1))


class MissionCharacterSummaryView(discord.ui.View):
    def __init__(self, runtime, player_id: int, mission_id: str, character_instance_id: str, selected: bool):
        super().__init__(timeout=86400)
        self.add_item(BackToPreparationButton(runtime, player_id, row=0))
        self.add_item(ToggleCharacterButton(runtime, player_id, character_instance_id, selected=selected, row=0))


class MissionActiveView(discord.ui.View):
    def __init__(self, runtime, player_id: int, state, page: int = 0):
        super().__init__(timeout=86400)
        self.runtime = runtime
        self.player_id = int(player_id)
        accessible = runtime._accessible_nodes_with_labels(state)
        current_items, page_index, total_pages = runtime._paginate(accessible, page, runtime.MOVE_BUTTONS_PER_PAGE)
        self.add_item(BackToMissionMenuButton(runtime, player_id, row=0))
        row = 1
        for node_id, label in current_items:
            self.add_item(MoveButton(runtime, player_id, node_id, label, row=row))
            row = 1 if row >= 4 else row + 1
        if total_pages > 1:
            self.add_item(PageButton(runtime, player_id, page_index - 1, "Prev", mode="active", row=4, disabled=page_index <= 0))
            self.add_item(PageButton(runtime, player_id, page_index + 1, "Next", mode="active", row=4, disabled=page_index >= total_pages - 1))


class MissionResultView(discord.ui.View):
    def __init__(self, runtime, player_id: int, status: MissionRunStatus, force_single_button: bool = False):
        super().__init__(timeout=86400)
        label = "Return to Mission Menu"
        if force_single_button:
            self.add_item(AcknowledgeMissionResultButton(runtime, player_id, label=label, row=0))
        else:
            self.add_item(AcknowledgeMissionResultButton(runtime, player_id, label=label, row=0))


class MissionNodeEventView(discord.ui.View):
    def __init__(self, runtime, player_id: int):
        super().__init__(timeout=86400)
        self.add_item(ContinueNodeEventButton(runtime, player_id, row=0))


class MissionChoiceButton(discord.ui.Button):
    def __init__(self, runtime, player_id: int, entry: dict[str, object], row: int = 1):
        mission = entry["mission"]
        super().__init__(label=str(getattr(mission, "name", "Mission"))[:80], style=discord.ButtonStyle.primary, row=row)
        self.runtime = runtime
        self.player_id = int(player_id)
        self.mission_id = str(getattr(mission, "missionId", "") or "")
        self.campaign_ids = list(entry.get("campaignIds", []) or [])

    async def callback(self, interaction: discord.Interaction):
        await self.runtime.open_preparation(interaction, self.player_id, self.mission_id, campaign_ids=self.campaign_ids)


class ResumeMissionButton(discord.ui.Button):
    def __init__(self, runtime, player_id: int, row: int = 0):
        super().__init__(label="Resume Active Mission", style=discord.ButtonStyle.success, row=row)
        self.runtime = runtime
        self.player_id = int(player_id)

    async def callback(self, interaction: discord.Interaction):
        await self.runtime.resume_active_mission(interaction, self.player_id)


class CharacterChoiceButton(discord.ui.Button):
    def __init__(self, runtime, player_id: int, character, row: int = 1):
        label = str(getattr(character, "name", "Character") or "Character")
        super().__init__(label=label[:80], style=discord.ButtonStyle.secondary, row=row)
        self.runtime = runtime
        self.player_id = int(player_id)
        self.character_instance_id = str(getattr(character, "playerInstanceId", "") or getattr(character, "name", "") or "")

    async def callback(self, interaction: discord.Interaction):
        await self.runtime.show_character_summary(interaction, self.player_id, self.character_instance_id)


class ToggleCharacterButton(discord.ui.Button):
    def __init__(self, runtime, player_id: int, character_instance_id: str, selected: bool, row: int = 0):
        label = "Remove from Mission" if selected else "Add to Mission"
        style = discord.ButtonStyle.danger if selected else discord.ButtonStyle.success
        super().__init__(label=label, style=style, row=row)
        self.runtime = runtime
        self.player_id = int(player_id)
        self.character_instance_id = str(character_instance_id or "")

    async def callback(self, interaction: discord.Interaction):
        await self.runtime.toggle_character_selection(interaction, self.player_id, self.character_instance_id)


class StartMissionButton(discord.ui.Button):
    def __init__(self, runtime, player_id: int, row: int = 0, disabled: bool = False):
        super().__init__(label="Start Mission", style=discord.ButtonStyle.success, row=row, disabled=disabled)
        self.runtime = runtime
        self.player_id = int(player_id)

    async def callback(self, interaction: discord.Interaction):
        await self.runtime.start_mission(interaction, self.player_id)


class MoveButton(discord.ui.Button):
    def __init__(self, runtime, player_id: int, node_id: int, label_text: str, row: int = 1):
        super().__init__(label=label_text, style=discord.ButtonStyle.primary, row=row)
        self.runtime = runtime
        self.player_id = int(player_id)
        self.node_id = int(node_id)

    async def callback(self, interaction: discord.Interaction):
        await self.runtime.move_to_node(interaction, self.player_id, self.node_id)


class BackToMissionMenuButton(discord.ui.Button):
    def __init__(self, runtime, player_id: int, row: int = 0):
        super().__init__(label="Mission Menu", style=discord.ButtonStyle.secondary, row=row)
        self.runtime = runtime
        self.player_id = int(player_id)

    async def callback(self, interaction: discord.Interaction):
        await self.runtime.show_mission_menu(interaction, self.player_id)


class BackToPreparationButton(discord.ui.Button):
    def __init__(self, runtime, player_id: int, row: int = 0):
        super().__init__(label="Back", style=discord.ButtonStyle.secondary, row=row)
        self.runtime = runtime
        self.player_id = int(player_id)

    async def callback(self, interaction: discord.Interaction):
        await self.runtime.preparation_page(interaction, self.player_id, 0)


class AcknowledgeMissionResultButton(discord.ui.Button):
    def __init__(self, runtime, player_id: int, label: str, row: int = 0):
        super().__init__(label=label, style=discord.ButtonStyle.primary, row=row)
        self.runtime = runtime
        self.player_id = int(player_id)

    async def callback(self, interaction: discord.Interaction):
        await self.runtime.acknowledge_result(interaction, self.player_id)


class ContinueNodeEventButton(discord.ui.Button):
    def __init__(self, runtime, player_id: int, row: int = 0):
        super().__init__(label="Continue", style=discord.ButtonStyle.primary, row=row)
        self.runtime = runtime
        self.player_id = int(player_id)

    async def callback(self, interaction: discord.Interaction):
        await self.runtime.advance_node_event(interaction, self.player_id)


class PageButton(discord.ui.Button):
    def __init__(self, runtime, player_id: int, target_page: int, label: str, mode: str, row: int = 4, disabled: bool = False):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=row, disabled=disabled)
        self.runtime = runtime
        self.player_id = int(player_id)
        self.target_page = int(target_page)
        self.mode = str(mode or "menu")

    async def callback(self, interaction: discord.Interaction):
        if self.mode == "prep":
            await self.runtime.preparation_page(interaction, self.player_id, self.target_page)
        elif self.mode == "active":
            await self.runtime.active_mission_page(interaction, self.player_id, self.target_page)
        else:
            await self.runtime.mission_menu_page(interaction, self.player_id, self.target_page)
