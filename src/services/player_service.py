import os
import re
from typing import Optional

from src.domain.CharacterUtil import (
    DEFAULT_DURABILITY,
    Attribute,
    AttributeBonus,
    Bonus,
    BonusType,
    DamageType,
    EquipSlot,
    ItemPower,
    ItemType,
    PowerType,
)
from src.domain.Items import Item
from src.domain.player_functions import Player, load_player
from src.persistence.roster_store import ExistingPlayersRosterStore
from src.services.game_context import GameContext


class PlayerService:
    def __init__(
        self,
        bot,
        guild_id: int,
        context: GameContext,
        player_save_directory: str = "./PlayerSaves",
        existing_players_roster_path: str = "./ExistingPlayersRoster.json",
    ):
        self.bot = bot
        self.guild_id = guild_id
        self.context = context
        self.player_save_directory = player_save_directory
        self.existing_players_roster_path = existing_players_roster_path
        self.roster_store = ExistingPlayersRosterStore(
            roster_path=existing_players_roster_path,
            player_save_directory=player_save_directory,
        )

    def set_guild(self, guild_obj):
        self.context.guild = guild_obj

    @staticmethod
    def get_int_from_string_end(string: str) -> Optional[int]:
        match = re.search(r"\d+$", string)
        return int(match.group()) if match else None

    async def get_name_from_id(self, guild_obj, discord_id: int) -> str:
        candidate_guild = guild_obj or self.context.guild

        if candidate_guild is None and hasattr(self.bot, "get_guild"):
            candidate_guild = self.bot.get_guild(self.guild_id)

        if candidate_guild is not None and hasattr(candidate_guild, "fetch_member"):
            try:
                member = await candidate_guild.fetch_member(discord_id)
                return member.nick or member.display_name
            except Exception:
                pass

        if hasattr(self.bot, "get_user"):
            cached_user = self.bot.get_user(discord_id)
            if cached_user is not None:
                return getattr(cached_user, "display_name", None) or cached_user.name

        if hasattr(self.bot, "fetch_user"):
            try:
                user = await self.bot.fetch_user(discord_id)
                return getattr(user, "display_name", None) or user.name
            except Exception:
                pass

        return str(discord_id)

    def get_player_save_path(self, discord_id: int) -> str:
        return os.path.join(self.player_save_directory, f"{discord_id}.json")

    def save_existing_players_roster(self, filename: Optional[str] = None):
        if filename is not None and filename != self.existing_players_roster_path:
            custom_store = ExistingPlayersRosterStore(filename, self.player_save_directory)
            custom_store.save_roster(self.context.existing_players)
            return
        self.roster_store.save_roster(self.context.existing_players)

    def load_existing_players_roster(self, filename: Optional[str] = None):
        if filename is not None and filename != self.existing_players_roster_path:
            custom_store = ExistingPlayersRosterStore(filename, self.player_save_directory)
            loaded = custom_store.load_roster()
        else:
            loaded = self.roster_store.load_roster()

        self.context.existing_players.clear()
        self.context.existing_players.update(loaded)

    def initialize_storage(self):
        self.roster_store.ensure_save_directory()

        if self.roster_store.roster_exists():
            self.load_existing_players_roster()

        for player_id in self.roster_store.discover_save_ids():
            if player_id not in self.context.existing_players:
                self.context.existing_players[player_id] = False

        self.item_setup()

    def item_setup(self):
        self.context.all_items.clear()
        self.context.error_item = None

        standard_attack_power = [ItemPower(PowerType.PHYSICAL_ATTACK, 12)]
        piercing_damage = [DamageType.PIERCING]
        bludgeoning_damage = [DamageType.BLUDGEONING]
        slashing_damage = [DamageType.SLASHING]
        standard_consumable_power = [ItemPower(PowerType.CONSUMABLE_POWER, 10)]

        phys_resist_bonus = [
            Bonus(BonusType.FLAT, AttributeBonus(Attribute.PHYSICAL_RESISTANCE, 1), None, 0, "")
        ]

        new_item = Item("Dagger", EquipSlot.HANDS, 0, DEFAULT_DURABILITY, None, ItemType.MELEE_THROWABLE, standard_attack_power, piercing_damage)
        self.context.all_items[new_item.name] = new_item
        new_item = Item("Spear", EquipSlot.HANDS, 0, DEFAULT_DURABILITY, None, ItemType.MELEE_WEAPON, standard_attack_power, piercing_damage)
        self.context.all_items[new_item.name] = new_item
        new_item = Item("Sword", EquipSlot.HANDS, 0, DEFAULT_DURABILITY, None, ItemType.MELEE_WEAPON, standard_attack_power, slashing_damage)
        self.context.all_items[new_item.name] = new_item
        new_item = Item("Warhammer", EquipSlot.HANDS, 0, DEFAULT_DURABILITY, None, ItemType.MELEE_WEAPON, standard_attack_power, bludgeoning_damage)
        self.context.all_items[new_item.name] = new_item
        new_item = Item("Bow", EquipSlot.HANDS, 0, DEFAULT_DURABILITY, None, ItemType.RANGED_WEAPON, standard_attack_power, piercing_damage)
        self.context.all_items[new_item.name] = new_item
        new_item = Item("Shield", EquipSlot.HANDS, 0, DEFAULT_DURABILITY, phys_resist_bonus, ItemType.MELEE_WEAPON, None, None)
        self.context.all_items[new_item.name] = new_item

        new_item = Item("Helmet", EquipSlot.HEAD, 0, DEFAULT_DURABILITY, phys_resist_bonus, ItemType.ARMOR, None, None)
        self.context.all_items[new_item.name] = new_item
        new_item = Item("Necklace", EquipSlot.NECK, 0, DEFAULT_DURABILITY, phys_resist_bonus, ItemType.ARMOR, None, None)
        self.context.all_items[new_item.name] = new_item
        new_item = Item("Body Armor", EquipSlot.BODY, 0, DEFAULT_DURABILITY, phys_resist_bonus, ItemType.ARMOR, None, None)
        self.context.all_items[new_item.name] = new_item
        new_item = Item("Gloves", EquipSlot.HANDS, 0, DEFAULT_DURABILITY, phys_resist_bonus, ItemType.ARMOR, None, None)
        self.context.all_items[new_item.name] = new_item
        new_item = Item("Ring", EquipSlot.RING, 0, DEFAULT_DURABILITY, phys_resist_bonus, ItemType.ARMOR, None, None)
        self.context.all_items[new_item.name] = new_item
        new_item = Item("Pants", EquipSlot.LEGS, 0, DEFAULT_DURABILITY, phys_resist_bonus, ItemType.ARMOR, None, None)
        self.context.all_items[new_item.name] = new_item
        new_item = Item("Boots", EquipSlot.FEET, 0, DEFAULT_DURABILITY, phys_resist_bonus, ItemType.ARMOR, None, None)
        self.context.all_items[new_item.name] = new_item

        new_item = Item("Bandage", EquipSlot.NOT_EQUIPABLE, 0, DEFAULT_DURABILITY, None, ItemType.CONSUMABLE, standard_consumable_power, None)
        self.context.all_items[new_item.name] = new_item

        new_item = Item("Paperclip", EquipSlot.NOT_EQUIPABLE, 0, DEFAULT_DURABILITY, None, ItemType.DEFAULT, None, None)
        self.context.all_items[new_item.name] = new_item
        self.context.error_item = Item("[ERROR MISSING ITEM]", EquipSlot.NOT_EQUIPABLE, 0, DEFAULT_DURABILITY, None, ItemType.DEFAULT, None, None)
        self.context.all_items[self.context.error_item.name] = self.context.error_item

    def find_item(self, name: str) -> Item:
        return self.context.all_items.get(name, self.context.error_item)

    def create_new_player(self, discord_id: int) -> Player:
        return Player(discord_id)

    async def get_player(self, discord_id: int) -> Player:
        if discord_id in self.context.player_cache:
            return self.context.player_cache[discord_id]

        player_save_path = self.get_player_save_path(discord_id)

        if os.path.exists(player_save_path):
            self.context.existing_players[discord_id] = True
            player = load_player(player_save_path)
            player.AttachSavePath(player_save_path, enableAutoSave=True)
            nickname = await self.get_name_from_id(self.context.guild, discord_id)
            player.playerName = nickname
            self.context.player_cache[discord_id] = player
            return player

        new_player = self.create_new_player(discord_id)
        new_player.AttachSavePath(player_save_path, enableAutoSave=False)
        self.context.existing_players[discord_id] = True
        self.save_existing_players_roster(self.existing_players_roster_path)
        nickname = await self.get_name_from_id(self.context.guild, discord_id)
        new_player.playerName = nickname
        new_player.isNewPlayer = True
        new_player.SetAutoSaveEnabled(True)
        new_player.Save()
        self.context.player_cache[discord_id] = new_player
        return new_player

    def list_known_player_ids(self) -> list[int]:
        ids: set[int] = set()
        ids.update(int(player_id) for player_id in self.context.existing_players.keys())
        ids.update(int(player_id) for player_id in self.context.player_cache.keys())
        ids.update(self.roster_store.discover_save_ids())
        return sorted(ids)

    def get_player_sync(self, discord_id: int) -> Player | None:
        if discord_id in self.context.player_cache:
            return self.context.player_cache[discord_id]

        player_save_path = self.get_player_save_path(discord_id)
        if not os.path.exists(player_save_path):
            return None

        try:
            player = load_player(player_save_path)
        except Exception:
            return None

        player.AttachSavePath(player_save_path, enableAutoSave=True)
        self.context.existing_players[discord_id] = True
        self.context.player_cache[discord_id] = player
        return player

    def persist_player(self, player: Player):
        discord_id = int(getattr(player, "discordID", 0))
        if discord_id <= 0:
            raise ValueError("Player must have a valid discordID before saving.")

        player_save_path = self.get_player_save_path(discord_id)
        player.AttachSavePath(player_save_path, enableAutoSave=getattr(player, "_auto_save_enabled", True))
        player.Save()
        self.context.existing_players[discord_id] = True
        self.context.player_cache[discord_id] = player
        self.save_existing_players_roster(self.existing_players_roster_path)

