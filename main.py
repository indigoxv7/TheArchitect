import copy
import discord
from discord import app_commands
from discord.ext import commands
from string import Template
import re
from player_functions import *
import os
from dotenv import load_dotenv


# Load the .env file
load_dotenv()

GUILD_ID = 288770050448424971
# Create the bot with the required intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
guild = None

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
    member = await guildObj.fetch_member(discord_id)
    return member.nick or member.display_name

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
nanoEmoji = "<:Nano:1274243202773418024>"

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

    PhysResistBonus = [AttributeBonus(Attribute.PHYSICAL_RESISTANCE, 1)]

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
    testPlayer = Player(191980469670248448, 10000, 3, TitlePreference.Masculine, exampleCharacters)
    testPlayer.isNewPlayer = True
    testPlayer.playerName = "Wasabi Avenger"
    playerList[testPlayer.discordID] = testPlayer

# gets a player object from our playerList. if the player does not exist, create it.
async def GetPlayer(id: int):
    # Check if the player is already loaded
    if id in playerList:
        return playerList[id]

    # Check if the player has a save file
    if id in existingPlayers:
        # Mark the player as loaded and load the player object
        existingPlayers[id] = True
        p = load_player("./PlayerData/" + str(id) + ".pkl")
        nickname = await GetNameFromID(guild, id) # we refresh player nickname each time they are loaded.
        p.playerName = nickname
        playerList[id] = p
        return p

    # If the player doesn't exist, create a new player
    new_player = CreateNewPlayer(id)
    existingPlayers[id] = True
    SaveExistingPlayersRoster("./ExistingPlayersRoster.json")
    nickname = await GetNameFromID(guild, id)
    new_player.playerName = nickname
    playerList[id] = new_player
    save_player(new_player, "./PlayerData/" + str(id) + ".pkl")
    new_player.isNewPlayer = True
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
def MenuSetup():
    global rootMenu
    global newPlayerMenu

    newPlayerMenu = Menu(
        myOptionText="Welcome to the collective $playerName!",
        bodyText="Your species has been chosen by the Architect to join countless others on a path to power. As a member of the Collective, you will use nano to enhance your body, gain access to combat classifications, "
                 "and harness power previously unknown."
                 "\n\nDon’t get caught up in the game-like system though. If your character dies, they’re gone for good. Be "
                 "careful and choose wisely, as even a small miscalculation in planning can lead to the end.",
        uniqueName="newPlayerMenu",
        myEmoji="🌟",
        imageURL="https://media.discordapp.net/attachments/886469391548559372/1274236983559979050/image.png?ex=66c1852b&is=66c033ab&hm=82c9b63ad2903e31659408b2057e488d6a4f9f0d82c7bdb12da34e477e7af077&=&format=webp&quality=lossless"
    )

    HowToPlayMenu = Menu(
        myOptionText="How to play",
        bodyText="The apocalypse has begun. It’s a harsh place out here, and to protect yourself and those around you, you’ll need to form a **Faction.**\n\n"
                 "Only problem is that costs " + nanoEmoji + " **Nano.** Lots of it.\n\nSo before you can do that, you’ll need to go on missions to get stronger and gather resources.\n\n"
                 "There are two types of missions. **Scavenging Missions**, in which you will face off against roaming monsters and bandits on earth, and **Portal Missions**, "
                 "in which you enter a scenario in another world and must complete the objective given to you by the architect.\n\nStart with **Scavenging Missions**. "
                 "They give fewer rewards, but you at least have a chance to run if it gets too dangerous. There is no escape if you fail a **Portal Mission**. \n\n"
                 "Check your **Character**’s gear before you start and make sure you’re bringing your best stuff.\n\n"
                 "# Good luck!",
        uniqueName="HowToPlayMenu",
        myEmoji="🌟",
        imageURL="https://media.discordapp.net/attachments/886469391548559372/1274239069127180338/Portal.png?ex=66c1871c&is=66c0359c&hm=d3c39e8d6175df24827f2da43b294f65ec5f5017da0e04d8330557ceffee82cb&=&format=webp&quality=lossless&width=1920&height=555"
    )
    newPlayerMenu.add_option(HowToPlayMenu)

    rootMenu = Menu(
        myOptionText="Main Menu - $factionTitle $playerName $achievementTitle",
        bodyText="Nano: " + nanoEmoji + "$nano\n\n* Faction (Not founded)\n* Party Members\n* Inventory\n\n* Make trade request\n* Pending Notifications (0)\n\n* Scavenging Mission\n* Portal Mission",
        uniqueName="mainMenu",
        myEmoji="🏠",
        imageURL="https://media.discordapp.net/attachments/886469391548559372/1273164687847985205/image.png?ex=66bd9e83&is=66bc4d03&hm=17098b12936cc89fca3476cc8f5888b94e21b3ba1fce5cc222000cd948b0348b&=&format=webp&quality=lossless"
    )
    HowToPlayMenu.add_option(rootMenu)

    ########### party
    partyMembers = Menu(
        myOptionText="Party Members",
        bodyText="$characters",
        uniqueName="partyMembers",
        myEmoji="👥",
        parent=rootMenu,
        imageURL="https://media.discordapp.net/attachments/886469391548559372/1273163972010446849/image.png?ex=66bd9dd9&is=66bc4c59&hm=21db64e5c101376c91e04e034b17b843940b5ef930af16d016f88dbe3f586321&=&format=webp&quality=lossless"
    )
    rootMenu.add_option(partyMembers)

    character0 = Menu(
        myOptionText="$character0",
        bodyText="Combat Classification - $combatClassification\n\nChi - $chiAffinity\nMana - $manaAffinity\nPsi - $psiAffinity\nAether - $aetherAffinity"
                 "\n\nRace - $raceTier\n\nAttributes - Increased by $attributePercentIncrease\nAttributes -\nPhysical Power - $physicalPower\n"
                 "Physical Stamina - $physicalStamina\nPhysical Resistance - $physicalResistance\nMagic Power - $magicPower\nMagic Stamina - $magicStamina\n"
                 "Magic Resistance - $magicResistance\n\nAchievements -\n$achievements\n\nGeneral Skills - \n$generalSkills\n\nPooled Nano " + nanoEmoji + " - $nano",
        uniqueName="character0",
        myEmoji="👤",
        parent=partyMembers,
        imageURL="https://media.discordapp.net/attachments/886469391548559372/1273163972010446849/image.png?ex=66bd9dd9&is=66bc4c59&hm=21db64e5c101376c91e04e034b17b843940b5ef930af16d016f88dbe3f586321&=&format=webp&quality=lossless"
    )
    partyMembers.add_option(character0)

    # create the other character menus as a copy of the one above, but with the different title variables.
    for i in range(1, maxNumCharacters): # starting at 1 up to but not including maxNumCharacters
        characterX = copy.deepcopy(character0)
        characterX.myOptionText = "$character" + str(i)
        characterX.uniqueName = "$character" + str(i)
        partyMembers.add_option(characterX)

    ###################

    inventory = Menu(
        myOptionText="Inventory",
        bodyText="Rusty Dagger\nbat\nwater\nfood",
        uniqueName="mainInventory",
        myEmoji="🎒",
        parent=rootMenu,
        imageURL="https://media.discordapp.net/attachments/886469391548559372/1273177201893965907/image.png?ex=66bdaa2b&is=66bc58ab&hm=1505bd075e5edf8409110e02894652f09d4b28a6094383296a57067752661d04&=&format=webp&quality=lossless"
    )
    rootMenu.add_option(inventory)

    tradeRequest = Menu(
        myOptionText="Trade Request",
        bodyText="use /trade @username",
        uniqueName="tradeRequest",
        myEmoji="🔁",
        parent=rootMenu,
        imageURL="https://media.discordapp.net/attachments/886469391548559372/1273176860305522693/image.png?ex=66bda9d9&is=66bc5859&hm=c9eb7caa7c2efc6b30a1575bcedddac7a65b8b9d340c968d4956efe767af9537&=&format=webp&quality=lossless&width=550&height=254"
    )
    rootMenu.add_option(tradeRequest)


def Initialize():
    MenuSetup()
    ItemSetup()
    ExampleCharacterSetup()
    PlayerSetup()




def ReplacePlaceholders(text: str, player: Player, menuState: MenuContext):

    fTitle = ""
    if player.faction:
        fTitle = player.faction.title

    data = {
        'nano': player.nano,
        'playerName': player.playerName,
        'factionTitle': fTitle,
        'achievementTitle': player.achievementTitle,
        'characters': player.GetCharacterText(),
        # 'attributeAffinities':
        #'character0': player.GetCharacterName(0),
        #'character1': player.GetCharacterName(1),
        #'character2': player.GetCharacterName(2),
        #'character3': player.GetCharacterName(3),
        # Add more placeholders as needed
    }

    for i in range(0, maxNumCharacters):
        data["character" + str(i)] = player.GetCharacterName(i)

    # Convert text to a Template object
    template = Template(text)

    # Use safe_substitute to replace placeholders
    replaced_text = template.safe_substitute(data)

    # replace double spaces which might be left. Minor issue but it bothered me.
    replaced_text = replaced_text.replace("  ", " ")

    return replaced_text

def MakeMenuEmbed(interaction: discord.Interaction, menu: Menu, player: Player, menuState: MenuContext):
    replacedTitle = ReplacePlaceholders(menu.myOptionText, player, menuState)
    replacedBody = ReplacePlaceholders(menu.bodyText, player, menuState)
    embed = discord.Embed(title=replacedTitle, description=replacedBody)
    embed.set_footer(text=interaction.user.nick or interaction.user.display_name + "'s Menu")
    # Add the footer image if imageURL is not None
    if hasattr(menu, 'imageURL') and menu.imageURL:
        embed.set_image(url=menu.imageURL)
    return embed

class OriginalMessage:
    def __init__(self, player: Player):
        self.player = player
        self.message = None
        self.menuContext = MenuContext()

    def setMessageObject(self, message: discord.Message):
        self.message = message


async def display_menu(interaction: discord.Interaction, menu: Menu):
    # Create the embed
    player = await GetPlayer(interaction.user.id)

    # create our save class for the original message for editing and making sure nobody but the original user messes with it.
    originalMessage = OriginalMessage(player)
    if player.isNewPlayer: # If they're a new player we have an intro menu for them.
        originalMessage.menuContext.menuState = MenuState.NEW_PLAYER
        menu = newPlayerMenu
        player.isNewPlayer = False

    if menu.menuState == MenuState.CHARACTER:
        index = GetNameFromID(menu.myOptionText)
        originalMessage.menuContext.character = player.GetCharacter(index)

    embed = MakeMenuEmbed(interaction, menu, player, originalMessage.menuContext)

    # Create an instance of SimpleMenu with the current menu
    view = SimpleMenu(current_menu=menu, originalMessage=originalMessage)

    await interaction.response.send_message(embed=embed, view=view)
    originalMessage.setMessageObject(await interaction.original_response())



async def update_menu(interaction: discord.Interaction, menu: Menu, originalMessage: OriginalMessage):
    if interaction.user.id != originalMessage.player.discordID:
        await interaction.response.send_message(content="You can only interact with your own menus. use /menu to open your menu.", ephemeral=True)
        return

    # Acknowledge the interaction first to prevent timeout
    await interaction.response.defer()

    # Create the embed
    embed = MakeMenuEmbed(interaction, menu, originalMessage.player, originalMessage.menuContext)

    # Create an instance of SimpleMenu with the current menu
    view = SimpleMenu(menu, originalMessage)

    await originalMessage.message.edit(embed=embed, view=view)






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
        for child_menu in self.current_menu.Options:
            properTitle = ReplacePlaceholders(child_menu.myOptionText, originalMessage.player, originalMessage.menuContext)
            if properTitle != "": # do not display menus that are intentionally hidden.
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
        super().__init__(label="Back", emoji="🔙", style=discord.ButtonStyle.secondary)
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
async def menu(interaction: discord.Interaction):
    # embed = discord.Embed(title="Menu", description="Press the button below")
    await display_menu(interaction, rootMenu)

@app_commands.command(name="menu", description="Displays an interactive menu")
async def menu(interaction: discord.Interaction):
    # embed = discord.Embed(title="Menu", description="Press the button below")
    await display_menu(interaction, rootMenu)


################################
#                              #
#          Bot Start           #
#                              #
################################

# Sync the command with the specific guild when the bot is ready

@bot.event
async def on_ready():
    global guild
    guild = discord.Object(id=GUILD_ID)
    bot.tree.add_command(menu, guild=guild)  # Register the command with the guild
    await bot.tree.sync(guild=guild)  # Sync the command with the guild
    Initialize()
    print(f"Bot is ready and commands are synced with guild {GUILD_ID}")


TOKEN = os.getenv('BOT_TOKEN')
bot.run(TOKEN)
