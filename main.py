import copy
import json
import asyncio
import time
from string import Template
import re
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Optional, List
from player_functions import *
from Character import *
from Items import Item
import Globals
import os
from pathlib import Path
from dotenv import load_dotenv

try:
    import discord
    from discord import app_commands
    from discord.ext import commands
    DISCORD_AVAILABLE = True
except ModuleNotFoundError:
    DISCORD_AVAILABLE = False

    class _DummyIntents:
        @staticmethod
        def all():
            return None

    class _DummyEmbed:
        def __init__(self, title="", description=""):
            self.title = title
            self.description = description
            self.footer = ""
            self.image_url = None

        def set_footer(self, text=""):
            self.footer = text

        def set_image(self, url=""):
            self.image_url = url

    class _DummyButtonStyle:
        primary = 1
        secondary = 2

    class _DummyView:
        def __init__(self, timeout=None):
            self.timeout = timeout
            self.items = []

        def add_item(self, item):
            self.items.append(item)

    class _DummyButton:
        def __init__(self, label=None, emoji=None, style=None):
            self.label = label
            self.emoji = emoji
            self.style = style

    class _DummyUI:
        View = _DummyView
        Button = _DummyButton

    class _DummyObject:
        def __init__(self, id=None):
            self.id = id

    class _DummyTree:
        def add_command(self, *args, **kwargs):
            return None

        async def sync(self, *args, **kwargs):
            return None

    class _DummyBot:
        def __init__(self, command_prefix=None, intents=None):
            self.command_prefix = command_prefix
            self.intents = intents
            self.tree = _DummyTree()

        def event(self, func):
            return func

        def run(self, token):
            print("Discord package not available; bot.run skipped.")

    class _DummyGroup:
        def __init__(self, name=None, description=None):
            self.name = name
            self.description = description

        def command(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

    class _DummyAppCommands:
        Group = _DummyGroup

        @staticmethod
        def command(*args, **kwargs):
            def decorator(func):
                return func
            return decorator

        @staticmethod
        def describe(**kwargs):
            def decorator(func):
                return func
            return decorator

    class _DummyDiscordModule:
        Intents = _DummyIntents
        Embed = _DummyEmbed
        ui = _DummyUI
        ButtonStyle = _DummyButtonStyle
        Object = _DummyObject
        Message = object
        Interaction = object
        Member = object

    discord = _DummyDiscordModule()
    app_commands = _DummyAppCommands()

    class _DummyCommandsModule:
        Bot = _DummyBot

    commands = _DummyCommandsModule()


# Load the .env file
load_dotenv()

GUILD_ID = 288770050448424971
ADMIN_WHITELIST_PATH = "./AdminWhitelist.json"
# Create the bot with the required intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
guild = None
developmentAdminWhitelist = set()
EMOJI_PLACEHOLDERS = {
    key: value for key, value in vars(Globals).items()
    if key.endswith("Emoji") and isinstance(value, str)
}


def ReplaceEmojiAliases(text: str):
    for key, value in EMOJI_PLACEHOLDERS.items():
        short_name = key[:-5]
        text = text.replace(f":{short_name}:", value)
        text = text.replace("{" + key + "}", value)
    return text


def EnsureAdminWhitelistExists(filename: str):
    if os.path.exists(filename):
        return

    with open(filename, "w", encoding="utf-8") as file:
        json.dump([191980469670248448], file, indent=4)


def LoadAdminWhitelist(filename: str):
    global developmentAdminWhitelist
    EnsureAdminWhitelistExists(filename)

    with open(filename, "r", encoding="utf-8-sig") as file:
        rawList = json.load(file)

    developmentAdminWhitelist = set()
    for value in rawList:
        try:
            developmentAdminWhitelist.add(int(value))
        except (TypeError, ValueError):
            continue


def IsDevelopmentAdmin(discordID: int):
    return discordID in developmentAdminWhitelist

################################
#                              #
#        Other Classes         #
#                              #
################################


################################
#                              #
#      Utility Functions       #
#                              #
################################

def GetIntFromStringEnd(string: str):
    match = re.search(r'\d+$', string)
    return int(match.group()) if match else None

async def GetNameFromID(guildObj, discord_id):
    # Prefer guild-specific nicknames when available.
    candidate_guild = guildObj

    if candidate_guild is None and hasattr(bot, "get_guild"):
        candidate_guild = bot.get_guild(GUILD_ID)

    if candidate_guild is not None and hasattr(candidate_guild, "fetch_member"):
        try:
            member = await candidate_guild.fetch_member(discord_id)
            return member.nick or member.display_name
        except Exception:
            pass

    if hasattr(bot, "get_user"):
        cached_user = bot.get_user(discord_id)
        if cached_user is not None:
            return getattr(cached_user, "display_name", None) or cached_user.name

    if hasattr(bot, "fetch_user"):
        try:
            user = await bot.fetch_user(discord_id)
            return getattr(user, "display_name", None) or user.name
        except Exception:
            pass

    return str(discord_id)

################################
#                              #
#       player functions       #
#                              #
################################


existingPlayers = {}    # this is a list of all discord IDs who have a save file already. This list is used so that we don't have to search our whole save file list each to make sure they aren't new time an unloaded player wants to play.
                        # key = discord ID, value = bool true if loaded false if not loaded.
playerList = {} # the actual loaded player objects. Key = discord ID, value = Player object
allItems = {}  # Master list of items with no organization. Key is name value is Item object.
errorItem = None # default item for errors
exampleCharacters = [] # for testing
maxNumCharacters = 4
PLAYER_SAVE_DIRECTORY = "./PlayerSaves"
EXISTING_PLAYERS_ROSTER_PATH = "./ExistingPlayersRoster.json"

def GetPlayerSavePath(discord_id: int):
    return os.path.join(PLAYER_SAVE_DIRECTORY, f"{discord_id}.json")


def SaveExistingPlayersRoster(filename: str):
    with open(filename, 'w') as file:
        json.dump(list(existingPlayers.keys()), file)

def LoadExistingPlayersRoster(filename: str):
    global existingPlayers
    with open(filename, 'r') as file:
        keys = json.load(file)
        existingPlayers = {key: False for key in keys}


# I'll choose items at random by giving them a rarity value (how often in 1,000 drops they should appear for example), with 1 being the lowest.
# Then I add up all values of a given list of item type I want dropped, choose a random number, and iterate the list adding to a count until I reach that number.
def ItemSetup():
    global allItems
    global errorItem
    standardAttackPower = [ItemPower(PowerType.PHYSICAL_ATTACK, 12)]
    piercingDamage = [DamageType.PIERCING]
    bludgeoningDamage = [DamageType.BLUDGEONING]
    slashingDamage = [DamageType.SLASHING]
    standardConsumablePower = [ItemPower(PowerType.CONSUMABLE_POWER, 10)]

    # A reason="" will automatically be filled out by the item that inherits it (using its own name as the reason).
    PhysResistBonus = [Bonus(BonusType.FLAT, AttributeBonus(Attribute.PHYSICAL_RESISTANCE, 1), None, 0, "")]

    # Weapons
    newItem = Item("Dagger", EquipSlot.HANDS, 0, DEFAULT_DURABILITY, None, ItemType.MELEE_THROWABLE, standardAttackPower, piercingDamage)
    allItems[newItem.name] = newItem
    newItem = Item("Spear", EquipSlot.HANDS, 0, DEFAULT_DURABILITY, None, ItemType.MELEE_WEAPON, standardAttackPower, piercingDamage)
    allItems[newItem.name] = newItem
    newItem = Item("Sword", EquipSlot.HANDS, 0, DEFAULT_DURABILITY, None, ItemType.MELEE_WEAPON, standardAttackPower, slashingDamage)
    allItems[newItem.name] = newItem
    newItem = Item("Warhammer", EquipSlot.HANDS, 0, DEFAULT_DURABILITY, None, ItemType.MELEE_WEAPON, standardAttackPower, bludgeoningDamage)
    allItems[newItem.name] = newItem
    newItem = Item("Bow", EquipSlot.HANDS, 0, DEFAULT_DURABILITY, None, ItemType.RANGED_WEAPON, standardAttackPower, piercingDamage)
    allItems[newItem.name] = newItem
    newItem = Item("Shield", EquipSlot.HANDS, 0, DEFAULT_DURABILITY, PhysResistBonus, ItemType.MELEE_WEAPON, None, None)
    allItems[newItem.name] = newItem

    # Armor
    newItem = Item("Helmet", EquipSlot.HEAD, 0, DEFAULT_DURABILITY, PhysResistBonus, ItemType.ARMOR, None, None)
    allItems[newItem.name] = newItem
    newItem = Item("Necklace", EquipSlot.NECK, 0, DEFAULT_DURABILITY, PhysResistBonus, ItemType.ARMOR, None, None)
    allItems[newItem.name] = newItem
    newItem = Item("Body Armor", EquipSlot.BODY, 0, DEFAULT_DURABILITY, PhysResistBonus, ItemType.ARMOR, None, None)
    allItems[newItem.name] = newItem
    newItem = Item("Gloves", EquipSlot.HANDS, 0, DEFAULT_DURABILITY, PhysResistBonus, ItemType.ARMOR, None, None)
    allItems[newItem.name] = newItem
    newItem = Item("Ring", EquipSlot.RING, 0, DEFAULT_DURABILITY, PhysResistBonus, ItemType.ARMOR, None, None)
    allItems[newItem.name] = newItem
    newItem = Item("Pants", EquipSlot.LEGS, 0, DEFAULT_DURABILITY, PhysResistBonus, ItemType.ARMOR, None, None)
    allItems[newItem.name] = newItem
    newItem = Item("Boots", EquipSlot.FEET, 0, DEFAULT_DURABILITY, PhysResistBonus, ItemType.ARMOR, None, None)
    allItems[newItem.name] = newItem

    # Consumables
    newItem = Item("Bandage", EquipSlot.NOT_EQUIPABLE, 0, DEFAULT_DURABILITY, None, ItemType.CONSUMABLE, standardConsumablePower, None)
    allItems[newItem.name] = newItem

    # Msc
    newItem = Item("Paperclip", EquipSlot.NOT_EQUIPABLE, 0, DEFAULT_DURABILITY, None, ItemType.DEFAULT, None, None)
    allItems[newItem.name] = newItem
    errorItem = Item("[ERROR MISSING ITEM]", EquipSlot.NOT_EQUIPABLE, 0, DEFAULT_DURABILITY, None, ItemType.DEFAULT, None, None)
    allItems[errorItem.name] = errorItem


# returns an ERROR MISSING ITEM if it can't find the given name in our master item dictionary.
def FindItem(name: str):
    try:
        return allItems[name]
    except KeyError:
        return errorItem



def ExampleCharacterSetup():
    global exampleCharacters
    attributes = Attributes(7, 4, 5, 4, 3, 5)
    inv = [FindItem("Bandage"), FindItem("Paperclip")]
    gear = Gear(FindItem("Helmet"), None, FindItem("Body Armor"), FindItem("Gloves"), None, FindItem("Pants"), FindItem("Boots"), FindItem("Warhammer"), FindItem("Shield"), inv)
    achievement = Achievement("First Kill", Bonus(BonusType.FLAT, AttributeBonus(Attribute.ALL_ATTRIBUTES, 2), None, 0), "Firstblood")
    affinities = Affinities(0.5, 0.5, 0.5, 0.5)
    exampleCharacters.append(Character("Bjorn Smith", attributes, 0, "Tier I", affinities, "None", gear, achievement))


def PlayerSetup():
    global playerList
    # testPlayer = Player(191980469670248448, 10000, 3, TitlePreference.Masculine, exampleCharacters)
    # testPlayer.AttachSavePath(GetPlayerSavePath(testPlayer.discordID), enableAutoSave=False)
    # testPlayer.isNewPlayer = True
    # testPlayer.playerName = "Wasabi Avenger"
    # testPlayer.isNewPlayer = False
    # testPlayer.SetAutoSaveEnabled(True)
    # testPlayer.Save()
    # playerList[testPlayer.discordID] = testPlayer

# gets a player object from our playerList. if the player does not exist, create it.
async def GetPlayer(id: int):
    # Check if the player is already loaded
    if id in playerList:
        return playerList[id]

    playerSavePath = GetPlayerSavePath(id)

    # Check if the player has a save file
    if os.path.exists(playerSavePath):
        # Mark the player as loaded and load the player object
        existingPlayers[id] = True
        p = load_player(playerSavePath)
        p.AttachSavePath(playerSavePath, enableAutoSave=True)
        nickname = await GetNameFromID(guild, id) # we refresh player nickname each time they are loaded.
        p.playerName = nickname
        playerList[id] = p
        return p

    # If the player doesn't exist, create a new player
    new_player = CreateNewPlayer(id)
    new_player.AttachSavePath(playerSavePath, enableAutoSave=False)
    existingPlayers[id] = True
    SaveExistingPlayersRoster(EXISTING_PLAYERS_ROSTER_PATH)
    nickname = await GetNameFromID(guild, id)
    new_player.playerName = nickname
    new_player.isNewPlayer = True
    new_player.SetAutoSaveEnabled(True)
    new_player.Save()
    playerList[id] = new_player
    return new_player

def CreateNewPlayer(id: int):
    newPlayer = Player(id)
    return newPlayer



# Global dictionary to store player objects using discord_id as the key
players = {}

###############################
#                             #
#          Menu Stuff         #
#                             #
###############################
from menu_functions import *

rootMenu = None
newPlayerMenu = None
MENU_DIRECTORY = "./menus"


def CreateDefaultMenusGraph():
    new_player_menu = Menu(
        myOptionText="Welcome to the collective $playerName!",
        bodyText="Your species has been chosen by the Architect to join countless others on a path to power. As a member of the Collective, you will use nano to enhance your body, gain access to combat classifications, "
                 "and harness power previously unknown."
                 "\n\nDon't get caught up in the game-like system though. If your character dies, they're gone for good. Be "
                 "careful and choose wisely, as even a small miscalculation in planning can lead to the end.",
        uniqueName="newPlayerMenu",
        myEmoji="\U0001F31F",
        imageURL="https://media.discordapp.net/attachments/886469391548559372/1274236983559979050/image.png?ex=66c1852b&is=66c033ab&hm=82c9b63ad2903e31659408b2057e488d6a4f9f0d82c7bdb12da34e477e7af077&=&format=webp&quality=lossless"
    )

    how_to_play_menu = Menu(
        myOptionText="How to play",
        bodyText="The apocalypse has begun. It's a harsh place out here, and to protect yourself and those around you, you'll need to form a **Faction.**\n\n"
                 "Only problem is that costs $nanoEmoji **Nano.** Lots of it.\n\nSo before you can do that, you'll need to go on missions to get stronger and gather resources.\n\n"
                 "There are two types of missions. **Scavenging Missions**, in which you will face off against roaming monsters and bandits on earth, and **Portal Missions**, "
                 "in which you enter a scenario in another world and must complete the objective given to you by the architect.\n\nStart with **Scavenging Missions**. "
                 "They give fewer rewards, but you at least have a chance to run if it gets too dangerous. There is no escape if you fail a **Portal Mission**. \n\n"
                 "Check your **Character**'s gear before you start and make sure you're bringing your best stuff.\n\n"
                 "# Good luck!",
        uniqueName="HowToPlayMenu",
        myEmoji="\U0001F31F",
        imageURL="https://media.discordapp.net/attachments/886469391548559372/1274239069127180338/Portal.png?ex=66c1871c&is=66c0359c&hm=d3c39e8d6175df24827f2da43b294f65ec5f5017da0e04d8330557ceffee82cb&=&format=webp&quality=lossless&width=1920&height=555"
    )
    new_player_menu.add_option(how_to_play_menu)

    main_menu = Menu(
        myOptionText="Main Menu - $factionTitle $playerName $achievementTitle",
        bodyText="Nano: $nanoEmoji $nano\nEnergy: $energy/$energyCap\n\n* Faction (Not founded)\n* Party Members\n* Inventory\n\n* Make trade request\n* Pending Notifications (0)\n\n* Scavenging Mission\n* Portal Mission",
        uniqueName="mainMenu",
        myEmoji="\U0001F3E0",
        imageURL="https://media.discordapp.net/attachments/886469391548559372/1273164687847985205/image.png?ex=66bd9e83&is=66bc4d03&hm=17098b12936cc89fca3476cc8f5888b94e21b3ba1fce5cc222000cd948b0348b&=&format=webp&quality=lossless"
    )
    how_to_play_menu.add_option(main_menu)

    party_members = Menu(
        myOptionText="Party Members",
        bodyText="$characters",
        uniqueName="partyMembers",
        myEmoji="\U0001F465",
        parent=main_menu,
        imageURL="https://media.discordapp.net/attachments/886469391548559372/1273163972010446849/image.png?ex=66bd9dd9&is=66bc4c59&hm=21db64e5c101376c91e04e034b17b843940b5ef930af16d016f88dbe3f586321&=&format=webp&quality=lossless"
    )
    main_menu.add_option(party_members)

    character0 = Menu(
        myOptionText="$character0",
        bodyText="$characterOverview",
        uniqueName="character0",
        myEmoji="\U0001F464",
        parent=party_members,
        imageURL="https://media.discordapp.net/attachments/886469391548559372/1273163972010446849/image.png?ex=66bd9dd9&is=66bc4c59&hm=21db64e5c101376c91e04e034b17b843940b5ef930af16d016f88dbe3f586321&=&format=webp&quality=lossless",
        menuState=MenuState.CHARACTER
    )
    party_members.add_option(character0)

    for i in range(1, maxNumCharacters):
        character_x = copy.deepcopy(character0)
        character_x.myOptionText = "$character" + str(i)
        character_x.uniqueName = "character" + str(i)
        party_members.add_option(character_x)

    inventory = Menu(
        myOptionText="Inventory",
        bodyText="Rusty Dagger\nbat\nwater\nfood",
        uniqueName="mainInventory",
        myEmoji="\U0001F392",
        parent=main_menu,
        imageURL="https://media.discordapp.net/attachments/886469391548559372/1273177201893965907/image.png?ex=66bdaa2b&is=66bc58ab&hm=1505bd075e5edf8409110e02894652f09d4b28a6094383296a57067752661d04&=&format=webp&quality=lossless"
    )
    main_menu.add_option(inventory)

    trade_request = Menu(
        myOptionText="Trade Request",
        bodyText="use /trade @username",
        uniqueName="tradeRequest",
        myEmoji="\U0001F501",
        parent=main_menu,
        imageURL="https://media.discordapp.net/attachments/886469391548559372/1273176860305522693/image.png?ex=66bda9d9&is=66bc5859&hm=c9eb7caa7c2efc6b30a1575bcedddac7a65b8b9d340c968d4956efe767af9537&=&format=webp&quality=lossless&width=550&height=254"
    )
    main_menu.add_option(trade_request)

    return {
        new_player_menu.uniqueName: new_player_menu,
        how_to_play_menu.uniqueName: how_to_play_menu,
        main_menu.uniqueName: main_menu,
        party_members.uniqueName: party_members,
        inventory.uniqueName: inventory,
        trade_request.uniqueName: trade_request,
        character0.uniqueName: character0
    }


def SeedMenuFilesIfMissing(directory: str):
    menu_path = Path(directory)
    menu_path.mkdir(parents=True, exist_ok=True)
    if any(menu_path.glob("*.json")):
        return

    default_menus = CreateDefaultMenusGraph()
    save_menu(default_menus["newPlayerMenu"], directory)


def MenuSetup():
    global rootMenu
    global newPlayerMenu

    SeedMenuFilesIfMissing(MENU_DIRECTORY)
    menus_by_name = load_menus_from_directory(MENU_DIRECTORY)

    if "mainMenu" not in menus_by_name:
        raise ValueError("Missing required menu JSON: 'mainMenu'.")
    if "newPlayerMenu" not in menus_by_name:
        raise ValueError("Missing required menu JSON: 'newPlayerMenu'.")

    rootMenu = menus_by_name["mainMenu"]
    newPlayerMenu = menus_by_name["newPlayerMenu"]
def Initialize():
    os.makedirs(PLAYER_SAVE_DIRECTORY, exist_ok=True)

    if os.path.exists(EXISTING_PLAYERS_ROSTER_PATH):
        LoadExistingPlayersRoster(EXISTING_PLAYERS_ROSTER_PATH)

    LoadAdminWhitelist(ADMIN_WHITELIST_PATH)

    for savePath in Path(PLAYER_SAVE_DIRECTORY).glob("*.json"):
        playerID = GetIntFromStringEnd(savePath.stem)
        if playerID is not None and playerID not in existingPlayers:
            existingPlayers[playerID] = False

    MenuSetup()
    ItemSetup()
    ExampleCharacterSetup()
    PlayerSetup()



def ReplacePlaceholders(text: str, player: Player, menuState: MenuContext):

    fTitle = ""
    if player.faction:
        fTitle = player.faction.title


    characterOverview = "";

    data = {
        'nano': player.nano,
        'playerName': player.playerName,
        'factionTitle': fTitle,
        'achievementTitle': player.achievementTitle,
        'energy': int(player.energy),
        'energyCap': int(player.energyCap),
        'characters': player.GetCharacterText(),
        # Add more placeholders as needed
    }
    data.update(EMOJI_PLACEHOLDERS)

    if menuState.character is not None:
        data['characterOverview'] = menuState.character.GetCharacterOverviewText(player.nano)

    for i in range(0, maxNumCharacters):
        data["character" + str(i)] = player.GetCharacterName(i)

    # Convert text to a Template object
    template = Template(text)

    # Use safe_substitute to replace placeholders
    replaced_text = template.safe_substitute(data)
    replaced_text = ReplaceEmojiAliases(replaced_text)

    # replace double spaces which might be left. Minor issue but it bothered me.
    replaced_text = replaced_text.replace("  ", " ")

    return replaced_text

def GetVisibleChildMenus(menu: Menu, originalMessage: 'OriginalMessage'):
    visibleChildren = []
    for child_menu in menu.Options:
        properTitle = ReplacePlaceholders(child_menu.myOptionText, originalMessage.player, originalMessage.menuContext)
        if properTitle != "":
            visibleChildren.append((child_menu, properTitle))
    return visibleChildren


@dataclass
class RenderedButton:
    targetMenuName: str
    label: str
    emoji: str


@dataclass
class RenderedMenu:
    title: str
    description: str
    footer: str
    imageURL: Optional[str]
    hasBack: bool
    buttons: List[RenderedButton]


class MenuInterface(ABC):
    @property
    @abstractmethod
    def user_id(self) -> int:
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        pass

    @abstractmethod
    async def send_ephemeral(self, content: str):
        pass

    @abstractmethod
    async def before_update(self):
        pass

    @abstractmethod
    async def send_initial(self, rendered: RenderedMenu, menu: Menu, originalMessage: 'OriginalMessage'):
        pass

    @abstractmethod
    async def send_update(self, rendered: RenderedMenu, menu: Menu, originalMessage: 'OriginalMessage'):
        pass


def BuildRenderedMenu(menu: Menu, originalMessage: 'OriginalMessage', displayName: str):
    originalMessage.player.GetCurrentEnergy(persist=True)
    replacedTitle = ReplacePlaceholders(menu.myOptionText, originalMessage.player, originalMessage.menuContext)
    replacedBody = ReplacePlaceholders(menu.bodyText, originalMessage.player, originalMessage.menuContext)
    buttons = [
        RenderedButton(targetMenuName=child.uniqueName, label=label, emoji=child.myEmoji or "")
        for child, label in GetVisibleChildMenus(menu, originalMessage)
    ]

    return RenderedMenu(
        title=replacedTitle,
        description=replacedBody,
        footer=f"{displayName}'s Menu",
        imageURL=menu.imageURL if hasattr(menu, "imageURL") else None,
        hasBack=menu.parent is not None,
        buttons=buttons
    )


def BuildDiscordEmbed(rendered: RenderedMenu):
    embed = discord.Embed(title=rendered.title, description=rendered.description)
    embed.set_footer(text=rendered.footer)
    if rendered.imageURL:
        embed.set_image(url=rendered.imageURL)
    return embed


class DiscordMenuInterface(MenuInterface):
    def __init__(self, interaction: discord.Interaction):
        self.interaction = interaction

    @property
    def user_id(self) -> int:
        return self.interaction.user.id

    @property
    def display_name(self) -> str:
        return self.interaction.user.nick or self.interaction.user.display_name

    async def send_ephemeral(self, content: str):
        await self.interaction.response.send_message(content=content, ephemeral=True)

    async def before_update(self):
        await self.interaction.response.defer()

    async def send_initial(self, rendered: RenderedMenu, menu: Menu, originalMessage: 'OriginalMessage'):
        embed = BuildDiscordEmbed(rendered)
        view = SimpleMenu(current_menu=menu, originalMessage=originalMessage)
        await self.interaction.response.send_message(embed=embed, view=view)
        originalMessage.setMessageObject(await self.interaction.original_response())

    async def send_update(self, rendered: RenderedMenu, menu: Menu, originalMessage: 'OriginalMessage'):
        embed = BuildDiscordEmbed(rendered)
        view = SimpleMenu(current_menu=menu, originalMessage=originalMessage)
        await originalMessage.message.edit(embed=embed, view=view)


class ConsoleMenuInterface(MenuInterface):
    def __init__(self, user_id: int, display_name: str = "IntegrationTester"):
        self._user_id = user_id
        self._display_name = display_name

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def display_name(self) -> str:
        return self._display_name

    async def send_ephemeral(self, content: str):
        print(f"[EPHEMERAL] {content}")

    async def before_update(self):
        return

    @staticmethod
    def _safe_text(text):
        return str(text).encode("ascii", "backslashreplace").decode("ascii")

    def _print_render(self, rendered: RenderedMenu):
        print("[MENU]")
        print(f"Title: {self._safe_text(rendered.title)}")
        print(f"Body:\n{self._safe_text(rendered.description)}")
        print(f"Footer: {self._safe_text(rendered.footer)}")
        if rendered.imageURL:
            print(f"Image: {self._safe_text(rendered.imageURL)}")
        if rendered.hasBack:
            print("Button: back")
        for button in rendered.buttons:
            safe_label = self._safe_text(button.label)
            safe_emoji = self._safe_text(button.emoji)
            print(f"Button: {button.targetMenuName} label='{safe_label}' emoji='{safe_emoji}'")
        print("")

    async def send_initial(self, rendered: RenderedMenu, menu: Menu, originalMessage: 'OriginalMessage'):
        self._print_render(rendered)

    async def send_update(self, rendered: RenderedMenu, menu: Menu, originalMessage: 'OriginalMessage'):
        self._print_render(rendered)

class OriginalMessage:
    def __init__(self, player: Player):
        self.player = player
        self.message = None
        self.menuContext = MenuContext()

    def setMessageObject(self, message: discord.Message):
        self.message = message


async def display_menu(interaction: discord.Interaction, menu: Menu):
    interface = DiscordMenuInterface(interaction)
    await display_menu_with_interface(interface, menu)


async def display_menu_with_interface(interface: MenuInterface, menu: Menu):
    player = await GetPlayer(interface.user_id)
    originalMessage = OriginalMessage(player)
    activeMenu = menu
    if player.isNewPlayer:
        originalMessage.menuContext.menuState = MenuState.NEW_PLAYER
        activeMenu = newPlayerMenu
        player.isNewPlayer = False

    UpdateMenuValues(originalMessage, activeMenu)
    rendered = BuildRenderedMenu(activeMenu, originalMessage, interface.display_name)
    await interface.send_initial(rendered, activeMenu, originalMessage)
    return originalMessage, activeMenu


def UpdateMenuValues(originalMessage: OriginalMessage, menu: Menu):
    # check for updated variables
    originalMessage.menuContext.menuState = menu.menuState
    if menu.menuState == MenuState.CHARACTER:
        characterIndex = GetIntFromStringEnd(menu.uniqueName)
        if characterIndex is None:
            characterIndex = 0
        originalMessage.menuContext.character = originalMessage.player.GetCharacter(characterIndex)


async def update_menu(interaction: discord.Interaction, menu: Menu, originalMessage: OriginalMessage):
    interface = DiscordMenuInterface(interaction)
    await update_menu_with_interface(interface, menu, originalMessage)


async def update_menu_with_interface(interface: MenuInterface, menu: Menu, originalMessage: OriginalMessage):
    if interface.user_id != originalMessage.player.discordID:
        await interface.send_ephemeral(content="You can only interact with your own menus. use /menu to open your menu.")
        return menu

    await interface.before_update()
    UpdateMenuValues(originalMessage, menu)
    rendered = BuildRenderedMenu(menu, originalMessage, interface.display_name)
    await interface.send_update(rendered, menu, originalMessage)

    return menu






################################
#                              #
#           Buttons            #
#                              #
################################

class SimpleMenu(discord.ui.View):
    def __init__(self, current_menu: Menu, originalMessage: OriginalMessage):
        super().__init__(timeout=86400)  # (timeout=86400) 1 day in seconds. (timeout=None) No timeout, making buttons persistent
        self.current_menu = current_menu

        # Add a back button if there's a parent menu
        if self.current_menu.parent is not None:
            self.add_item(BackButton(menu=self.current_menu, originalMessage=originalMessage))

        # Add buttons for each child menu
        for child_menu, properTitle in GetVisibleChildMenus(self.current_menu, originalMessage):
            self.add_item(MenuButton(child_menu, originalMessage, properTitle))

class MenuButton(discord.ui.Button):
    def __init__(self, menu: Menu, originalMessage: OriginalMessage, properTitle: str):
        super().__init__(label=properTitle, emoji=menu.myEmoji or "", style=discord.ButtonStyle.primary)
        self.menu = menu
        self.originalMessage = originalMessage

    async def callback(self, interaction: discord.Interaction):
        # When the button is pressed, display the new menu
        await update_menu(interaction, self.menu, self.originalMessage)

class BackButton(discord.ui.Button):
    def __init__(self, menu: Menu, originalMessage: OriginalMessage):
        super().__init__(label="Back", emoji="\U0001F519", style=discord.ButtonStyle.secondary)
        self.menu = menu
        self.originalMessage = originalMessage

    async def callback(self, interaction: discord.Interaction):
        # When the back button is pressed, display the parent menu
        if self.menu.parent:
            await update_menu(interaction, self.menu.parent, self.originalMessage)





################################
#                              #
#          Commands            #
#                              #
################################


# Create the slash command using app_commands
@app_commands.command(name="play", description="Displays an interactive menu")
async def play_command(interaction: discord.Interaction):
    # embed = discord.Embed(title="Menu", description="Press the button below")
    await display_menu(interaction, rootMenu)

@app_commands.command(name="menu", description="Displays an interactive menu")
async def menu_command(interaction: discord.Interaction):
    # embed = discord.Embed(title="Menu", description="Press the button below")
    await display_menu(interaction, rootMenu)


set_group = app_commands.Group(name="set", description="Admin-only set commands")

@set_group.command(name="energy", description="Set a player's energy")
@app_commands.describe(discord_user="Player to update", value="New energy value")
async def set_energy_command(interaction: discord.Interaction, discord_user: discord.Member, value: int):
    if not IsDevelopmentAdmin(interaction.user.id):
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return

    targetPlayer = await GetPlayer(discord_user.id)
    clampedValue = max(0, min(int(targetPlayer.energyCap), int(value)))
    targetPlayer.energy = float(clampedValue)
    targetPlayer.energyLastCalculatedTime = time.time()
    targetPlayer.Save()

    await interaction.response.send_message(
        f"Set energy for <@{discord_user.id}> to {int(targetPlayer.energy)}/{int(targetPlayer.energyCap)}.",
        ephemeral=True
    )


################################
#                              #
#          Bot Start           #
#                              #
################################

# Sync the command with the specific guild when the bot is ready

@bot.event
async def on_ready():
    global guild
    guild_ref = discord.Object(id=GUILD_ID)

    # Register/sync commands against a guild reference object.
    bot.tree.add_command(play_command, guild=guild_ref)
    bot.tree.add_command(menu_command, guild=guild_ref)
    bot.tree.add_command(set_group, guild=guild_ref)
    await bot.tree.sync(guild=guild_ref)

    # Keep a real Guild object (when available) for member nickname lookups.
    guild = bot.get_guild(GUILD_ID) if hasattr(bot, "get_guild") else None

    Initialize()
    print(f"Bot is ready and commands are synced with guild {GUILD_ID}")


TOKEN = os.getenv('BOT_TOKEN')
if __name__ == "__main__":
    bot.run(TOKEN)
