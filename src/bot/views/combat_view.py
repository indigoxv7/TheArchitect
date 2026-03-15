import discord


class CombatView(discord.ui.View):
    def __init__(self, runtime, battle):
        super().__init__(timeout=86400)
        self.runtime = runtime
        self.battle = battle
        player_id = int(battle.player_id)

        self.add_item(TabButton(runtime, player_id, "Orders", row=0))
        self.add_item(TabButton(runtime, player_id, "Targets", row=0))
        self.add_item(TabButton(runtime, player_id, "Resources", row=0))
        self.add_item(TabButton(runtime, player_id, "Intel", row=0))
        self.add_item(TabButton(runtime, player_id, "Retreat", row=0))

        active_tab = str(getattr(battle, "active_tab", "Orders") or "Orders")
        if active_tab == "Orders":
            self.add_item(CycleOrdersButton(runtime, player_id, "Stance", row=1))
            self.add_item(CycleOrdersButton(runtime, player_id, "Token", row=1))
        elif active_tab == "Targets":
            self.add_item(CycleOrdersButton(runtime, player_id, "Priority", row=1))
        elif active_tab == "Resources":
            consumables = runtime.battle_service.list_available_consumables(battle)
            if consumables:
                self.add_item(ConsumableSelect(runtime, player_id, consumables, row=1))
        elif active_tab == "Retreat":
            self.add_item(RetreatButton(runtime, player_id, row=1, disabled=not battle.encounter.allow_retreat))

        self.add_item(AdvanceButton(runtime, player_id, row=2))
        self.add_item(AutoResolveButton(runtime, player_id, row=2))
        self.add_item(StrategyButton(runtime, player_id, row=2))
        self.add_item(ResourcesShortcutButton(runtime, player_id, row=2))
        self.add_item(HoldButton(runtime, player_id, row=2))


class TabButton(discord.ui.Button):
    def __init__(self, runtime, player_id: int, tab_name: str, row: int = 0):
        style = discord.ButtonStyle.secondary
        if runtime._is_active_tab(player_id, tab_name):
            style = discord.ButtonStyle.primary
        super().__init__(label=tab_name, style=style, row=row)
        self.runtime = runtime
        self.player_id = player_id
        self.tab_name = tab_name

    async def callback(self, interaction: discord.Interaction):
        await self.runtime.show_tab(interaction, self.player_id, self.tab_name)


class CycleOrdersButton(discord.ui.Button):
    def __init__(self, runtime, player_id: int, kind: str, row: int = 1):
        battle = runtime.battle_service.get_active_battle(player_id)
        label_value = ""
        if battle is not None:
            if kind == "Stance":
                label_value = battle.orders.stance.name
            elif kind == "Token":
                label_value = battle.orders.token_policy.name
            elif kind == "Priority":
                label_value = battle.orders.target_priority.name
        super().__init__(label=f"{kind}: {label_value}", style=discord.ButtonStyle.secondary, row=row)
        self.runtime = runtime
        self.player_id = player_id
        self.kind = kind

    async def callback(self, interaction: discord.Interaction):
        await self.runtime.cycle_order_setting(interaction, self.player_id, self.kind)


class AdvanceButton(discord.ui.Button):
    def __init__(self, runtime, player_id: int, row: int = 2):
        super().__init__(label="Advance", style=discord.ButtonStyle.success, row=row)
        self.runtime = runtime
        self.player_id = player_id

    async def callback(self, interaction: discord.Interaction):
        await self.runtime.advance_exchange(interaction, self.player_id)


class AutoResolveButton(discord.ui.Button):
    def __init__(self, runtime, player_id: int, row: int = 2):
        super().__init__(label="Auto-resolve", style=discord.ButtonStyle.danger, row=row)
        self.runtime = runtime
        self.player_id = player_id

    async def callback(self, interaction: discord.Interaction):
        await self.runtime.auto_resolve(interaction, self.player_id)


class StrategyButton(discord.ui.Button):
    def __init__(self, runtime, player_id: int, row: int = 2):
        super().__init__(label="Submit Strategy", style=discord.ButtonStyle.primary, row=row)
        self.runtime = runtime
        self.player_id = player_id

    async def callback(self, interaction: discord.Interaction):
        await self.runtime.open_strategy_modal(interaction, self.player_id)


class ResourcesShortcutButton(discord.ui.Button):
    def __init__(self, runtime, player_id: int, row: int = 2):
        super().__init__(label="Use Consumable", style=discord.ButtonStyle.secondary, row=row)
        self.runtime = runtime
        self.player_id = player_id

    async def callback(self, interaction: discord.Interaction):
        await self.runtime.show_tab(interaction, self.player_id, "Resources")


class HoldButton(discord.ui.Button):
    def __init__(self, runtime, player_id: int, row: int = 2):
        super().__init__(label="Hold", style=discord.ButtonStyle.secondary, row=row)
        self.runtime = runtime
        self.player_id = player_id

    async def callback(self, interaction: discord.Interaction):
        await self.runtime.hold_position(interaction, self.player_id)


class RetreatButton(discord.ui.Button):
    def __init__(self, runtime, player_id: int, row: int = 1, disabled: bool = False):
        super().__init__(label="Retreat", style=discord.ButtonStyle.danger, row=row, disabled=disabled)
        self.runtime = runtime
        self.player_id = player_id

    async def callback(self, interaction: discord.Interaction):
        await self.runtime.retreat(interaction, self.player_id)


class ConsumableSelect(discord.ui.Select):
    def __init__(self, runtime, player_id: int, consumables: list[tuple[str, str]], row: int = 1):
        options = [discord.SelectOption(label=label[:100], value=value) for value, label in consumables[:25]]
        super().__init__(placeholder="Select a consumable", min_values=1, max_values=1, options=options, row=row)
        self.runtime = runtime
        self.player_id = player_id

    async def callback(self, interaction: discord.Interaction):
        await self.runtime.use_consumable(interaction, self.player_id, self.values[0])
