from __future__ import annotations

import io
import random
from dataclasses import dataclass
from typing import Any

import discord

from src.bot.views.mission_view import (
    MissionActiveView,
    MissionCharacterSummaryView,
    MissionMenuView,
    MissionNodeEventView,
    MissionPreparationView,
    MissionResultView,
)
from src.domain.Allegiance import AllegianceRelationship
from src.domain.character_io import character_from_state, character_to_state
from src.domain.combat import BattleOutcome, EncounterType
from src.domain.mission import (
    MissionNodeEvent,
    MissionNodeEventType,
    MissionNodeState,
    MissionNodeUnitState,
    MissionObjectiveStatus,
    MissionPartyState,
    MissionRunState,
    MissionRunStatus,
    MissionStatistics,
)
from src.services.mission_map import (
    MissionMapOverlay,
    build_map_settings_from_range,
    generate_all_map_features,
    mission_map_from_dict,
    mission_map_to_dict,
    render_mission_map_image,
)
from src.services.mission_map.generator import generate_mission_map
from src.services.nano_display_service import format_nano


@dataclass
class MissionPreparationDraft:
    missionId: str
    campaignIds: list[str]
    selectedCharacterInstanceIds: list[str]


class MissionRuntimeService:
    PLAYER_PARTY_ALLEGIANCE_ID = "PlayerParty"
    MOVE_HOURS_PER_STEP = 0.25
    MISSION_IMAGE_FILENAME = "mission_map.png"
    CHARACTER_BUTTONS_PER_PAGE = 6
    MISSION_BUTTONS_PER_PAGE = 6
    MOVE_BUTTONS_PER_PAGE = 6

    def __init__(
        self,
        context,
        player_service,
        character_service,
        mission_service,
        campaign_service,
        allegiance_service,
        mission_unit_populator,
        active_mission_store,
        battle_runtime_service=None,
    ):
        self.context = context
        self.player_service = player_service
        self.character_service = character_service
        self.mission_service = mission_service
        self.campaign_service = campaign_service
        self.allegiance_service = allegiance_service
        self.mission_unit_populator = mission_unit_populator
        self.store = active_mission_store
        self.battle_runtime_service = battle_runtime_service
        self._preparation_drafts: dict[int, MissionPreparationDraft] = {}

    def set_battle_runtime_service(self, battle_runtime_service):
        self.battle_runtime_service = battle_runtime_service

    def initialize(self):
        self.store.ensure_directory()
        if not hasattr(self.context, "active_missions"):
            self.context.active_missions = {}

    def get_active_mission(self, player_id: int) -> MissionRunState | None:
        player_id = int(player_id)
        cached = getattr(self.context, "active_missions", {}).get(player_id)
        if isinstance(cached, MissionRunState):
            return cached
        payload = self.store.load_mission_file(player_id)
        if not isinstance(payload, dict):
            return None
        state_payload = payload.get("mission_run_state", payload)
        try:
            state = MissionRunState.from_dict(state_payload)
        except Exception:
            return None
        self.context.active_missions[player_id] = state
        return state

    def save_active_mission(self, state: MissionRunState):
        self.store.save_mission_file(
            state.playerId,
            {
                "format_version": 1,
                "mission_run_state": state.to_dict(),
            },
        )
        self.context.active_missions[int(state.playerId)] = state

    def clear_active_mission(self, player_id: int):
        player_id = int(player_id)
        self.store.delete_mission_file(player_id)
        getattr(self.context, "active_missions", {}).pop(player_id, None)

    def list_available_missions(self, player) -> list[dict[str, object]]:
        return self.campaign_service.list_unlocked_missions(player)

    def _get_preparation_draft(self, player_id: int) -> MissionPreparationDraft | None:
        return self._preparation_drafts.get(int(player_id))

    def _set_preparation_draft(self, player_id: int, draft: MissionPreparationDraft):
        self._preparation_drafts[int(player_id)] = draft

    def _clear_preparation_draft(self, player_id: int):
        self._preparation_drafts.pop(int(player_id), None)

    @staticmethod
    def _paginate(items: list[Any], page: int, per_page: int) -> tuple[list[Any], int, int]:
        if per_page <= 0:
            return items, 0, 1
        total_pages = max(1, ((len(items) - 1) // per_page) + 1) if items else 1
        page_index = max(0, min(int(page or 0), total_pages - 1))
        start = page_index * per_page
        end = start + per_page
        return items[start:end], page_index, total_pages

    def _mission_template(self, state: MissionRunState):
        return self.mission_service.get_mission_by_id(state.missionId) or self.mission_service.get_mission(
            state.missionId
        )

    @staticmethod
    def _character_identity(character) -> str:
        return str(getattr(character, "playerInstanceId", "") or getattr(character, "name", "") or "")

    def _player_character_by_id(self, player, character_instance_id: str):
        target = str(character_instance_id or "").strip()
        if not target:
            return None
        for character in getattr(player, "characters", []) or []:
            if self._character_identity(character) == target:
                return character
        return None

    def _resolve_relation(self, allegiance_id: str) -> AllegianceRelationship:
        return self.allegiance_service.get_relationship(str(allegiance_id or ""), self.PLAYER_PARTY_ALLEGIANCE_ID)

    def _is_hostile(self, allegiance_id: str) -> bool:
        return self._resolve_relation(allegiance_id) in {
            AllegianceRelationship.ENEMIES,
            AllegianceRelationship.HATED_ENEMIES,
        }

    def _is_ally(self, allegiance_id: str) -> bool:
        return self._resolve_relation(allegiance_id) in {
            AllegianceRelationship.DEFENSIVE_ALLIES,
            AllegianceRelationship.FULL_ALLIES,
        }

    @staticmethod
    def _movement_label(index: int) -> str:
        label = ""
        value = int(index)
        while True:
            value, remainder = divmod(value, 26)
            label = chr(ord("A") + remainder) + label
            if value == 0:
                break
            value -= 1
        return label

    def _mission_map(self, state: MissionRunState):
        return mission_map_from_dict(state.mapState)

    def _accessible_nodes_with_labels(self, state: MissionRunState) -> list[tuple[int, str]]:
        mission_map = self._mission_map(state)
        if state.currentNodeId is None:
            return []
        return [
            (int(node_id), self._movement_label(index))
            for index, node_id in enumerate(mission_map.neighbors(int(state.currentNodeId)))
        ]

    def _build_overlay(self, state: MissionRunState) -> MissionMapOverlay:
        overlay = MissionMapOverlay()
        for node_state in state.nodeStates:
            living_units = node_state.living_unit_states()
            if living_units:
                overlay.unitsByNode[int(node_state.nodeId)] = list(living_units)
            if not node_state.treasureCollected and int(node_state.nanoAmount or 0) > 0:
                overlay.nanoByNode[int(node_state.nodeId)] = int(node_state.nanoAmount)
            if not node_state.clueResolved and node_state.clueTargetNodeId is not None:
                overlay.clueTargetNodeByNode[int(node_state.nodeId)] = int(node_state.clueTargetNodeId)
        return overlay

    def _map_attachment(self, state: MissionRunState) -> discord.File:
        mission_map = self._mission_map(state)
        accessible_labels = {node_id: label for node_id, label in self._accessible_nodes_with_labels(state)}
        visible_nodes = set(state.visitedNodeIds) | set(state.revealedNodeIds) | set(accessible_labels.keys())
        if state.currentNodeId is not None:
            visible_nodes.add(int(state.currentNodeId))
        image = render_mission_map_image(
            mission_map,
            overlay=self._build_overlay(state),
            visited_node_ids=set(state.visitedNodeIds),
            revealed_node_ids=visible_nodes,
            current_node_id=state.currentNodeId,
            accessible_labels_by_node=accessible_labels,
            visible_feature_node_ids=visible_nodes,
        )
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        return discord.File(buffer, filename=self.MISSION_IMAGE_FILENAME)
    def _summary_for_selected_party(self, player, selected_ids: list[str]) -> str:
        selected_set = {str(entry or "").strip() for entry in selected_ids if str(entry or "").strip()}
        if not selected_set:
            return "No characters selected yet."
        lines = []
        for character in getattr(player, "characters", []) or []:
            if self._character_identity(character) not in selected_set:
                continue
            health = float(getattr(character, "health", 0.0) or 0.0)
            max_health = float(getattr(character, "GetMaxHealth", lambda: health)() or max(1.0, health))
            lines.append(
                f"- {getattr(character, 'name', 'Character')} [{self._character_identity(character)}] | "
                f"Lv {int(getattr(character, 'level', 0) or 0)} | {health:.0f}/{max_health:.0f}"
            )
        return "\n".join(lines) if lines else "No characters selected yet."

    def _build_mission_menu_embed(self, player, active_mission: MissionRunState | None) -> discord.Embed:
        available = self.list_available_missions(player)
        embed = discord.Embed(title="Mission Menu")
        lines = []
        if active_mission is not None:
            lines.append(f"Active mission: {active_mission.missionName} ({active_mission.status.value})")
        if available:
            lines.append(f"Unlocked missions: {len(available)}")
        else:
            lines.append("No missions are currently unlocked.")
        embed.description = "\n".join(lines)
        mission_lines = []
        for entry in available[:15]:
            mission = entry["mission"]
            mission_lines.append(f"- {mission.name} [{mission.missionId}] | {mission.objective.describe()}")
        if mission_lines:
            embed.add_field(name="Available Missions", value="\n".join(mission_lines), inline=False)
        if active_mission is not None:
            embed.add_field(
                name="Resume",
                value="Use the Resume Active Mission button to jump back into the current run.",
                inline=False,
            )
        return embed

    def _build_preparation_embed(self, player, mission, draft: MissionPreparationDraft) -> discord.Embed:
        embed = discord.Embed(title=f"Mission Preparation | {mission.name}")
        embed.description = mission.objective.describe()
        embed.add_field(
            name="Selected Party",
            value=self._summary_for_selected_party(player, draft.selectedCharacterInstanceIds),
            inline=False,
        )
        available_names = []
        for character in getattr(player, "characters", []) or []:
            available_names.append(
                f"- {getattr(character, 'name', 'Character')} [{self._character_identity(character)}] | "
                f"Lv {int(getattr(character, 'level', 0) or 0)}"
            )
        embed.add_field(
            name="Available Characters",
            value="\n".join(available_names[:15]) if available_names else "No characters available.",
            inline=False,
        )
        embed.set_footer(text="Select a character to view their summary and add or remove them from the mission.")
        return embed

    def _build_character_summary_embed(self, player, mission, character, selected: bool) -> discord.Embed:
        embed = discord.Embed(title=f"{mission.name} | {getattr(character, 'name', 'Character')}")
        overview = str(
            getattr(character, "GetCharacterOverviewText", lambda _nano: "No summary.")(
                getattr(player, "nano", 0)
            )
            or "No summary."
        )
        embed.description = overview
        portrait_url = str(getattr(character, "portraitURL", "") or "").strip()
        footer_image_url = str(getattr(character, "footerImageURL", "") or "").strip()
        if portrait_url:
            embed.set_thumbnail(url=portrait_url)
        if footer_image_url:
            embed.set_image(url=footer_image_url)
        embed.set_footer(text="Selected for mission." if selected else "Not selected for mission.")
        return embed

    def _current_node_summary(self, state: MissionRunState) -> str:
        if state.currentNodeId is None:
            return "No current node selected."
        node_state = state.get_node(state.currentNodeId)
        if node_state is None:
            return "This node has no special contents."

        hostile = 0
        allied = 0
        neutral = 0
        for unit in node_state.living_unit_states():
            if self._is_hostile(unit.allegianceId):
                hostile += 1
            elif self._is_ally(unit.allegianceId):
                allied += 1
            else:
                neutral += 1

        lines = [f"Node {int(state.currentNodeId)}"]
        if hostile:
            lines.append(f"- Hostile units: {hostile}")
        if allied:
            lines.append(f"- Allied units: {allied}")
        if neutral:
            lines.append(f"- Neutral units: {neutral}")
        if not node_state.treasureCollected and int(node_state.nanoAmount or 0) > 0:
            lines.append(f"- Nano cache: {format_nano(node_state.nanoAmount)}")
        if not node_state.clueResolved and node_state.clueTargetNodeId is not None:
            lines.append("- A clue is present here.")
        if len(lines) == 1:
            lines.append("- Quiet node.")
        return "\n".join(lines)

    def _append_node_event(
        self,
        state: MissionRunState,
        event_type: MissionNodeEventType,
        title: str,
        description: str,
    ):
        state.pendingNodeEvents.append(
            MissionNodeEvent(
                eventType=event_type,
                title=str(title or ""),
                description=str(description or ""),
            )
        )

    def _collect_node_events(self, player, state: MissionRunState, node_state: MissionNodeState) -> str:
        notes: list[str] = []
        if not node_state.treasureCollected and int(node_state.nanoAmount or 0) > 0:
            amount = int(node_state.nanoAmount or 0)
            player.nano = int(getattr(player, "nano", 0) or 0) + amount
            node_state.treasureCollected = True
            self.player_service.persist_player(player)
            self._append_node_event(
                state,
                MissionNodeEventType.TREASURE,
                "Treasure Found",
                f"You found {format_nano(amount)} nano at this location.",
            )

        if not node_state.clueResolved and node_state.clueTargetNodeId is not None:
            target_node_id = self._resolve_clue_target(state, int(node_state.nodeId), int(node_state.clueTargetNodeId))
            if target_node_id is not None:
                state.reveal_node(int(target_node_id))
                self._append_node_event(
                    state,
                    MissionNodeEventType.CLUE,
                    "Clue Found",
                    f"A clue points toward node {int(target_node_id)}.",
                )
            else:
                self._append_node_event(
                    state,
                    MissionNodeEventType.CLUE,
                    "Clue Found",
                    "You found a clue, but it does not reveal a new location.",
                )
            node_state.clueResolved = True

        non_hostile_units = [unit for unit in node_state.living_unit_states() if not self._is_hostile(unit.allegianceId)]
        if non_hostile_units:
            allied_count = sum(1 for unit in non_hostile_units if self._is_ally(unit.allegianceId))
            neutral_count = len(non_hostile_units) - allied_count
            if allied_count:
                notes.append(f"You find {allied_count} allied unit(s) here.")
            if neutral_count:
                notes.append(f"You spot {neutral_count} neutral unit(s) here.")
        return " ".join(notes)

    def _build_node_event_embed(self, state: MissionRunState) -> discord.Embed:
        event = state.pendingNodeEvents[0]
        mission = self._mission_template(state)
        mission_name = state.missionName or (mission.name if mission is not None else "Mission")
        embed = discord.Embed(title=f"{mission_name} | {event.title}", description=event.description or "")
        if state.currentNodeId is not None:
            embed.set_footer(text=f"Node {int(state.currentNodeId)}")
        return embed

    async def render_node_event(self, interaction: discord.Interaction, state: MissionRunState):
        if not state.pendingNodeEvents:
            await self.render_active_mission(interaction, state)
            return
        embed = self._build_node_event_embed(state)
        view = MissionNodeEventView(self, int(state.playerId))
        await self._edit_message(interaction, embed=embed, view=view)

    async def advance_node_event(self, interaction: discord.Interaction, player_id: int):
        state = self.get_active_mission(player_id)
        if state is None:
            await self.show_mission_menu(interaction, player_id)
            return
        if state.pendingNodeEvents:
            state.pendingNodeEvents.pop(0)
            self.save_active_mission(state)
        if state.pendingNodeEvents:
            await self.render_node_event(interaction, state)
            return
        if state.status in {MissionRunStatus.SUCCESS, MissionRunStatus.FAILED, MissionRunStatus.FORCED_RETREAT}:
            await self.render_mission_result(interaction, state)
            return
        await self.render_active_mission(interaction, state)

    def _build_active_mission_embed(self, player, state: MissionRunState) -> discord.Embed:
        mission = self._mission_template(state)
        title = state.missionName or (mission.name if mission is not None else "Mission")
        embed = discord.Embed(title=title)
        objective_text = mission.objective.describe() if mission is not None else "Unknown"
        embed.description = (
            f"Objective: {objective_text}\n"
            f"Status: {state.missionObjectiveStatus.value}\n"
            f"Current Node: {state.currentNodeId if state.currentNodeId is not None else 'Unknown'}"
        )
        stats = state.missionStatistics
        embed.add_field(
            name="Party",
            value=self._summary_for_selected_party(player, state.partyState.selectedCharacterInstanceIds),
            inline=False,
        )
        embed.add_field(
            name="Mission Stats",
            value=(
                f"Enemies Remaining: {stats.enemiesRemaining}/{stats.totalStartingEnemies}\n"
                f"Allies Remaining: {stats.alliesRemaining}/{stats.totalStartingAllies}\n"
                f"Hours in Mission: {float(stats.timeInsideMissionHours or 0.0):.2f}\n"
                f"Bosses Defeated: {stats.bossesDefeated}"
            ),
            inline=False,
        )
        embed.add_field(name="Current Node", value=self._current_node_summary(state), inline=False)
        if state.lastBattleSummary:
            embed.add_field(name="Latest Event", value=state.lastBattleSummary, inline=False)
        embed.set_image(url=f"attachment://{self.MISSION_IMAGE_FILENAME}")
        return embed

    def _record_completed_mission_count(self, state: MissionRunState, player=None):
        if state.missionCountRecorded:
            return
        if state.status not in {MissionRunStatus.SUCCESS, MissionRunStatus.FAILED, MissionRunStatus.FORCED_RETREAT}:
            return
        if player is None:
            player = self.player_service.get_player_sync(int(state.playerId))
        if player is None:
            return
        selected_ids = set(state.partyState.selectedCharacterInstanceIds)
        updated = False
        for character in getattr(player, "characters", []) or []:
            if self._character_identity(character) not in selected_ids:
                continue
            stats = getattr(character, "stats", None)
            if stats is None:
                continue
            stats.missionCount = int(getattr(stats, "missionCount", 0) or 0) + 1
            updated = True
        state.missionCountRecorded = True
        if updated:
            self.player_service.persist_player(player)

    def _build_result_embed(self, state: MissionRunState) -> discord.Embed:
        if state.status == MissionRunStatus.FORCED_RETREAT:
            title = "Mission Failed"
            description = "your squad was forced to retreat"
        elif state.status == MissionRunStatus.SUCCESS:
            title = "Mission Complete"
            description = state.resultSummary or "Mission success."
        else:
            title = "Mission Ended"
            description = state.resultSummary or state.status.value
        embed = discord.Embed(title=title, description=description)
        stats = state.missionStatistics
        embed.add_field(
            name="Summary",
            value=(
                f"Enemies Remaining: {stats.enemiesRemaining}/{stats.totalStartingEnemies}\n"
                f"Allies Remaining: {stats.alliesRemaining}/{stats.totalStartingAllies}\n"
                f"Hours in Mission: {float(stats.timeInsideMissionHours or 0.0):.2f}\n"
                f"Bosses Defeated: {stats.bossesDefeated}"
            ),
            inline=False,
        )
        return embed

    async def _edit_message(
        self,
        interaction: discord.Interaction,
        *,
        embed: discord.Embed,
        view: discord.ui.View,
        file: discord.File | None = None,
    ):
        kwargs = {"embed": embed, "view": view, "attachments": [file] if file is not None else []}
        if interaction.response.is_done():
            if interaction.message is not None:
                await interaction.message.edit(**kwargs)
            else:
                await interaction.followup.send(**kwargs, ephemeral=True)
        else:
            await interaction.response.edit_message(**kwargs)

    async def show_mission_menu(self, interaction: discord.Interaction, player_id: int, page: int = 0):
        player = await self.player_service.get_player(int(player_id))
        active_mission = self.get_active_mission(player_id)
        embed = self._build_mission_menu_embed(player, active_mission)
        view = MissionMenuView(self, int(player_id), player, page=page)
        await self._edit_message(interaction, embed=embed, view=view)

    async def mission_menu_page(self, interaction: discord.Interaction, player_id: int, page: int):
        await self.show_mission_menu(interaction, player_id, page=page)

    async def resume_active_mission(self, interaction: discord.Interaction, player_id: int):
        active_battle = None
        if self.battle_runtime_service is not None:
            active_battle = self.battle_runtime_service.battle_service.get_active_battle(player_id)
        if active_battle is not None and str(getattr(active_battle, "origin_type", "") or "") == "mission_node":
            await self.battle_runtime_service.render_battle(
                interaction, active_battle, note="Resumed active mission battle."
            )
            return
        state = self.get_active_mission(player_id)
        if state is None:
            await self.show_mission_menu(interaction, player_id)
            return
        if state.pendingNodeEvents:
            await self.render_node_event(interaction, state)
            return
        if state.status in {MissionRunStatus.SUCCESS, MissionRunStatus.FAILED, MissionRunStatus.FORCED_RETREAT}:
            await self.render_mission_result(interaction, state)
            return
        await self.render_active_mission(interaction, state)
    async def open_preparation(
        self,
        interaction: discord.Interaction,
        player_id: int,
        mission_id: str,
        campaign_ids: list[str] | None = None,
        page: int = 0,
    ):
        if self.get_active_mission(player_id) is not None:
            await interaction.response.send_message("Finish or resume your active mission first.", ephemeral=True)
            return
        player = await self.player_service.get_player(int(player_id))
        mission = self.mission_service.get_mission_by_id(mission_id)
        if mission is None:
            await interaction.response.send_message("That mission is no longer available.", ephemeral=True)
            return
        selected_ids = player.GetMissionPartyCharacterIds()
        draft = self._get_preparation_draft(player_id)
        if draft is None or draft.missionId != mission.missionId:
            draft = MissionPreparationDraft(
                missionId=mission.missionId,
                campaignIds=list(campaign_ids or []),
                selectedCharacterInstanceIds=list(selected_ids),
            )
            self._set_preparation_draft(player_id, draft)
        embed = self._build_preparation_embed(player, mission, draft)
        view = MissionPreparationView(self, int(player_id), mission, draft, page=page)
        await self._edit_message(interaction, embed=embed, view=view)

    async def preparation_page(self, interaction: discord.Interaction, player_id: int, page: int):
        draft = self._get_preparation_draft(player_id)
        if draft is None:
            await self.show_mission_menu(interaction, player_id)
            return
        await self.open_preparation(
            interaction,
            player_id,
            draft.missionId,
            campaign_ids=draft.campaignIds,
            page=page,
        )

    async def show_character_summary(self, interaction: discord.Interaction, player_id: int, character_instance_id: str):
        draft = self._get_preparation_draft(player_id)
        if draft is None:
            await self.show_mission_menu(interaction, player_id)
            return
        player = await self.player_service.get_player(int(player_id))
        mission = self.mission_service.get_mission_by_id(draft.missionId)
        character = self._player_character_by_id(player, character_instance_id)
        if mission is None or character is None:
            await interaction.response.send_message("Unable to open that character.", ephemeral=True)
            return
        selected = str(character_instance_id or "").strip() in set(draft.selectedCharacterInstanceIds)
        embed = self._build_character_summary_embed(player, mission, character, selected)
        view = MissionCharacterSummaryView(self, int(player_id), mission.missionId, character_instance_id, selected)
        await self._edit_message(interaction, embed=embed, view=view)

    async def toggle_character_selection(
        self,
        interaction: discord.Interaction,
        player_id: int,
        character_instance_id: str,
    ):
        draft = self._get_preparation_draft(player_id)
        if draft is None:
            await self.show_mission_menu(interaction, player_id)
            return
        target = str(character_instance_id or "").strip()
        if target in draft.selectedCharacterInstanceIds:
            draft.selectedCharacterInstanceIds = [entry for entry in draft.selectedCharacterInstanceIds if entry != target]
        else:
            draft.selectedCharacterInstanceIds.append(target)
        self._set_preparation_draft(player_id, draft)
        await self.show_character_summary(interaction, player_id, target)

    def _build_initial_statistics(self, node_states: list[MissionNodeState]) -> MissionStatistics:
        total_enemies = 0
        total_allies = 0
        unit_alive_states: dict[str, bool] = {}
        unit_distances: dict[str, float] = {}
        for node_state in node_states:
            for unit in node_state.unitStates:
                alive = not bool(unit.defeated)
                if self._is_hostile(unit.allegianceId):
                    total_enemies += 1
                elif self._is_ally(unit.allegianceId):
                    total_allies += 1
                unit_alive_states[unit.runtimeUnitId] = alive
                unit_distances[unit.runtimeUnitId] = 0.0
                if unit.unitId and unit.unitId not in unit_alive_states:
                    unit_alive_states[unit.unitId] = alive
        return MissionStatistics(
            totalStartingEnemies=total_enemies,
            totalStartingAllies=total_allies,
            enemiesRemaining=total_enemies,
            alliesRemaining=total_allies,
            unitAliveStates=unit_alive_states,
            unitDistancesMoved=unit_distances,
        )

    def _generate_state(self, player, mission, campaign_ids: list[str]) -> MissionRunState:
        seed = random.SystemRandom().randrange(0, 2**32)
        mission_map = generate_mission_map(build_map_settings_from_range(mission.mapGenerationRange, seed=seed))
        populated = self.mission_unit_populator.populate(mission, seed=seed)
        overlay = generate_all_map_features(mission_map, mission, populated, seed=seed)
        unit_metadata: dict[int, object] = {}
        for entry in populated.generatedUnits:
            unit_metadata[id(entry)] = entry
            character = getattr(entry, "character", None)
            if character is not None:
                unit_metadata[id(character)] = entry
        node_states: list[MissionNodeState] = []
        for node_id in sorted(mission_map.nodes_by_id.keys()):
            units = []
            for index, overlay_entry in enumerate(overlay.unitsByNode.get(node_id, []) or []):
                metadata = unit_metadata.get(id(overlay_entry))
                if metadata is None:
                    continue
                character = getattr(overlay_entry, "character", None)
                if character is None:
                    character = getattr(metadata, "character", None)
                if character is None:
                    character = overlay_entry
                runtime_unit_id = f"{metadata.allegianceId}_{metadata.unitId}_{int(node_id)}_{index}"
                units.append(
                    MissionNodeUnitState(
                        runtimeUnitId=runtime_unit_id,
                        allegianceId=str(metadata.allegianceId or ""),
                        unitId=str(metadata.unitId or ""),
                        unitLabel=str(metadata.unitLabel or ""),
                        characterState=character_to_state(character),
                        isBoss=bool(metadata.isBoss),
                        isElite=bool(metadata.isElite),
                        defeated=False,
                    )
                )
            node_states.append(
                MissionNodeState(
                    nodeId=int(node_id),
                    unitStates=units,
                    nanoAmount=int(overlay.nanoByNode.get(node_id, 0) or 0),
                    clueTargetNodeId=(
                        int(overlay.clueTargetNodeByNode[node_id])
                        if node_id in overlay.clueTargetNodeByNode
                        else None
                    ),
                )
            )

        state = MissionRunState(
            playerId=int(player.discordID),
            missionId=str(mission.missionId or ""),
            missionName=str(mission.name or "Mission"),
            missionTemplateState=mission.to_dict(),
            mapState=mission_map_to_dict(mission_map),
            partyState=MissionPartyState(selectedCharacterInstanceIds=player.GetMissionPartyCharacterIds()),
            status=MissionRunStatus.ACTIVE,
            currentNodeId=int(mission_map.start_node_id),
            visitedNodeIds=[int(mission_map.start_node_id)],
            revealedNodeIds=[int(mission_map.start_node_id)],
            nodeStates=node_states,
            missionStatistics=self._build_initial_statistics(node_states),
            missionObjectiveStatus=MissionObjectiveStatus.IN_PROGRESS,
            campaignIds=list(campaign_ids or []),
        )
        self._update_ally_progress_metrics(state)
        self._refresh_objective_status(state)
        return state

    def _distance_from_start(self, state: MissionRunState, node_id: int) -> int:
        mission_map = self._mission_map(state)
        start = int(mission_map.start_node_id)
        target = int(node_id)
        frontier = [(start, 0)]
        visited = {start}
        while frontier:
            current_node_id, distance = frontier.pop(0)
            if current_node_id == target:
                return distance
            for neighbor_id in mission_map.neighbors(current_node_id):
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)
                frontier.append((int(neighbor_id), distance + 1))
        return 0

    def _update_ally_progress_metrics(self, state: MissionRunState):
        if state.currentNodeId is None:
            return
        current_distance = float(self._distance_from_start(state, state.currentNodeId))
        state.missionStatistics.allyDistanceMovedFromStartingPoint = max(
            float(state.missionStatistics.allyDistanceMovedFromStartingPoint or 0.0),
            current_distance,
        )
        node_state = state.get_node(state.currentNodeId)
        if node_state is None:
            return
        for unit in node_state.living_unit_states():
            if not self._is_ally(unit.allegianceId):
                continue
            state.missionStatistics.unitDistancesMoved[unit.runtimeUnitId] = max(
                float(state.missionStatistics.unitDistancesMoved.get(unit.runtimeUnitId, 0.0) or 0.0),
                current_distance,
            )
            state.missionStatistics.unitAliveStates[unit.runtimeUnitId] = True
            if unit.unitId:
                state.missionStatistics.unitAliveStates[unit.unitId] = True

    def _recompute_counts(self, state: MissionRunState):
        enemies_remaining = 0
        allies_remaining = 0
        template_alive: dict[str, bool] = {}
        for node_state in state.nodeStates:
            for unit in node_state.unitStates:
                alive = not bool(unit.defeated)
                state.missionStatistics.unitAliveStates[unit.runtimeUnitId] = alive
                if unit.unitId:
                    template_alive[unit.unitId] = template_alive.get(unit.unitId, False) or alive
                if not alive:
                    continue
                if self._is_hostile(unit.allegianceId):
                    enemies_remaining += 1
                elif self._is_ally(unit.allegianceId):
                    allies_remaining += 1
        for unit_id, alive in template_alive.items():
            state.missionStatistics.unitAliveStates[unit_id] = alive
        state.missionStatistics.enemiesRemaining = enemies_remaining
        state.missionStatistics.alliesRemaining = allies_remaining

    def _mission_complete_flag(self, state: MissionRunState) -> bool:
        mission_map = self._mission_map(state)
        return len(set(state.visitedNodeIds)) >= len(mission_map.nodes_by_id)

    def _refresh_objective_status(self, state: MissionRunState):
        mission = self._mission_template(state)
        if mission is None:
            return
        self._recompute_counts(state)
        state.missionObjectiveStatus = mission.evaluate_objective(
            state.missionStatistics,
            mission_complete=self._mission_complete_flag(state),
        )
        if state.status == MissionRunStatus.FORCED_RETREAT:
            state.resultSummary = state.resultSummary or "your squad was forced to retreat"
            return
        if state.missionObjectiveStatus == MissionObjectiveStatus.SUCCESS:
            state.status = MissionRunStatus.SUCCESS
            state.resultSummary = f"Mission success: {mission.objective.describe()}."
        elif state.missionObjectiveStatus == MissionObjectiveStatus.FAILURE:
            state.status = MissionRunStatus.FAILED
            state.resultSummary = f"Mission failed: {mission.objective.describe()}."
        elif self._mission_complete_flag(state):
            state.status = MissionRunStatus.FAILED
            state.resultSummary = "Mission ended without meeting its objective."
        elif state.status not in {MissionRunStatus.PREPARING, MissionRunStatus.ACTIVE}:
            state.status = MissionRunStatus.ACTIVE
    async def start_mission(self, interaction: discord.Interaction, player_id: int):
        draft = self._get_preparation_draft(player_id)
        if draft is None:
            await self.show_mission_menu(interaction, player_id)
            return
        mission = self.mission_service.get_mission_by_id(draft.missionId)
        if mission is None:
            await interaction.response.send_message("That mission is no longer available.", ephemeral=True)
            return
        if not draft.selectedCharacterInstanceIds:
            await interaction.response.send_message(
                "Select at least one character before starting the mission.",
                ephemeral=True,
            )
            return
        player = await self.player_service.get_player(int(player_id))
        selected = [
            entry for entry in draft.selectedCharacterInstanceIds if self._player_character_by_id(player, entry) is not None
        ]
        if not selected:
            await interaction.response.send_message(
                "Select at least one valid character before starting the mission.",
                ephemeral=True,
            )
            return
        player.SetMissionPartyCharacterIds(selected)
        self.player_service.persist_player(player)
        draft.selectedCharacterInstanceIds = list(player.GetMissionPartyCharacterIds())
        state = self._generate_state(player, mission, draft.campaignIds)
        state.partyState = MissionPartyState(selectedCharacterInstanceIds=list(draft.selectedCharacterInstanceIds))
        state.lastBattleSummary = ""
        self.save_active_mission(state)
        self._clear_preparation_draft(player_id)
        await self._enter_current_node(interaction, state)

    def _resolve_clue_target(self, state: MissionRunState, source_node_id: int, suggested_target_node_id: int) -> int | None:
        if suggested_target_node_id not in set(state.revealedNodeIds):
            target_state = state.get_node(suggested_target_node_id)
            if target_state is not None and target_state.living_unit_states():
                return int(suggested_target_node_id)
        mission_map = self._mission_map(state)
        distances = {int(source_node_id): 0}
        queue = [int(source_node_id)]
        while queue:
            node_id = queue.pop(0)
            for neighbor_id in mission_map.neighbors(node_id):
                if int(neighbor_id) in distances:
                    continue
                distances[int(neighbor_id)] = distances[node_id] + 1
                queue.append(int(neighbor_id))
        candidates = []
        for node_state in state.nodeStates:
            if int(node_state.nodeId) in set(state.revealedNodeIds):
                continue
            if not node_state.living_unit_states():
                continue
            if int(node_state.nodeId) not in distances:
                continue
            candidates.append((distances[int(node_state.nodeId)], int(node_state.nodeId)))
        if not candidates:
            return None
        candidates.sort()
        return int(candidates[0][1])

    async def _start_node_battle(
        self,
        interaction: discord.Interaction,
        player,
        state: MissionRunState,
        node_state: MissionNodeState,
        hostile_units: list[MissionNodeUnitState],
    ):
        if self.battle_runtime_service is None:
            await interaction.response.send_message("Battle runtime is unavailable.", ephemeral=True)
            return
        mission = self._mission_template(state)
        encounter_type = EncounterType.PORTAL if bool(mission.portalMission if mission is not None else True) else EncounterType.SCAVENGING
        enemy_characters = []
        for unit in hostile_units:
            character = character_from_state(
                unit.characterState,
                item_resolver=self.character_service._resolve_item,
                error_item=self.context.error_item,
            )
            enemy_characters.append(
                {
                    "character": character,
                    "is_boss": bool(unit.isBoss),
                    "is_elite": bool(unit.isElite),
                }
            )
        await self.battle_runtime_service.start_or_resume_mission_battle(
            interaction=interaction,
            player_id=int(player.discordID),
            mission_id=state.missionId,
            mission_name=state.missionName,
            node_id=int(node_state.nodeId),
            enemy_characters=enemy_characters,
            encounter_type=encounter_type,
            allow_retreat=not bool(mission.portalMission if mission is not None else True),
        )

    async def _enter_current_node(self, interaction: discord.Interaction, state: MissionRunState):
        player = await self.player_service.get_player(int(state.playerId))
        mission = self._mission_template(state)
        if mission is None:
            await interaction.response.send_message("Mission data is unavailable.", ephemeral=True)
            return
        if state.currentNodeId is None:
            await self.render_active_mission(interaction, state)
            return
        state.mark_visited(int(state.currentNodeId))
        self._update_ally_progress_metrics(state)
        node_state = state.get_node(int(state.currentNodeId))
        if node_state is not None:
            hostile_units = [unit for unit in node_state.living_unit_states() if self._is_hostile(unit.allegianceId)]
            if hostile_units:
                state.pendingBattleNodeId = int(node_state.nodeId)
                self.save_active_mission(state)
                await self._start_node_battle(interaction, player, state, node_state, hostile_units)
                return

            notes = self._collect_node_events(player, state, node_state)
            if notes:
                state.lastBattleSummary = notes

        self._refresh_objective_status(state)
        self._record_completed_mission_count(state, player)
        self.save_active_mission(state)
        if state.pendingNodeEvents:
            await self.render_node_event(interaction, state)
            return
        if state.status in {MissionRunStatus.SUCCESS, MissionRunStatus.FAILED, MissionRunStatus.FORCED_RETREAT}:
            await self.render_mission_result(interaction, state)
            return
        await self.render_active_mission(interaction, state)

    async def render_active_mission(self, interaction: discord.Interaction, state: MissionRunState, page: int = 0):
        player = await self.player_service.get_player(int(state.playerId))
        embed = self._build_active_mission_embed(player, state)
        view = MissionActiveView(self, int(state.playerId), state, page=page)
        await self._edit_message(interaction, embed=embed, view=view, file=self._map_attachment(state))

    async def move_to_node(self, interaction: discord.Interaction, player_id: int, target_node_id: int):
        state = self.get_active_mission(player_id)
        if state is None:
            await self.show_mission_menu(interaction, player_id)
            return
        accessible = {node_id for node_id, _label in self._accessible_nodes_with_labels(state)}
        target = int(target_node_id)
        if target not in accessible:
            await interaction.response.send_message("That node is not currently reachable.", ephemeral=True)
            return
        state.currentNodeId = target
        state.lastBattleSummary = ""
        state.missionStatistics.timeInsideMissionHours += float(self.MOVE_HOURS_PER_STEP)
        self.save_active_mission(state)
        await self._enter_current_node(interaction, state)

    async def active_mission_page(self, interaction: discord.Interaction, player_id: int, page: int):
        state = self.get_active_mission(player_id)
        if state is None:
            await self.show_mission_menu(interaction, player_id)
            return
        await self.render_active_mission(interaction, state, page=page)

    def apply_battle_resolution(self, battle):
        if getattr(battle, "origin_type", "") != "mission_node":
            return
        state = self.get_active_mission(int(battle.player_id))
        if state is None:
            return
        node_id = int(getattr(battle, "origin_mission_node_id", 0) or 0)
        node_state = state.get_node(node_id)
        if node_state is None or bool(getattr(battle, "origin_resolution_applied", False)):
            return
        battle.origin_resolution_applied = True
        state.pendingBattleNodeId = None
        state.lastBattleSummary = str(getattr(battle, "result_summary", "") or "")
        state.missionStatistics.timeInsideMissionHours += float(
            getattr(getattr(battle, "mission_statistics", None), "timeInsideMissionHours", 0.0) or 0.0
        )

        defeated_bosses = 0
        if battle.outcome == BattleOutcome.VICTORY:
            for unit in node_state.unitStates:
                if self._is_hostile(unit.allegianceId) and not unit.defeated:
                    unit.defeated = True
                    if unit.isBoss:
                        defeated_bosses += 1
            state.missionStatistics.bossesDefeated += defeated_bosses
        else:
            state.status = MissionRunStatus.FORCED_RETREAT
            state.resultSummary = "your squad was forced to retreat"

        player = self.player_service.get_player_sync(int(state.playerId))
        if player is not None:
            selected_ids = set(state.partyState.selectedCharacterInstanceIds)
            selected_characters = [
                character
                for character in getattr(player, "characters", []) or []
                if self._character_identity(character) in selected_ids
            ]
            if selected_characters and all(float(getattr(character, "health", 0.0) or 0.0) <= 0.0 for character in selected_characters):
                state.status = MissionRunStatus.FORCED_RETREAT
                state.resultSummary = "your squad was forced to retreat"

        self._refresh_objective_status(state)
        self._record_completed_mission_count(state, player)
        if state.status == MissionRunStatus.SUCCESS and player is not None:
            self.campaign_service.mark_mission_completed_everywhere(player, state.missionId)
            self.player_service.persist_player(player)
        elif player is not None:
            self.player_service.persist_player(player)
        self.save_active_mission(state)

    async def return_from_battle(self, interaction: discord.Interaction, player_id: int):
        state = self.get_active_mission(player_id)
        if state is None:
            await self.show_mission_menu(interaction, player_id)
            return
        if state.pendingNodeEvents:
            await self.render_node_event(interaction, state)
            return
        if state.status == MissionRunStatus.FORCED_RETREAT:
            await self.render_mission_result(interaction, state)
            return
        await self._enter_current_node(interaction, state)

    async def render_mission_result(self, interaction: discord.Interaction, state: MissionRunState):
        embed = self._build_result_embed(state)
        force_single_button = state.status == MissionRunStatus.FORCED_RETREAT
        view = MissionResultView(self, int(state.playerId), state.status, force_single_button=force_single_button)
        await self._edit_message(interaction, embed=embed, view=view)

    async def acknowledge_result(self, interaction: discord.Interaction, player_id: int):
        state = self.get_active_mission(player_id)
        if state is not None:
            player = self.player_service.get_player_sync(int(player_id))
            self._record_completed_mission_count(state, player)
            if state.status == MissionRunStatus.SUCCESS and player is not None:
                self.campaign_service.mark_mission_completed_everywhere(player, state.missionId)
                self.player_service.persist_player(player)
            self.clear_active_mission(player_id)
        await self.show_mission_menu(interaction, player_id)
