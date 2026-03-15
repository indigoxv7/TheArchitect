import os
import time

from dotenv import load_dotenv

from src.config import Globals
import discord
from discord import app_commands
from discord.ext import commands

from src.persistence.active_battle_store import ActiveBattleStore
from src.persistence.player_memory_store import PlayerMemoryStore
from src.services.achievement_service import AchievementService
from src.services.allegiance_service import AllegianceService
from src.services.battle_runtime_service import BattleRuntimeService
from src.services.battle_service import BattleService
from src.services.character_service import CharacterService
from src.services.encounter_service import EncounterService
from src.services.environment_service import EnvironmentService
from src.services.game_context import GameContext
from src.services.item_service import ItemService
from src.services.main_character_memory_service import MainCharacterMemoryService
from src.services.mission_service import MissionService
from src.services.menu_runtime_service import ConsoleMenuInterface, MenuRuntimeService
from src.services.menu_service import MenuService
from src.services.openai_narrative_service import OpenAINarrativeService
from src.services.player_service import PlayerService
from src.services.power_rating_service import PowerRatingService
from src.services.race_service import RaceService
from src.services.spell_service import SpellService
from src.services.unit_service import UnitService
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
ALLEGIANCEBOOK_PATH = os.path.join(GAME_DATA_DIRECTORY, "Allegiances", "allegiancebook.json")
RACEBOOK_PATH = os.path.join(GAME_DATA_DIRECTORY, "Races", "racebook.json")
UNITBOOK_PATH = os.path.join(GAME_DATA_DIRECTORY, "Units", "unitbook.json")
MISSIONBOOK_PATH = os.path.join(GAME_DATA_DIRECTORY, "Missions", "missionbook.json")
ENVIRONMENTBOOK_PATH = os.path.join(GAME_DATA_DIRECTORY, "Environment", "environmentbook.json")
PLAYER_MEMORY_DIRECTORY = os.path.join(GAME_DATA_DIRECTORY, "PlayerMemory")
PLAYER_MEMORY_DB_PATH = os.path.join(PLAYER_MEMORY_DIRECTORY, "player_memory.sqlite")
ACTIVE_BATTLES_DIRECTORY = os.path.join(GAME_DATA_DIRECTORY, "ActiveBattles")
PORTAL_ENCOUNTER_DIRECTORY = os.path.join(GAME_DATA_DIRECTORY, "PortalEncounters")

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
power_rating_service = PowerRatingService(spell_service=spell_service, item_service=item_service)
character_service = CharacterService(characters_directory=CHARACTER_DIRECTORY, context=context, item_service=item_service)
achievement_service = AchievementService(achievementbook_path=ACHIEVEMENTBOOK_PATH, context=context)
allegiance_service = AllegianceService(allegiancebook_path=ALLEGIANCEBOOK_PATH, context=context)
race_service = RaceService(
    racebook_path=RACEBOOK_PATH,
    context=context,
    character_service=character_service,
    spell_service=spell_service,
    item_service=item_service,
)
unit_service = UnitService(
    unitbook_path=UNITBOOK_PATH,
    context=context,
    race_service=race_service,
    character_service=character_service,
    spell_service=spell_service,
    item_service=item_service,
)
mission_service = MissionService(
    missionbook_path=MISSIONBOOK_PATH,
    context=context,
    allegiance_service=allegiance_service,
    unit_service=unit_service,
)
environment_service = EnvironmentService(environmentbook_path=ENVIRONMENTBOOK_PATH, context=context)
menu_service = MenuService(
    menu_directory=MENU_DIRECTORY,
    emoji_placeholders=EMOJI_PLACEHOLDERS,
    context=context,
)
openai_narrative_service = OpenAINarrativeService()
player_memory_store = PlayerMemoryStore(db_path=PLAYER_MEMORY_DB_PATH)
active_battle_store = ActiveBattleStore(battles_directory=ACTIVE_BATTLES_DIRECTORY)
encounter_service = EncounterService(
    portal_encounter_directory=PORTAL_ENCOUNTER_DIRECTORY,
    context=context,
    race_service=race_service,
    character_service=character_service,
)
memory_service = MainCharacterMemoryService(
    memory_store=player_memory_store,
    player_service=player_service,
    openai_service=openai_narrative_service,
)
battle_service = BattleService(
    context=context,
    player_service=player_service,
    item_service=item_service,
    spell_service=spell_service,
    character_service=character_service,
    race_service=race_service,
    encounter_service=encounter_service,
    active_battle_store=active_battle_store,
    openai_service=openai_narrative_service,
    memory_service=memory_service,
)
battle_runtime_service = BattleRuntimeService(battle_service=battle_service)
_is_initialized = False

menu_runtime_service = MenuRuntimeService(
    menu_service=menu_service,
    player_service=player_service,
    whitelist_service=whitelist_service,
    spell_service=spell_service,
    item_service=item_service,
    context=context,
    battle_runtime_service=battle_runtime_service,
)


def initialize_game():
    global _is_initialized
    if _is_initialized:
        return

    whitelist_service.load()
    player_service.initialize_storage()
    spell_service.load_spellbook()
    achievement_service.load_achievementbook()
    allegiance_service.load_allegiancebook()
    item_service.load_itembook(default_items=dict(context.all_items))
    character_service.load_characters()
    race_service.load_racebook()
    unit_service.load_unitbook()
    mission_service.load_missionbook()
    environment_service.load_environmentbook()
    memory_service.initialize()
    battle_service.initialize()
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
        unit_service=unit_service,
        allegiance_service=allegiance_service,
        mission_service=mission_service,
        environment_service=environment_service,
        memory_service=memory_service,
        power_rating_service=power_rating_service,
    )
    bot.run(TOKEN)


