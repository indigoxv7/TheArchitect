import discord


class SimpleMenu(discord.ui.View):
    def __init__(self, current_menu, original_message, visible_children, on_select):
        super().__init__(timeout=86400)
        self.current_menu = current_menu

        if self.current_menu.parent is not None:
            self.add_item(BackButton(menu=self.current_menu, original_message=original_message, on_select=on_select))

        for child_menu, proper_title in visible_children:
            self.add_item(MenuButton(child_menu, original_message, proper_title, on_select))


class MenuButton(discord.ui.Button):
    def __init__(self, menu, original_message, proper_title: str, on_select):
        super().__init__(label=proper_title, emoji=menu.myEmoji or "", style=discord.ButtonStyle.primary)
        self.menu = menu
        self.original_message = original_message
        self.on_select = on_select

    async def callback(self, interaction: discord.Interaction):
        await self.on_select(interaction, self.menu, self.original_message)


class BackButton(discord.ui.Button):
    def __init__(self, menu, original_message, on_select):
        super().__init__(label="Back", emoji="\U0001F519", style=discord.ButtonStyle.secondary)
        self.menu = menu
        self.original_message = original_message
        self.on_select = on_select

    async def callback(self, interaction: discord.Interaction):
        if self.menu.parent:
            await self.on_select(interaction, self.menu.parent, self.original_message)
