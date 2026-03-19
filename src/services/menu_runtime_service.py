import json
from abc import ABC, abstractmethod

import discord

from src.bot.views.menu_view import SimpleMenu
from src.domain.CharacterUtil import DEFAULT_DURABILITY, DamageType, EquipSlot, ItemType, PowerType
from src.domain.combat import EncounterType
from src.services.game_context import GameContext
from src.services.item_service import ItemService
from src.services.menu_runtime_actions import MenuSpecialActionRouter
from src.services.menu_service import MenuService, RenderedMenu
from src.services.player_service import PlayerService
from src.services.spell_service import SpellService
from src.services.whitelist_service import AdminWhitelistService
from src.ui.menu_functions import Menu, MenuContext, MenuState


SPELL_FIELD_DEFAULTS = {
    "name": "",
    "level": "",
    "power": "",
    "affinity": "",
    "casting_time": "",
    "range": "",
    "component_verbal": False,
    "component_somatic": False,
    "component_material": False,
    "duration": "",
    "description": "",
    "higher_level": "",
}
ITEM_FIELD_DEFAULTS = {
    "name": "",
    "slot": EquipSlot.NOT_EQUIPABLE.name,
    "tier": 0,
    "durability": DEFAULT_DURABILITY,
    "item_type": ItemType.DEFAULT.name,
    "damage_type": "NONE",
    "power_type": "NONE",
    "power_value": 0,
    "power_spell_name": "",
    "stat_bonuses_json": "[]",
}


ATTRIBUTES_DRAFT_DEFAULTS = {
    "physical_power": 5,
    "physical_stamina": 5,
    "physical_resistance": 5,
    "magic_power": 5,
    "magic_stamina": 5,
    "magic_resistance": 5,
}

GEAR_DRAFT_DEFAULTS = {
    "head": "",
    "neck": "",
    "body": "",
    "hands": "",
    "ring": "",
    "legs": "",
    "feet": "",
    "primary_weapon": "",
    "offhand": "",
    "inventory_json": "[]",
}

BONUS_DRAFT_DEFAULTS = {
    "bonus_type": "FLAT",
    "attribute_bonus_json": "{}",
    "affinities_json": "{}",
    "nano_multiplier": 0.0,
    "reason": "",
    "permanent": False,
}

ACHIEVEMENT_DRAFT_DEFAULTS = {
    "name": "",
    "title": "",
    "bonus_json": "{}",
}

def _parse_non_empty_text(value: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError("Value cannot be empty.")
    return text


def _parse_level(value: str) -> int:
    text = str(value).strip()
    level = int(text)
    if level < 0:
        raise ValueError("Level must be >= 0.")
    return level



def _parse_non_negative_int(value: str) -> int:
    text = str(value).strip()
    parsed = int(text)
    if parsed < 0:
        raise ValueError("Value must be >= 0.")
    return parsed
def _parse_bool_yes_no(value: str) -> bool:
    text = str(value).strip().lower()
    if text in {"y", "yes", "true", "1"}:
        return True
    if text in {"n", "no", "false", "0"}:
        return False
    raise ValueError("Use yes/no.")


def _parse_material(value: str):
    text = str(value).strip()
    if not text:
        return False
    if text.lower() in {"none", "false", "no"}:
        return False
    return text


def _parse_optional_text(value: str):
    text = str(value).strip()
    return text if text else ""


def _parse_float(value: str) -> float:
    text = str(value).strip()
    return float(text)


def _parse_json_object(value: str) -> str:
    text = str(value).strip() or "{}"
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Value must be a JSON object.")
    return json.dumps(parsed, ensure_ascii=False)


def _parse_json_list(value: str) -> str:
    text = str(value).strip() or "[]"
    parsed = json.loads(text)
    if not isinstance(parsed, list):
        raise ValueError("Value must be a JSON array.")
    return json.dumps(parsed, ensure_ascii=False)



def _parse_stat_bonuses_json(value: str) -> str:
    text = str(value).strip() or "[]"
    parsed = json.loads(text)
    if not isinstance(parsed, list):
        raise ValueError("Stat bonuses must be a JSON array.")
    return json.dumps(parsed, ensure_ascii=False)
SPELL_FIELD_EDIT_CONFIG = {
    "spellSetNameAction": ("name", "Spell Name", _parse_non_empty_text),
    "spellSetLevelAction": ("level", "Spell Level", _parse_level),
    "spellSetPowerAction": ("power", "Power", _parse_non_empty_text),
    "spellSetAffinityAction": ("affinity", "Affinity", _parse_non_empty_text),
    "spellSetCastingTimeAction": ("casting_time", "Casting Time", _parse_non_empty_text),
    "spellSetRangeAction": ("range", "Range", _parse_non_empty_text),
    "spellSetVerbalAction": ("component_verbal", "Verbal Component (yes/no)", _parse_bool_yes_no),
    "spellSetSomaticAction": ("component_somatic", "Somatic Component (yes/no)", _parse_bool_yes_no),
    "spellSetMaterialAction": ("component_material", "Material Component (text or none)", _parse_material),
    "spellSetDurationAction": ("duration", "Duration", _parse_non_empty_text),
    "spellSetDescriptionAction": ("description", "Description", _parse_non_empty_text),
    "spellSetHigherLevelAction": ("higher_level", "Higher Level Text (optional)", _parse_optional_text),
}
ITEM_FIELD_EDIT_CONFIG = {
    "itemSetNameAction": ("itemDraft", "name", "Item Name", _parse_non_empty_text),
    "itemSetTierAction": ("itemDraft", "tier", "Item Tier", _parse_non_negative_int),
    "itemSetDurabilityAction": ("itemDraft", "durability", "Durability", _parse_non_negative_int),
    "itemSetPowerValueAction": ("itemDraft", "power_value", "Power Value", _parse_non_negative_int),
    "itemSetSpellNameAction": ("itemDraft", "power_spell_name", "Power Spell Name (optional)", _parse_optional_text),
    "itemSetStatBonusesAction": ("itemDraft", "stat_bonuses_json", "Stat Bonuses JSON", _parse_stat_bonuses_json),
}



COMPONENT_FIELD_EDIT_CONFIG = {
    "attributesSetPhysicalPowerAction": ("attributesDraft", "physical_power", "Physical Power", _parse_non_negative_int),
    "attributesSetPhysicalStaminaAction": ("attributesDraft", "physical_stamina", "Physical Stamina", _parse_non_negative_int),
    "attributesSetPhysicalResistanceAction": ("attributesDraft", "physical_resistance", "Physical Resistance", _parse_non_negative_int),
    "attributesSetMagicPowerAction": ("attributesDraft", "magic_power", "Magic Power", _parse_non_negative_int),
    "attributesSetMagicStaminaAction": ("attributesDraft", "magic_stamina", "Magic Stamina", _parse_non_negative_int),
    "attributesSetMagicResistanceAction": ("attributesDraft", "magic_resistance", "Magic Resistance", _parse_non_negative_int),
    "gearSetHeadAction": ("gearDraft", "head", "Head Item Name", _parse_optional_text),
    "gearSetNeckAction": ("gearDraft", "neck", "Neck Item Name", _parse_optional_text),
    "gearSetBodyAction": ("gearDraft", "body", "Body Item Name", _parse_optional_text),
    "gearSetHandsAction": ("gearDraft", "hands", "Hands Item Name", _parse_optional_text),
    "gearSetRingAction": ("gearDraft", "ring", "Ring Item Name", _parse_optional_text),
    "gearSetLegsAction": ("gearDraft", "legs", "Legs Item Name", _parse_optional_text),
    "gearSetFeetAction": ("gearDraft", "feet", "Feet Item Name", _parse_optional_text),
    "gearSetPrimaryWeaponAction": ("gearDraft", "primary_weapon", "Primary Weapon Name", _parse_optional_text),
    "gearSetOffhandAction": ("gearDraft", "offhand", "Offhand Item Name", _parse_optional_text),
    "gearSetInventoryAction": ("gearDraft", "inventory_json", "Inventory JSON", _parse_json_list),
    "bonusSetBonusTypeAction": ("bonusDraft", "bonus_type", "Bonus Type", _parse_non_empty_text),
    "bonusSetAttributeBonusAction": ("bonusDraft", "attribute_bonus_json", "Attribute Bonus JSON", _parse_json_object),
    "bonusSetAffinitiesAction": ("bonusDraft", "affinities_json", "Affinities JSON", _parse_json_object),
    "bonusSetNanoMultiplierAction": ("bonusDraft", "nano_multiplier", "Nano Multiplier", _parse_float),
    "bonusSetReasonAction": ("bonusDraft", "reason", "Reason", _parse_optional_text),
    "bonusSetPermanentAction": ("bonusDraft", "permanent", "Permanent (yes/no)", _parse_bool_yes_no),
    "achievementSetNameAction": ("achievementDraft", "name", "Achievement Name", _parse_non_empty_text),
    "achievementSetTitleAction": ("achievementDraft", "title", "Achievement Title", _parse_optional_text),
    "achievementSetBonusAction": ("achievementDraft", "bonus_json", "Bonus JSON", _parse_json_object),
}

ITEM_ENUM_ACTIONS = {
    "itemSetSlot_NOT_EQUIPABLE_Action": ("slot", EquipSlot.NOT_EQUIPABLE.name),
    "itemSetSlot_HEAD_Action": ("slot", EquipSlot.HEAD.name),
    "itemSetSlot_NECK_Action": ("slot", EquipSlot.NECK.name),
    "itemSetSlot_BODY_Action": ("slot", EquipSlot.BODY.name),
    "itemSetSlot_HANDS_Action": ("slot", EquipSlot.HANDS.name),
    "itemSetSlot_RING_Action": ("slot", EquipSlot.RING.name),
    "itemSetSlot_LEGS_Action": ("slot", EquipSlot.LEGS.name),
    "itemSetSlot_FEET_Action": ("slot", EquipSlot.FEET.name),
    "itemSetSlot_PRIMARY_WEAPON_Action": ("slot", EquipSlot.PRIMARY_WEAPON.name),
    "itemSetSlot_OFFHAND_Action": ("slot", EquipSlot.OFFHAND.name),
    "itemSetType_DEFAULT_Action": ("item_type", ItemType.DEFAULT.name),
    "itemSetType_CONSUMABLE_Action": ("item_type", ItemType.CONSUMABLE.name),
    "itemSetType_MELEE_WEAPON_Action": ("item_type", ItemType.MELEE_WEAPON.name),
    "itemSetType_MELEE_THROWABLE_Action": ("item_type", ItemType.MELEE_THROWABLE.name),
    "itemSetType_RANGED_WEAPON_Action": ("item_type", ItemType.RANGED_WEAPON.name),
    "itemSetType_ARMOR_Action": ("item_type", ItemType.ARMOR.name),
    "itemSetDamage_NONE_Action": ("damage_type", "NONE"),
    "itemSetDamage_PIERCING_Action": ("damage_type", DamageType.PIERCING.name),
    "itemSetDamage_BLUDGEONING_Action": ("damage_type", DamageType.BLUDGEONING.name),
    "itemSetDamage_SLASHING_Action": ("damage_type", DamageType.SLASHING.name),
    "itemSetDamage_COLD_Action": ("damage_type", DamageType.COLD.name),
    "itemSetDamage_FIRE_Action": ("damage_type", DamageType.FIRE.name),
    "itemSetDamage_LIGHTNING_Action": ("damage_type", DamageType.LIGHTNING.name),
    "itemSetDamage_THUNDER_Action": ("damage_type", DamageType.THUNDER.name),
    "itemSetDamage_POISON_Action": ("damage_type", DamageType.POISON.name),
    "itemSetDamage_ACID_Action": ("damage_type", DamageType.ACID.name),
    "itemSetDamage_RADIANT_Action": ("damage_type", DamageType.RADIANT.name),
    "itemSetDamage_NECROTIC_Action": ("damage_type", DamageType.NECROTIC.name),
    "itemSetDamage_FORCE_Action": ("damage_type", DamageType.FORCE.name),
    "itemSetDamage_PSYCHIC_Action": ("damage_type", DamageType.PSYCHIC.name),
    "itemSetPowerType_NONE_Action": ("power_type", "NONE"),
    "itemSetPowerType_PHYSICAL_ATTACK_Action": ("power_type", PowerType.PHYSICAL_ATTACK.name),
    "itemSetPowerType_MAGIC_ATTACK_Action": ("power_type", PowerType.MAGIC_ATTACK.name),
    "itemSetPowerType_CONSUMABLE_POWER_Action": ("power_type", PowerType.CONSUMABLE_POWER.name),
}

class FieldEditModal(discord.ui.Modal):
    def __init__(
        self,
        runtime: "MenuRuntimeService",
        original_message: "OriginalMessage",
        return_menu: Menu,
        draft_attr: str,
        field_key: str,
        field_label: str,
        parser,
        title: str,
    ):
        super().__init__(title=title)
        self.runtime = runtime
        self.original_message = original_message
        self.return_menu = return_menu
        self.draft_attr = draft_attr
        self.field_key = field_key
        self.field_label = field_label
        self.parser = parser
        self.value = discord.ui.TextInput(
            label=field_label,
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=4000,
        )
        self.add_item(self.value)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            parsed = self.parser(self.value.value)
            draft = getattr(self.original_message.menuContext, self.draft_attr)
            draft[self.field_key] = parsed
        except Exception as exc:
            await interaction.response.send_message(f"Invalid value: {exc}", ephemeral=True)
            return

        await interaction.response.defer()
        self.runtime._refresh_spellbook_overview()
        self.runtime._refresh_itembook_overview()
        self.runtime.menu_service.update_menu_values(self.original_message, self.return_menu)
        rendered = self.runtime.menu_service.build_rendered_menu(
            self.return_menu,
            self.original_message,
            getattr(interaction.user, "display_name", interaction.user.name),
        )
        await self.original_message.message.edit(
            embed=self.runtime.build_discord_embed(rendered),
            view=self.runtime.build_view(self.return_menu, self.original_message),
        )


class SpellSelectModal(discord.ui.Modal, title="Edit Existing Spell"):
    spell_name = discord.ui.TextInput(
        label="Existing Spell Name",
        style=discord.TextStyle.short,
        required=True,
        max_length=100,
    )

    def __init__(self, runtime: "MenuRuntimeService", original_message: "OriginalMessage"):
        super().__init__()
        self.runtime = runtime
        self.original_message = original_message

    async def on_submit(self, interaction: discord.Interaction):
        spell_name = str(self.spell_name.value).strip()
        spell = self.runtime.spell_service.get_spell(spell_name)
        if spell is None:
            await interaction.response.send_message(f"Spell '{spell_name}' does not exist.", ephemeral=True)
            return

        self.runtime._start_spell_draft(self.original_message.menuContext, source_spell_name=spell.name)
        self.runtime._populate_spell_draft_from_spell(self.original_message.menuContext, spell)
        self.runtime._refresh_spellbook_overview()

        first_menu = self.runtime.context.menus_by_name.get("spellCreateNameMenu")
        if first_menu is None:
            self.runtime._clear_spell_draft(self.original_message.menuContext)
            await interaction.response.send_message("Spell editor menu is not configured.", ephemeral=True)
            return

        self.runtime.menu_service.update_menu_values(self.original_message, first_menu)
        rendered = self.runtime.menu_service.build_rendered_menu(
            first_menu,
            self.original_message,
            getattr(interaction.user, "display_name", interaction.user.name),
        )

        await interaction.response.defer()
        await self.original_message.message.edit(
            embed=self.runtime.build_discord_embed(rendered),
            view=self.runtime.build_view(first_menu, self.original_message),
        )



class ItemSelectModal(discord.ui.Modal, title="Edit Existing Item"):
    item_name = discord.ui.TextInput(
        label="Existing Item Name",
        style=discord.TextStyle.short,
        required=True,
        max_length=100,
    )

    def __init__(self, runtime: "MenuRuntimeService", original_message: "OriginalMessage"):
        super().__init__()
        self.runtime = runtime
        self.original_message = original_message

    async def on_submit(self, interaction: discord.Interaction):
        item_name = str(self.item_name.value).strip()
        item = self.runtime.item_service.get_item(item_name)
        if item is None:
            matches = self.runtime.item_service.get_items_by_name(item_name)
            if len(matches) > 1:
                await interaction.response.send_message(
                    f"Item name '{item_name}' is ambiguous. Use the item ID instead.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(f"Item '{item_name}' does not exist.", ephemeral=True)
            return

        self.runtime._start_item_draft(self.original_message.menuContext, source_item_id=item.itemId)
        self.runtime._populate_item_draft_from_item(self.original_message.menuContext, item)
        self.runtime._refresh_itembook_overview()

        first_menu = self.runtime.context.menus_by_name.get("itemCreateNameMenu")
        if first_menu is None:
            self.runtime._clear_item_draft(self.original_message.menuContext)
            await interaction.response.send_message("Item editor menu is not configured.", ephemeral=True)
            return

        self.runtime.menu_service.update_menu_values(self.original_message, first_menu)
        rendered = self.runtime.menu_service.build_rendered_menu(
            first_menu,
            self.original_message,
            getattr(interaction.user, "display_name", interaction.user.name),
        )

        await interaction.response.defer()
        await self.original_message.message.edit(
            embed=self.runtime.build_discord_embed(rendered),
            view=self.runtime.build_view(first_menu, self.original_message),
        )
class MenuInterface(ABC):
    @property
    @abstractmethod
    def user_id(self) -> int:
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        pass

    @property
    @abstractmethod
    def supports_modals(self) -> bool:
        pass

    @property
    @abstractmethod
    def discord_interaction(self) -> discord.Interaction | None:
        pass

    @abstractmethod
    async def send_ephemeral(self, content: str):
        pass

    @abstractmethod
    async def before_update(self):
        pass

    @abstractmethod
    async def send_initial(self, rendered: RenderedMenu, menu: Menu, original_message: "OriginalMessage"):
        pass

    @abstractmethod
    async def send_update(self, rendered: RenderedMenu, menu: Menu, original_message: "OriginalMessage"):
        pass

    @abstractmethod
    async def send_modal(self, modal: discord.ui.Modal):
        pass


class OriginalMessage:
    def __init__(self, player, is_developer_admin: bool = False):
        self.player = player
        self.message = None
        self.menuContext = MenuContext()
        self.is_developer_admin = is_developer_admin

    def setMessageObject(self, message: discord.Message):
        self.message = message


class MenuRuntimeService:
    def __init__(
        self,
        menu_service: MenuService,
        player_service: PlayerService,
        whitelist_service: AdminWhitelistService,
        spell_service: SpellService,
        item_service: ItemService,
        context: GameContext,
        battle_runtime_service=None,
    ):
        self.menu_service = menu_service
        self.player_service = player_service
        self.whitelist_service = whitelist_service
        self.spell_service = spell_service
        self.item_service = item_service
        self.context = context
        self.battle_runtime_service = battle_runtime_service
        self._special_action_router = MenuSpecialActionRouter(self)

    def build_discord_embed(self, rendered: RenderedMenu):
        embed = discord.Embed(title=rendered.title, description=rendered.description)
        embed.set_footer(text=rendered.footer)
        if rendered.thumbnailURL:
            embed.set_thumbnail(url=rendered.thumbnailURL)
        if rendered.imageURL:
            embed.set_image(url=rendered.imageURL)
        return embed

    def build_view(self, menu: Menu, original_message: OriginalMessage):
        visible_children = self.menu_service.get_visible_child_menus(menu, original_message)
        return SimpleMenu(
            current_menu=menu,
            original_message=original_message,
            visible_children=visible_children,
            on_select=self.update_menu,
        )

    def build_spell_select_modal(self, original_message: OriginalMessage) -> discord.ui.Modal:
        return SpellSelectModal(self, original_message)

    def build_item_select_modal(self, original_message: OriginalMessage) -> discord.ui.Modal:
        return ItemSelectModal(self, original_message)

    def build_field_edit_modal(self, menu: Menu, original_message: OriginalMessage) -> discord.ui.Modal:
        if menu.uniqueName in SPELL_FIELD_EDIT_CONFIG:
            draft_attr = "spellDraft"
            field_key, field_label, parser = SPELL_FIELD_EDIT_CONFIG[menu.uniqueName]
            modal_title = "Edit Spell Field"
        elif menu.uniqueName in ITEM_FIELD_EDIT_CONFIG:
            draft_attr, field_key, field_label, parser = ITEM_FIELD_EDIT_CONFIG[menu.uniqueName]
            modal_title = "Edit Item Field"
        else:
            draft_attr, field_key, field_label, parser = COMPONENT_FIELD_EDIT_CONFIG[menu.uniqueName]
            modal_title = "Edit Field"
        return_menu = menu.parent if menu.parent is not None else menu
        return FieldEditModal(
            runtime=self,
            original_message=original_message,
            return_menu=return_menu,
            draft_attr=draft_attr,
            field_key=field_key,
            field_label=field_label,
            parser=parser,
            title=modal_title,
        )

    @staticmethod
    def _build_spell_payload_from_draft(draft: dict) -> dict:
        return {
            "name": draft.get("name", ""),
            "level": draft.get("level", 0),
            "power": draft.get("power", ""),
            "affinity": draft.get("affinity", ""),
            "casting_time": draft.get("casting_time", ""),
            "range": draft.get("range", ""),
            "components": {
                "verbal": bool(draft.get("component_verbal", False)),
                "somatic": bool(draft.get("component_somatic", False)),
                "material": draft.get("component_material", False),
            },
            "duration": draft.get("duration", ""),
            "description": draft.get("description", ""),
            "higher_level": draft.get("higher_level", ""),
        }



    @staticmethod
    def _build_item_payload_from_draft(draft: dict) -> dict:
        damage_type = str(draft.get("damage_type", "NONE") or "NONE").strip().upper()
        power_type = str(draft.get("power_type", "NONE") or "NONE").strip().upper()

        power_spell_name = str(draft.get("power_spell_name", "")).strip()
        power_value = int(draft.get("power_value", 0) or 0)

        item_power = []
        if power_type != "NONE":
            item_power.append(
                {
                    "powerType": power_type,
                    "power": power_value,
                    "spellName": power_spell_name,
                }
            )

        stat_bonuses_raw = str(draft.get("stat_bonuses_json", "[]") or "[]")
        stat_bonuses = json.loads(stat_bonuses_raw)
        if not isinstance(stat_bonuses, list):
            raise ValueError("Stat bonuses must be a JSON array.")

        return {
            "name": str(draft.get("name", "")).strip(),
            "slot": str(draft.get("slot", EquipSlot.NOT_EQUIPABLE.name)),
            "tier": int(draft.get("tier", 0) or 0),
            "durability": int(draft.get("durability", DEFAULT_DURABILITY) or DEFAULT_DURABILITY),
            "itemType": str(draft.get("item_type", ItemType.DEFAULT.name)),
            "itemPower": item_power,
            "damageType": [] if damage_type == "NONE" else [damage_type],
            "statBonuses": stat_bonuses,
        }

    @staticmethod
    def _start_spell_draft(menu_context: MenuContext, source_spell_name: str | None = None):
        menu_context.spellDraft = dict(SPELL_FIELD_DEFAULTS)
        menu_context.spellDraftActive = True
        menu_context.spellDraftSourceName = source_spell_name

    @staticmethod
    def _populate_spell_draft_from_spell(menu_context: MenuContext, spell):
        spell_data = spell.to_dict()
        components = spell_data.get("components", {})
        menu_context.spellDraft.update(
            {
                "name": spell_data.get("name", ""),
                "level": spell_data.get("level", 0),
                "power": spell_data.get("power", ""),
                "affinity": spell_data.get("affinity", ""),
                "casting_time": spell_data.get("casting_time", ""),
                "range": spell_data.get("range", ""),
                "component_verbal": bool(components.get("verbal", False)),
                "component_somatic": bool(components.get("somatic", False)),
                "component_material": components.get("material", False),
                "duration": spell_data.get("duration", ""),
                "description": spell_data.get("description", ""),
                "higher_level": spell_data.get("higher_level", ""),
            }
        )

    @staticmethod
    def _clear_spell_draft(menu_context: MenuContext):
        menu_context.spellDraft = {}
        menu_context.spellDraftActive = False
        menu_context.spellDraftSourceName = None



    @staticmethod
    def _start_item_draft(menu_context: MenuContext, source_item_id: str | None = None):
        menu_context.itemDraft = dict(ITEM_FIELD_DEFAULTS)
        menu_context.itemDraftActive = True
        menu_context.itemDraftSourceId = source_item_id
        menu_context.itemDraftSourceName = source_item_id

    @staticmethod
    def _populate_item_draft_from_item(menu_context: MenuContext, item):
        item_data = item.to_dict()
        damage_types = item_data.get("damageType", [])
        item_power = item_data.get("itemPower", [])
        first_power = item_power[0] if item_power else {}

        menu_context.itemDraft.update(
            {
                "name": item_data.get("name", ""),
                "slot": item_data.get("slot", EquipSlot.NOT_EQUIPABLE.name),
                "tier": int(item_data.get("tier", 0) or 0),
                "durability": int(item_data.get("durability", DEFAULT_DURABILITY) or DEFAULT_DURABILITY),
                "item_type": item_data.get("itemType", ItemType.DEFAULT.name),
                "damage_type": damage_types[0] if damage_types else "NONE",
                "power_type": str(first_power.get("powerType", "NONE") or "NONE"),
                "power_value": int(first_power.get("power", 0) or 0),
                "power_spell_name": str(first_power.get("spellName", "") or ""),
                "stat_bonuses_json": json.dumps(item_data.get("statBonuses", []), ensure_ascii=False),
            }
        )

    @staticmethod
    def _clear_item_draft(menu_context: MenuContext):
        menu_context.itemDraft = {}
        menu_context.itemDraftActive = False
        menu_context.itemDraftSourceId = None
        menu_context.itemDraftSourceName = None



    @staticmethod
    def _start_attributes_draft(menu_context: MenuContext):
        menu_context.attributesDraft = dict(ATTRIBUTES_DRAFT_DEFAULTS)
        menu_context.attributesDraftActive = True

    @staticmethod
    def _clear_attributes_draft(menu_context: MenuContext):
        menu_context.attributesDraft = {}
        menu_context.attributesDraftActive = False

    @staticmethod
    def _start_gear_draft(menu_context: MenuContext):
        menu_context.gearDraft = dict(GEAR_DRAFT_DEFAULTS)
        menu_context.gearDraftActive = True

    @staticmethod
    def _clear_gear_draft(menu_context: MenuContext):
        menu_context.gearDraft = {}
        menu_context.gearDraftActive = False

    @staticmethod
    def _start_bonus_draft(menu_context: MenuContext):
        menu_context.bonusDraft = dict(BONUS_DRAFT_DEFAULTS)
        menu_context.bonusDraftActive = True

    @staticmethod
    def _clear_bonus_draft(menu_context: MenuContext):
        menu_context.bonusDraft = {}
        menu_context.bonusDraftActive = False

    @staticmethod
    def _start_achievement_draft(menu_context: MenuContext):
        menu_context.achievementDraft = dict(ACHIEVEMENT_DRAFT_DEFAULTS)
        menu_context.achievementDraftActive = True

    @staticmethod
    def _clear_achievement_draft(menu_context: MenuContext):
        menu_context.achievementDraft = {}
        menu_context.achievementDraftActive = False

    def _refresh_spellbook_overview(self):
        self.context.spellbook_overview = self.spell_service.build_spellbook_overview()

    def _refresh_itembook_overview(self):
        self.context.itembook_overview = self.item_service.build_itembook_overview()

    async def _handle_special_menu_action(self, interface: "MenuInterface", menu: Menu, original_message: OriginalMessage):
        return await self._special_action_router.handle(interface, menu, original_message)

    async def display_menu(self, interaction: discord.Interaction, menu: Menu):
        interface = DiscordMenuInterface(interaction, self)
        await self.display_menu_with_interface(interface, menu)

    async def display_menu_with_interface(self, interface: MenuInterface, menu: Menu):
        player = await self.player_service.get_player(interface.user_id)
        original_message = OriginalMessage(
            player,
            is_developer_admin=self.whitelist_service.is_admin(interface.user_id),
        )

        active_menu = menu
        if player.isNewPlayer:
            original_message.menuContext.menuState = MenuState.NEW_PLAYER
            active_menu = self.context.new_player_menu
            player.isNewPlayer = False

        self._refresh_spellbook_overview()
        self._refresh_itembook_overview()
        self.menu_service.update_menu_values(original_message, active_menu)
        rendered = self.menu_service.build_rendered_menu(active_menu, original_message, interface.display_name)
        await interface.send_initial(rendered, active_menu, original_message)
        return original_message, active_menu

    async def update_menu(self, interaction: discord.Interaction, menu: Menu, original_message: OriginalMessage):
        interface = DiscordMenuInterface(interaction, self)
        await self.update_menu_with_interface(interface, menu, original_message)

    async def update_menu_with_interface(self, interface: MenuInterface, menu: Menu, original_message: OriginalMessage):
        if interface.user_id != original_message.player.discordID:
            await interface.send_ephemeral("You can only interact with your own menus. use /menu to open your menu.")
            return menu

        special_result = await self._handle_special_menu_action(interface, menu, original_message)
        if special_result is not None:
            target_menu, should_render, response_consumed = special_result
            if not should_render:
                return target_menu
            menu = target_menu
            if not response_consumed:
                await interface.before_update()
        else:
            response_consumed = False
            if menu.uniqueName == "spellbookMenu" and original_message.menuContext.spellDraftActive:
                was_edit = bool(original_message.menuContext.spellDraftSourceName)
                self._clear_spell_draft(original_message.menuContext)
                await interface.send_ephemeral("Spell edit cancelled." if was_edit else "Spell creation cancelled.")
                response_consumed = True
            if menu.uniqueName == "itembookMenu" and original_message.menuContext.itemDraftActive:
                was_edit = bool(getattr(original_message.menuContext, "itemDraftSourceId", None) or original_message.menuContext.itemDraftSourceName)
                self._clear_item_draft(original_message.menuContext)
                await interface.send_ephemeral("Item edit cancelled." if was_edit else "Item creation cancelled.")
                response_consumed = True
            if menu.uniqueName == "mainMenu" and original_message.menuContext.attributesDraftActive:
                self._clear_attributes_draft(original_message.menuContext)
                await interface.send_ephemeral("Attributes editor cancelled.")
                response_consumed = True
            if menu.uniqueName == "mainMenu" and original_message.menuContext.gearDraftActive:
                self._clear_gear_draft(original_message.menuContext)
                await interface.send_ephemeral("Gear editor cancelled.")
                response_consumed = True
            if menu.uniqueName == "mainMenu" and original_message.menuContext.bonusDraftActive:
                self._clear_bonus_draft(original_message.menuContext)
                await interface.send_ephemeral("Bonus editor cancelled.")
                response_consumed = True
            if menu.uniqueName == "mainMenu" and original_message.menuContext.achievementDraftActive:
                self._clear_achievement_draft(original_message.menuContext)
                await interface.send_ephemeral("Achievement editor cancelled.")
                response_consumed = True
            if not response_consumed:
                await interface.before_update()

        self._refresh_spellbook_overview()
        self._refresh_itembook_overview()
        self.menu_service.update_menu_values(original_message, menu)
        rendered = self.menu_service.build_rendered_menu(menu, original_message, interface.display_name)
        await interface.send_update(rendered, menu, original_message)
        return menu


class DiscordMenuInterface(MenuInterface):
    def __init__(self, interaction: discord.Interaction, runtime: MenuRuntimeService):
        self.interaction = interaction
        self.runtime = runtime

    @property
    def user_id(self) -> int:
        return self.interaction.user.id

    @property
    def display_name(self) -> str:
        return self.interaction.user.nick or self.interaction.user.display_name

    @property
    def supports_modals(self) -> bool:
        return True

    @property
    def discord_interaction(self) -> discord.Interaction | None:
        return self.interaction

    async def send_ephemeral(self, content: str):
        if self.interaction.response.is_done():
            await self.interaction.followup.send(content=content, ephemeral=True)
        else:
            await self.interaction.response.send_message(content=content, ephemeral=True)

    async def before_update(self):
        if not self.interaction.response.is_done():
            await self.interaction.response.defer()

    async def send_initial(self, rendered: RenderedMenu, menu: Menu, original_message: OriginalMessage):
        embed = self.runtime.build_discord_embed(rendered)
        view = self.runtime.build_view(menu, original_message)
        await self.interaction.response.send_message(embed=embed, view=view)
        original_message.setMessageObject(await self.interaction.original_response())

    async def send_update(self, rendered: RenderedMenu, menu: Menu, original_message: OriginalMessage):
        embed = self.runtime.build_discord_embed(rendered)
        view = self.runtime.build_view(menu, original_message)
        await original_message.message.edit(embed=embed, view=view)

    async def send_modal(self, modal: discord.ui.Modal):
        await self.interaction.response.send_modal(modal)


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

    @property
    def supports_modals(self) -> bool:
        return False

    @property
    def discord_interaction(self) -> discord.Interaction | None:
        return None

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
        if rendered.thumbnailURL:
            print(f"Thumbnail: {self._safe_text(rendered.thumbnailURL)}")
        if rendered.imageURL:
            print(f"Image: {self._safe_text(rendered.imageURL)}")
        if rendered.hasBack:
            print("Button: back")
        for button in rendered.buttons:
            safe_label = self._safe_text(button.label)
            safe_emoji = self._safe_text(button.emoji)
            print(f"Button: {button.targetMenuName} label='{safe_label}' emoji='{safe_emoji}'")
        print("")

    async def send_initial(self, rendered: RenderedMenu, menu: Menu, original_message: OriginalMessage):
        self._print_render(rendered)

    async def send_update(self, rendered: RenderedMenu, menu: Menu, original_message: OriginalMessage):
        self._print_render(rendered)

    async def send_modal(self, modal: discord.ui.Modal):
        raise RuntimeError("Console menu interface does not support modals.")
