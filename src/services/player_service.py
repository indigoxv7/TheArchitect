import copy
import os
import re
from typing import Optional

from src.domain.CharacterUtil import (
    DEFAULT_DURABILITY,
    Attribute,
    AttributeBonus,
    Bonus,
    BonusType,
    ConsumableKind,
    DamageType,
    EquipSlot,
    ItemType,
    PowerType,
)
from src.domain.Items import Armor, Consumable, Item, Weapon
from src.domain.MainCharacter import MainCharacter
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
        self.campaign_service = None

    def set_guild(self, guild_obj):
        self.context.guild = guild_obj

    def set_campaign_service(self, campaign_service):
        self.campaign_service = campaign_service

    @staticmethod
    def get_int_from_string_end(string: str) -> Optional[int]:
        match = re.search(r"\d+$", string)
        return int(match.group()) if match else None

    @staticmethod
    def _slugify_name(name: str) -> str:
        compact = re.sub(r"\s+", "", str(name or "").strip())
        compact = re.sub(r"[^A-Za-z0-9_\-]", "", compact)
        return compact or "Character"

    def _generate_player_instance_id(self, existing_characters: list, name: str) -> str:
        prefix = self._slugify_name(name)
        used_ids = {
            str(getattr(character, "playerInstanceId", "") or "")
            for character in existing_characters
            if character is not None
        }
        index = len(used_ids)
        candidate = f"{prefix}{index}"
        while candidate in used_ids:
            index += 1
            candidate = f"{prefix}{index}"
        return candidate

    def _clone_character_for_player(self, character, existing_characters: list | None = None):
        clone = copy.deepcopy(character)
        ensure_defaults = getattr(clone, "EnsureRuntimeDefaults", None)
        if callable(ensure_defaults):
            ensure_defaults()
        clone.playerInstanceId = self._generate_player_instance_id(
            existing_characters or [], getattr(clone, "name", "Character")
        )
        return clone

    def clone_character_from_template(self, character_identifier: str, existing_characters: list | None = None):
        template = self.context.all_characters.get(str(character_identifier or "").strip())
        if template is None:
            return None
        return self._clone_character_for_player(template, existing_characters)

    def _normalize_player_characters(self, player: Player) -> bool:
        characters = getattr(player, "characters", []) or []
        normalized = []
        migrated = False
        used_ids: set[str] = set()
        legacy_selected_ids: list[str] = []
        global_templates = list(self.context.all_characters.values())

        for entry in characters:
            character = entry
            if isinstance(entry, str):
                template = self.context.all_characters.get(entry)
                if template is None:
                    migrated = True
                    continue
                character = self._clone_character_for_player(template, normalized)
                migrated = True
            elif any(entry is template for template in global_templates):
                character = self._clone_character_for_player(entry, normalized)
                migrated = True

            legacy_party = getattr(character, "party", None)
            ensure_defaults = getattr(character, "EnsureRuntimeDefaults", None)
            if callable(ensure_defaults):
                ensure_defaults()

            player_instance_id = str(getattr(character, "playerInstanceId", "") or "")
            if not player_instance_id or player_instance_id in used_ids:
                character.playerInstanceId = self._generate_player_instance_id(
                    normalized, getattr(character, "name", "Character")
                )
                player_instance_id = str(getattr(character, "playerInstanceId", "") or "")
                migrated = True

            if legacy_party is not None:
                try:
                    if int(legacy_party) == 0:
                        legacy_selected_ids.append(player_instance_id)
                except Exception:
                    pass
                if hasattr(character, "party"):
                    delattr(character, "party")
                migrated = True

            if isinstance(character, MainCharacter):
                character.EnsureRuntimeDefaults()
            elif hasattr(character, "stats"):
                delattr(character, "stats")
                migrated = True

            used_ids.add(player_instance_id)
            normalized.append(character)

        if normalized != characters:
            player.characters = normalized
            migrated = True

        valid_ids = {
            str(getattr(character, "playerInstanceId", "") or "")
            for character in player.characters
            if str(getattr(character, "playerInstanceId", "") or "")
        }
        current_party = [
            str(entry or "").strip()
            for entry in getattr(player, "missionPartyCharacterIds", []) or []
            if str(entry or "").strip() in valid_ids
        ]
        if current_party != list(getattr(player, "missionPartyCharacterIds", []) or []):
            migrated = True
        if not current_party and valid_ids:
            current_party = [entry for entry in legacy_selected_ids if entry in valid_ids] or sorted(valid_ids)
            migrated = True
        player.missionPartyCharacterIds = current_party
        return migrated

    def _normalize_loaded_player(self, player: Player) -> bool:
        player._ensure_runtime_defaults()
        migrated = self._normalize_player_characters(player)
        if self.campaign_service is not None:
            migrated = self.campaign_service.ensure_player_progress(player) or migrated
        return migrated

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

        phys_resist_bonus = [
            Bonus(BonusType.FLAT, AttributeBonus(Attribute.PHYSICAL_RESISTANCE, 1), None, 0, "")
        ]

        default_items = [
            Weapon("Dagger", EquipSlot.PRIMARY_WEAPON, 0, DEFAULT_DURABILITY, None, ItemType.MELEE_THROWABLE, [DamageType.PIERCING], 9, 12, 0.9, 0.10, 4),
            Weapon("Spear", EquipSlot.PRIMARY_WEAPON, 0, DEFAULT_DURABILITY, None, ItemType.MELEE_WEAPON, [DamageType.PIERCING], 11, 15, 1.1, 0.05, 6),
            Weapon("Sword", EquipSlot.PRIMARY_WEAPON, 0, DEFAULT_DURABILITY, None, ItemType.MELEE_WEAPON, [DamageType.SLASHING], 12, 16, 1.0, 0.0, 5),
            Weapon("Warhammer", EquipSlot.PRIMARY_WEAPON, 0, DEFAULT_DURABILITY, None, ItemType.MELEE_WEAPON, [DamageType.BLUDGEONING], 13, 18, 1.35, 0.0, 8),
            Weapon("Bow", EquipSlot.PRIMARY_WEAPON, 0, DEFAULT_DURABILITY, None, ItemType.RANGED_WEAPON, [DamageType.PIERCING], 10, 14, 0.8, 0.10, 4),
            Armor("Shield", EquipSlot.OFFHAND, 0, 40, phys_resist_bonus, ItemType.ARMOR, maxArmor=40, currentArmor=40),
            Armor("Helmet", EquipSlot.HEAD, 0, 30, phys_resist_bonus, ItemType.ARMOR, maxArmor=30, currentArmor=30),
            Item("Necklace", EquipSlot.NECK, 0, DEFAULT_DURABILITY, phys_resist_bonus, ItemType.DEFAULT),
            Armor("Body Armor", EquipSlot.BODY, 0, 60, phys_resist_bonus, ItemType.ARMOR, maxArmor=60, currentArmor=60),
            Armor("Gloves", EquipSlot.HANDS, 0, 20, phys_resist_bonus, ItemType.ARMOR, maxArmor=20, currentArmor=20),
            Item("Ring", EquipSlot.RING, 0, DEFAULT_DURABILITY, phys_resist_bonus, ItemType.DEFAULT),
            Armor("Pants", EquipSlot.LEGS, 0, 35, phys_resist_bonus, ItemType.ARMOR, maxArmor=35, currentArmor=35),
            Armor("Boots", EquipSlot.FEET, 0, 25, phys_resist_bonus, ItemType.ARMOR, maxArmor=25, currentArmor=25),
            Consumable("Bandage", 0, None, ConsumableKind.POTION, effectPowerType=PowerType.CONSUMABLE_POWER, effectPower=10),
            Item("Paperclip", EquipSlot.NOT_EQUIPABLE, 0, DEFAULT_DURABILITY, None, ItemType.DEFAULT),
        ]

        for new_item in default_items:
            self.context.all_items[new_item.name] = new_item

        self.context.error_item = Item("[ERROR MISSING ITEM]", EquipSlot.NOT_EQUIPABLE, 0, DEFAULT_DURABILITY, None, ItemType.DEFAULT)
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
            migrated = self._normalize_loaded_player(player)
            player.AttachSavePath(player_save_path, enableAutoSave=True)
            nickname = await self.get_name_from_id(self.context.guild, discord_id)
            player.playerName = nickname
            if migrated:
                player.Save()
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

        migrated = self._normalize_loaded_player(player)
        player.AttachSavePath(player_save_path, enableAutoSave=True)
        if migrated:
            player.Save()
        self.context.existing_players[discord_id] = True
        self.context.player_cache[discord_id] = player
        return player

    def persist_player(self, player: Player):
        discord_id = int(getattr(player, "discordID", 0))
        if discord_id <= 0:
            raise ValueError("Player must have a valid discordID before saving.")

        self._normalize_loaded_player(player)
        player_save_path = self.get_player_save_path(discord_id)
        player.AttachSavePath(player_save_path, enableAutoSave=getattr(player, "_auto_save_enabled", True))
        player.Save()
        self.context.existing_players[discord_id] = True
        self.context.player_cache[discord_id] = player
        self.save_existing_players_roster(self.existing_players_roster_path)

    def list_player_main_characters(self, player: Player) -> list:
        result = []
        for character in getattr(player, "characters", []) or []:
            if isinstance(character, MainCharacter):
                result.append(character)
        return result
