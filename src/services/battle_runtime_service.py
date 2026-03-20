from __future__ import annotations

import discord

from src.bot.views.combat_view import CombatView, ResolvedBattleView
from src.domain.combat import BattlePhase, EncounterType


class StrategyModal(discord.ui.Modal, title="Battle Strategy"):
    strategy_text = discord.ui.TextInput(
        label="Commander Strategy",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000,
    )

    def __init__(self, runtime: "BattleRuntimeService", player_id: int, message: discord.Message):
        super().__init__()
        self.runtime = runtime
        self.player_id = int(player_id)
        self.message = message

    async def on_submit(self, interaction: discord.Interaction):
        battle = self.runtime.battle_service.get_active_battle(self.player_id)
        if battle is None:
            await interaction.response.send_message("No active battle to update.", ephemeral=True)
            return
        judgment = self.runtime.battle_service.apply_strategy(battle, str(self.strategy_text.value or ""))
        note = f"Strategy scored {judgment['score']}/10."
        if not interaction.response.is_done():
            await interaction.response.defer()
        await self.runtime.render_battle(interaction, battle, message=self.message, note=note)


class BattleRuntimeService:
    def __init__(self, battle_service, mission_runtime_service=None):
        self.battle_service = battle_service
        self.mission_runtime_service = mission_runtime_service

    def set_mission_runtime_service(self, mission_runtime_service):
        self.mission_runtime_service = mission_runtime_service

    def _is_active_tab(self, player_id: int, tab_name: str) -> bool:
        battle = self.battle_service.get_active_battle(player_id)
        return battle is not None and str(getattr(battle, "active_tab", "Orders") or "Orders") == str(
            tab_name or "Orders"
        )

    def build_embed(self, battle) -> discord.Embed:
        snapshot = self.battle_service.build_battle_snapshot(battle)
        title = f"{snapshot['mission_name']} | {snapshot['terrain']}"
        if battle.phase == BattlePhase.RESOLVED:
            title = f"{title} | {battle.outcome.name.title()}"
        embed = discord.Embed(title=title)
        odds = int(round(float(snapshot["cached_victory_odds"]) * 100))
        header_lines = [
            f"Exchange: {snapshot['exchange']}",
            f"Stance: {snapshot['stance']}",
            f"Objective: {snapshot['objective_description']}",
            f"Objective Status: {snapshot['objective_status']}",
            f"Odds of Success: {odds}%",
        ]
        embed.description = "\n".join(header_lines)
        mission_stats = snapshot.get("mission_statistics", {}) or {}
        embed.add_field(
            name="Battlefield",
            value=(
                f"Lines: {snapshot['total_lines']}\n"
                f"Width: {snapshot['width']}\n"
                f"Allied Front: {snapshot['player_front_line']}\n"
                f"Enemy Front: {snapshot['enemy_front_line']}"
            ),
            inline=True,
        )
        embed.add_field(
            name="Mission Stats",
            value=(
                f"Enemies Remaining: {mission_stats.get('enemiesRemaining', 0)}/{mission_stats.get('totalStartingEnemies', 0)}\n"
                f"Allies Remaining: {mission_stats.get('alliesRemaining', 0)}/{mission_stats.get('totalStartingAllies', 0)}\n"
                f"Bosses Defeated: {mission_stats.get('bossesDefeated', 0)}\n"
                f"Hours: {float(mission_stats.get('timeInsideMissionHours', 0.0) or 0.0):.2f}"
            ),
            inline=True,
        )
        embed.add_field(
            name="Orders",
            value=(
                f"Stance: {battle.orders.stance.name}\n"
                f"Target Priority: {battle.orders.target_priority.name}\n"
                f"Token Policy: {battle.orders.token_policy.name}\n"
                f"Strategy Score: {battle.orders.strategy_score}/10"
            ),
            inline=True,
        )
        ally_lines = []
        for ally in snapshot["allies"][:10]:
            ally_lines.append(
                f"{ally['name']} | {ally['health']:.0f}/{ally['max_health']:.0f} | {ally['state']} | L{ally['line']}"
            )
        enemy_lines = []
        for enemy in snapshot["enemies"][:10]:
            count_suffix = f" x{enemy['count']}" if int(enemy.get("count", 1)) > 1 else ""
            enemy_lines.append(
                f"{enemy['name']}{count_suffix} | {enemy['health']:.0f}/{enemy['max_health']:.0f} | {enemy['state']} | L{enemy['line']}"
            )
        embed.add_field(name="Allies", value="\n".join(ally_lines) if ally_lines else "No allied units.", inline=False)
        embed.add_field(
            name="Enemies", value="\n".join(enemy_lines) if enemy_lines else "No enemy units.", inline=False
        )

        highlights = snapshot["recent_highlights"][:8]
        trigger_lines = snapshot["recent_triggers"][:4]
        if highlights or trigger_lines:
            body = []
            if highlights:
                body.extend(f"- {line}" for line in highlights)
            if trigger_lines:
                body.extend(f"Trigger: {line}" for line in trigger_lines)
            embed.add_field(name="Highlights", value="\n".join(body), inline=False)

        if battle.phase == BattlePhase.RESOLVED:
            embed.add_field(name="Outcome", value=battle.result_summary or battle.outcome.name.title(), inline=False)
        elif battle.active_tab == "Intel":
            reasons = battle.orders.strategy_reasons[:4]
            if reasons:
                embed.add_field(
                    name="Strategy Notes", value="\n".join(f"- {reason}" for reason in reasons), inline=False
                )
        elif battle.active_tab == "Resources":
            consumables = self.battle_service.list_available_consumables(battle)
            embed.add_field(
                name="Consumables",
                value="\n".join(label for _value, label in consumables[:10])
                if consumables
                else "No consumables available.",
                inline=False,
            )
        elif battle.active_tab == "Retreat":
            if battle.encounter.allow_retreat:
                embed.add_field(name="Retreat", value="Retreat is available from this battle.", inline=False)
            else:
                embed.add_field(name="Retreat", value="Retreat is disabled in portal battles.", inline=False)

        embed.set_footer(text=f"Active Tab: {battle.active_tab}")
        return embed

    def build_view(self, battle):
        if battle.phase == BattlePhase.RESOLVED:
            return ResolvedBattleView(self, battle)
        return CombatView(self, battle)

    async def start_or_resume_battle(
        self, interaction: discord.Interaction, player_id: int, encounter_type: EncounterType
    ):
        battle, resumed = self.battle_service.start_or_resume_battle(player_id, encounter_type)
        note = "Resumed active battle." if resumed else f"Started {encounter_type.name.lower()} battle."
        await self.render_battle(interaction, battle, note=note)

    async def start_or_resume_mission_battle(
        self,
        interaction: discord.Interaction,
        player_id: int,
        mission_id: str,
        mission_name: str,
        node_id: int,
        enemy_characters: list[dict[str, object]],
        encounter_type: EncounterType,
        allow_retreat: bool,
    ):
        battle, resumed = self.battle_service.start_or_resume_mission_battle(
            player_id=player_id,
            mission_id=mission_id,
            mission_name=mission_name,
            node_id=node_id,
            enemy_characters=enemy_characters,
            encounter_type=encounter_type,
            allow_retreat=allow_retreat,
        )
        note = "Resumed mission battle." if resumed else "Hostile forces engage your squad."
        await self.render_battle(interaction, battle, note=note)

    async def render_battle(
        self, interaction: discord.Interaction, battle, message: discord.Message | None = None, note: str | None = None
    ):
        embed = self.build_embed(battle)
        view = self.build_view(battle)
        if message is None:
            if interaction.response.is_done():
                if interaction.message is not None:
                    await interaction.message.edit(embed=embed, view=view, attachments=[])
                else:
                    await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            else:
                await interaction.response.edit_message(embed=embed, view=view, attachments=[])
        else:
            if not interaction.response.is_done():
                await interaction.response.defer()
            await message.edit(embed=embed, view=view, attachments=[])
        if note:
            if interaction.response.is_done():
                await interaction.followup.send(note, ephemeral=True)
            else:
                await interaction.response.send_message(note, ephemeral=True)

    async def _load_owned_battle(self, interaction: discord.Interaction, player_id: int):
        if interaction.user.id != int(player_id):
            await interaction.response.send_message("You can only interact with your own battle.", ephemeral=True)
            return None
        battle = self.battle_service.get_active_battle(player_id)
        if battle is None:
            await interaction.response.send_message("No active battle found.", ephemeral=True)
            return None
        return battle

    async def show_tab(self, interaction: discord.Interaction, player_id: int, tab_name: str):
        battle = await self._load_owned_battle(interaction, player_id)
        if battle is None:
            return
        self.battle_service.set_active_tab(battle, tab_name)
        await self.render_battle(interaction, battle)

    async def cycle_order_setting(self, interaction: discord.Interaction, player_id: int, kind: str):
        battle = await self._load_owned_battle(interaction, player_id)
        if battle is None:
            return
        if kind == "Stance":
            self.battle_service.cycle_stance(battle)
        elif kind == "Token":
            self.battle_service.cycle_token_policy(battle)
        else:
            self.battle_service.cycle_target_priority(battle)
        await self.render_battle(interaction, battle)

    async def advance_exchange(self, interaction: discord.Interaction, player_id: int):
        battle = await self._load_owned_battle(interaction, player_id)
        if battle is None:
            return
        summary = self.battle_service.resolve_exchange(battle, persist=True, record_memory=True)
        note = f"Resolved exchange {summary.exchange_number}."
        await self.render_battle(interaction, battle, note=note)

    async def auto_resolve(self, interaction: discord.Interaction, player_id: int):
        battle = await self._load_owned_battle(interaction, player_id)
        if battle is None:
            return
        battle = self.battle_service.auto_resolve(battle, persist=True)
        await self.render_battle(interaction, battle, note="Battle auto-resolved.")

    async def open_strategy_modal(self, interaction: discord.Interaction, player_id: int):
        battle = await self._load_owned_battle(interaction, player_id)
        if battle is None:
            return
        message = interaction.message
        await interaction.response.send_modal(StrategyModal(self, player_id, message))

    async def use_consumable(self, interaction: discord.Interaction, player_id: int, item_identifier: str):
        battle = await self._load_owned_battle(interaction, player_id)
        if battle is None:
            return
        try:
            note = self.battle_service.use_consumable(battle, item_identifier)
        except Exception as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        await self.render_battle(interaction, battle, note=note)

    async def hold_position(self, interaction: discord.Interaction, player_id: int):
        battle = await self._load_owned_battle(interaction, player_id)
        if battle is None:
            return
        self.battle_service.hold_position(battle)
        await self.render_battle(interaction, battle, note="Holding position.")

    async def retreat(self, interaction: discord.Interaction, player_id: int):
        battle = await self._load_owned_battle(interaction, player_id)
        if battle is None:
            return
        try:
            battle = self.battle_service.retreat(battle)
        except Exception as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        await self.render_battle(interaction, battle, note="Retreat ordered.")

    async def return_to_mission(self, interaction: discord.Interaction, player_id: int):
        if self.mission_runtime_service is None:
            await interaction.response.send_message("Mission runtime is unavailable.", ephemeral=True)
            return
        await self.mission_runtime_service.return_from_battle(interaction, player_id)
