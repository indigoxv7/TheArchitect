import os
import time

from dotenv import load_dotenv

from src.config import Globals
import discord
from discord import app_commands
from discord.ext import commands

from src.services.achievement_service import AchievementService
from src.services.character_service import CharacterService
from src.services.game_context import GameContext
from src.services.item_service import ItemService
from src.services.menu_runtime_service import ConsoleMenuInterface, MenuRuntimeService
from src.services.menu_service import MenuService
from src.services.player_service import PlayerService
from src.services.race_service import RaceService
from src.services.spell_service import SpellService
from src.services.whitelist_service import AdminWhitelistService
from src.tools.admin_gui import start_admin_gui_thread


load_dotenv()

GUILD_ID = 288770050448424971
GAME_DATA_DIRECTORY = "./GameData"
ADMIN_WHITELIST_PATH = os.path.join(GAME_DATA_DIRECTORY, "AdminWhitelist.json")
PLAYER_SAVE_DIRECTORY = os.path.join(GAME_DATA_DIRECTORY, "PlayerSaves")
EXISTING_PLAYERS_ROSTER_PATH = os.path.join(GAME_DATA_DIRECTORY, "ExistingPlayersRoster.json")
MENU_DIRECTORY = os.path.join(GAME_DATA_DIRECTORY, "Menus")
SPELLBOOK_PATH = os.path.join(GAME_DATA_DIRECTORY, "Spells", "spellbook.json")
ITEMBOOK_PATH = os.path.join(GAME_DATA_DIRECTORY, "Items", "itembook.json")
CHARACTER_DIRECTORY = os.path.join(GAME_DATA_DIRECTORY, "Characters")
ACHIEVEMENTBOOK_PATH = os.path.join(GAME_DATA_DIRECTORY, "Achievements", "achievementbook.json")
RACEBOOK_PATH = os.path.join(GAME_DATA_DIRECTORY, "Races", "racebook.json")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

EMOJI_PLACEHOLDERS = {
    key: value for key, value in vars(Globals).items() if key.endswith("Emoji") and isinstance(value, str)
}

context = GameContext(max_num_characters=4)
whitelist_service = AdminWhitelistService(ADMIN_WHITELIST_PATH, context=context)
player_service = PlayerService(
    bot=bot,
    guild_id=GUILD_ID,
    context=context,
    player_save_directory=PLAYER_SAVE_DIRECTORY,
    existing_players_roster_path=EXISTING_PLAYERS_ROSTER_PATH,
)
spell_service = SpellService(spellbook_path=SPELLBOOK_PATH, context=context)
item_service = ItemService(itembook_path=ITEMBOOK_PATH, context=context)
character_service = CharacterService(characters_directory=CHARACTER_DIRECTORY, context=context, item_service=item_service)
achievement_service = AchievementService(achievementbook_path=ACHIEVEMENTBOOK_PATH, context=context)
race_service = RaceService(
    racebook_path=RACEBOOK_PATH,
    context=context,
    character_service=character_service,
    spell_service=spell_service,
)
menu_service = MenuService(
    menu_directory=MENU_DIRECTORY,
    emoji_placeholders=EMOJI_PLACEHOLDERS,
    context=context,
)
_is_initialized = False

menu_runtime_service = MenuRuntimeService(
    menu_service=menu_service,
    player_service=player_service,
    whitelist_service=whitelist_service,
    spell_service=spell_service,
    item_service=item_service,
    context=context,
)


def initialize_game():
    global _is_initialized
    if _is_initialized:
        return

    whitelist_service.load()
    player_service.initialize_storage()
    spell_service.load_spellbook()
    achievement_service.load_achievementbook()
    item_service.load_itembook(default_items=dict(context.all_items))
    character_service.load_characters()
    race_service.load_racebook()
    menu_service.load_menus()
    _is_initialized = True


@app_commands.command(name="play", description="Displays an interactive menu")
async def play_command(interaction: discord.Interaction):
    await menu_runtime_service.display_menu(interaction, context.root_menu)


@app_commands.command(name="menu", description="Displays an interactive menu")
async def menu_command(interaction: discord.Interaction):
    await menu_runtime_service.display_menu(interaction, context.root_menu)


set_group = app_commands.Group(name="set", description="Admin-only set commands")


@set_group.command(name="energy", description="Set a player's energy")
@app_commands.describe(discord_user="Player to update", value="New energy value")
async def set_energy_command(interaction: discord.Interaction, discord_user: discord.Member, value: int):
    if not whitelist_service.is_admin(interaction.user.id):
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return

    target_player = await player_service.get_player(discord_user.id)
    clamped_value = max(0, min(int(target_player.energyCap), int(value)))
    target_player.energy = float(clamped_value)
    target_player.energyLastCalculatedTime = time.time()
    target_player.Save()

    await interaction.response.send_message(
        f"Set energy for <@{discord_user.id}> to {int(target_player.energy)}/{int(target_player.energyCap)}.",
        ephemeral=True,
    )


@bot.event
async def on_ready():
    guild_ref = discord.Object(id=GUILD_ID)
    bot.tree.add_command(play_command, guild=guild_ref)
    bot.tree.add_command(menu_command, guild=guild_ref)
    bot.tree.add_command(set_group, guild=guild_ref)
    await bot.tree.sync(guild=guild_ref)

    guild = bot.get_guild(GUILD_ID) if hasattr(bot, "get_guild") else None
    player_service.set_guild(guild)

    initialize_game()
    print(f"Bot is ready and commands are synced with guild {GUILD_ID}")


TOKEN = os.getenv("BOT_TOKEN")
if __name__ == "__main__":
    initialize_game()
    start_admin_gui_thread(
        spell_service=spell_service,
        item_service=item_service,
        character_service=character_service,
        achievement_service=achievement_service,
        player_service=player_service,
        race_service=race_service,
    )
    bot.run(TOKEN)

