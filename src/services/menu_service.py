from dataclasses import dataclass
from string import Template
from typing import List, Optional

from src.domain.player_functions import Player
from src.persistence.menu_store import MenuStore
from src.services.game_context import GameContext
from src.ui.menu import Menu, MenuContext, MenuState


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
    thumbnailURL: Optional[str]
    hasBack: bool
    buttons: List[RenderedButton]


class MenuService:
    def __init__(
        self,
        menu_directory: str,
        emoji_placeholders: dict[str, str],
        context: GameContext,
    ):
        self.emoji_placeholders = dict(emoji_placeholders)
        self.context = context
        self.store = MenuStore(menu_directory)

    def load_menus(self):
        menus_by_name = self.store.load_menus()

        if "mainMenu" not in menus_by_name:
            raise ValueError("Missing required menu JSON: 'mainMenu'.")
        if "newPlayerMenu" not in menus_by_name:
            raise ValueError("Missing required menu JSON: 'newPlayerMenu'.")

        self.context.menus_by_name = menus_by_name
        self.context.root_menu = menus_by_name["mainMenu"]
        self.context.new_player_menu = menus_by_name["newPlayerMenu"]
        return menus_by_name

    def replace_emoji_aliases(self, text: str) -> str:
        for key, value in self.emoji_placeholders.items():
            short_name = key[:-5]
            text = text.replace(f":{short_name}:", value)
            text = text.replace("{" + key + "}", value)
        return text

    @staticmethod
    def _spell_draft_summary(draft: dict) -> str:
        if not draft:
            return "No draft spell in progress."

        lines = [
            f"Name: {draft.get('name', '')}",
            f"Level: {draft.get('level', '')}",
            f"Power: {draft.get('power', '')}",
            f"Affinity: {draft.get('affinity', '')}",
            f"Casting Time: {draft.get('casting_time', '')}",
            f"Range: {draft.get('range', '')}",
            f"Verbal: {draft.get('component_verbal', '')}",
            f"Somatic: {draft.get('component_somatic', '')}",
            f"Material: {draft.get('component_material', '')}",
            f"Duration: {draft.get('duration', '')}",
            f"Description: {draft.get('description', '')}",
            f"Higher Level: {draft.get('higher_level', '')}",
        ]
        return "\n".join(lines)


    @staticmethod
    def _item_draft_summary(draft: dict) -> str:
        if not draft:
            return "No draft item in progress."

        lines = [
            f"Name: {draft.get('name', '')}",
            f"Slot: {draft.get('slot', '')}",
            f"Tier: {draft.get('tier', '')}",
            f"Durability: {draft.get('durability', '')}",
            f"Item Type: {draft.get('item_type', '')}",
            f"Damage Type: {draft.get('damage_type', '')}",
            f"Power Type: {draft.get('power_type', '')}",
            f"Power Value: {draft.get('power_value', '')}",
            f"Power Spell Name: {draft.get('power_spell_name', '')}",
            f"Stat Bonuses JSON: {draft.get('stat_bonuses_json', '[]')}",
        ]
        return "\n".join(lines)


    @staticmethod
    def _attributes_draft_summary(draft: dict) -> str:
        if not draft:
            return "No draft attributes in progress."
        lines = [
            f"Physical Power: {draft.get('physical_power', 0)}",
            f"Physical Stamina: {draft.get('physical_stamina', 0)}",
            f"Physical Resistance: {draft.get('physical_resistance', 0)}",
            f"Magic Power: {draft.get('magic_power', 0)}",
            f"Magic Stamina: {draft.get('magic_stamina', 0)}",
            f"Magic Resistance: {draft.get('magic_resistance', 0)}",
        ]
        return "\n".join(lines)

    @staticmethod
    def _gear_draft_summary(draft: dict) -> str:
        if not draft:
            return "No draft gear in progress."
        lines = [
            f"Head: {draft.get('head', '')}",
            f"Neck: {draft.get('neck', '')}",
            f"Body: {draft.get('body', '')}",
            f"Hands: {draft.get('hands', '')}",
            f"Ring: {draft.get('ring', '')}",
            f"Legs: {draft.get('legs', '')}",
            f"Feet: {draft.get('feet', '')}",
            f"Primary Weapon: {draft.get('primary_weapon', '')}",
            f"Offhand: {draft.get('offhand', '')}",
            f"Inventory JSON: {draft.get('inventory_json', '[]')}",
        ]
        return "\n".join(lines)

    @staticmethod
    def _bonus_draft_summary(draft: dict) -> str:
        if not draft:
            return "No draft bonus in progress."
        lines = [
            f"Bonus Type: {draft.get('bonus_type', '')}",
            f"Attribute Bonus JSON: {draft.get('attribute_bonus_json', '{}')}",
            f"Affinities JSON: {draft.get('affinities_json', '{}')}",
            f"Nano Multiplier: {draft.get('nano_multiplier', 0)}",
            f"Reason: {draft.get('reason', '')}",
            f"Permanent: {draft.get('permanent', False)}",
        ]
        return "\n".join(lines)

    @staticmethod
    def _achievement_draft_summary(draft: dict) -> str:
        if not draft:
            return "No draft achievement in progress."
        lines = [
            f"Name: {draft.get('name', '')}",
            f"Title: {draft.get('title', '')}",
            f"Bonus JSON: {draft.get('bonus_json', '{}')}",
        ]
        return "\n".join(lines)

    def _resolve_inventory_entry_label(self, entry) -> str:
        if entry is None:
            return ""

        if hasattr(entry, "name"):
            name = str(getattr(entry, "name", "") or "").strip()
            item_id = str(getattr(entry, "itemId", "") or "").strip()
            if name and item_id:
                return f"{name} [{item_id}]"
            if name:
                return name

        raw = str(entry).strip()
        if not raw:
            return ""

        by_id = self.context.all_items.get(raw)
        if by_id is not None and hasattr(by_id, "name"):
            name = str(getattr(by_id, "name", "") or "").strip()
            item_id = str(getattr(by_id, "itemId", "") or "").strip()
            if name and item_id:
                return f"{name} [{item_id}]"
            if name:
                return name

        item_ids = self.context.all_items_by_name.get(raw.lower(), [])
        if len(item_ids) == 1:
            resolved = self.context.all_items.get(item_ids[0])
            if resolved is not None and hasattr(resolved, "name"):
                name = str(getattr(resolved, "name", "") or "").strip()
                item_id = str(getattr(resolved, "itemId", "") or "").strip()
                if name and item_id:
                    return f"{name} [{item_id}]"
                if name:
                    return name

        return raw

    def _inventory_summary(self, player: Player, max_items: int = 40) -> str:
        inventory = getattr(player, "inventory", None)
        if not isinstance(inventory, list) or not inventory:
            return "Inventory is empty."

        lines = []
        visible_entries = inventory[:max_items]
        for index, entry in enumerate(visible_entries, start=1):
            label = self._resolve_inventory_entry_label(entry) or "<Unknown Item>"
            lines.append(f"{index}. {label}")

        if len(inventory) > max_items:
            lines.append(f"... and {len(inventory) - max_items} more")

        return "\n".join(lines)

    def replace_placeholders(self, text: str, player: Player, menu_state: MenuContext) -> str:
        faction_title = player.faction.title if player.faction else ""

        draft = menu_state.spellDraft if hasattr(menu_state, "spellDraft") else {}
        item_draft = menu_state.itemDraft if hasattr(menu_state, "itemDraft") else {}
        attributes_draft = menu_state.attributesDraft if hasattr(menu_state, "attributesDraft") else {}
        gear_draft = menu_state.gearDraft if hasattr(menu_state, "gearDraft") else {}
        bonus_draft = menu_state.bonusDraft if hasattr(menu_state, "bonusDraft") else {}
        achievement_draft = menu_state.achievementDraft if hasattr(menu_state, "achievementDraft") else {}

        data = {
            "nano": player.nano,
            "playerName": player.playerName,
            "factionTitle": faction_title,
            "achievementTitle": player.achievementTitle,
            "energy": int(player.energy),
            "energyCap": int(player.energyCap),
            "characters": player.GetCharacterText(),
            "inventoryCount": len(player.inventory) if isinstance(player.inventory, list) else 0,
            "inventoryList": self._inventory_summary(player),
            "spellbookOverview": self.context.spellbook_overview,
            "itembookOverview": self.context.itembook_overview,
            "characterbookOverview": self.context.characterbook_overview,
            "spellDraftName": draft.get("name", ""),
            "spellDraftLevel": draft.get("level", ""),
            "spellDraftPower": draft.get("power", ""),
            "spellDraftAffinity": draft.get("affinity", ""),
            "spellDraftCastingTime": draft.get("casting_time", ""),
            "spellDraftRange": draft.get("range", ""),
            "spellDraftVerbal": draft.get("component_verbal", ""),
            "spellDraftSomatic": draft.get("component_somatic", ""),
            "spellDraftMaterial": draft.get("component_material", ""),
            "spellDraftDuration": draft.get("duration", ""),
            "spellDraftDescription": draft.get("description", ""),
            "spellDraftHigherLevel": draft.get("higher_level", ""),
            "spellDraftSummary": self._spell_draft_summary(draft),
            "itemDraftName": item_draft.get("name", ""),
            "itemDraftSlot": item_draft.get("slot", ""),
            "itemDraftTier": item_draft.get("tier", ""),
            "itemDraftDurability": item_draft.get("durability", ""),
            "itemDraftType": item_draft.get("item_type", ""),
            "itemDraftDamageType": item_draft.get("damage_type", ""),
            "itemDraftPowerType": item_draft.get("power_type", ""),
            "itemDraftPowerValue": item_draft.get("power_value", ""),
            "itemDraftPowerSpellName": item_draft.get("power_spell_name", ""),
            "itemDraftStatBonuses": item_draft.get("stat_bonuses_json", "[]"),
            "itemDraftSummary": self._item_draft_summary(item_draft),
            "attributesDraftSummary": self._attributes_draft_summary(attributes_draft),
            "gearDraftSummary": self._gear_draft_summary(gear_draft),
            "bonusDraftSummary": self._bonus_draft_summary(bonus_draft),
            "achievementDraftSummary": self._achievement_draft_summary(achievement_draft),
        }
        data.update(self.emoji_placeholders)

        if menu_state.character is not None:
            data["characterOverview"] = menu_state.character.GetCharacterOverviewText(player.nano)

        for i in range(0, self.context.max_num_characters):
            data[f"character{i}"] = player.GetCharacterName(i)

        template = Template(text)
        replaced_text = template.safe_substitute(data)
        replaced_text = self.replace_emoji_aliases(replaced_text)
        replaced_text = replaced_text.replace("  ", " ")
        return replaced_text

    def get_visible_child_menus(self, menu: Menu, original_message: "OriginalMessage"):
        visible_children = []
        for child_menu in menu.Options:
            if child_menu.developerOnly and not getattr(original_message, "is_developer_admin", False):
                continue

            proper_title = self.replace_placeholders(
                child_menu.myOptionText,
                original_message.player,
                original_message.menuContext,
            )
            if proper_title != "":
                visible_children.append((child_menu, proper_title))
        return visible_children

    def update_menu_values(self, original_message: "OriginalMessage", menu: Menu):
        original_message.menuContext.menuState = menu.menuState
        if menu.menuState == MenuState.CHARACTER:
            character_index = None
            if menu.uniqueName:
                numeric_suffix = ""
                for char in reversed(menu.uniqueName):
                    if char.isdigit():
                        numeric_suffix = char + numeric_suffix
                    else:
                        break
                if numeric_suffix:
                    character_index = int(numeric_suffix)

            if character_index is None:
                character_index = 0
            original_message.menuContext.character = original_message.player.GetCharacter(character_index)

    def _resolve_character_for_media(self, character):
        if character is None:
            return None

        portrait_url = str(getattr(character, "portraitURL", "") or "").strip()
        footer_image_url = str(getattr(character, "footerImageURL", "") or "").strip()
        if portrait_url or footer_image_url:
            return character

        name = str(getattr(character, "name", "") or "").strip().lower()
        if not name:
            return character

        for candidate in self.context.all_characters.values():
            candidate_name = str(getattr(candidate, "name", "") or "").strip().lower()
            if candidate_name == name:
                return candidate

        return character

    def build_rendered_menu(self, menu: Menu, original_message: "OriginalMessage", display_name: str) -> RenderedMenu:
        original_message.player.GetCurrentEnergy(persist=True)
        replaced_title = self.replace_placeholders(menu.myOptionText, original_message.player, original_message.menuContext)
        replaced_body = self.replace_placeholders(menu.bodyText, original_message.player, original_message.menuContext)
        buttons = [
            RenderedButton(targetMenuName=child.uniqueName, label=label, emoji=child.myEmoji or "")
            for child, label in self.get_visible_child_menus(menu, original_message)
        ]

        character = self._resolve_character_for_media(original_message.menuContext.character)
        thumbnail_url = str(getattr(character, "portraitURL", "") or "").strip() if character is not None else ""
        footer_image_url = str(getattr(character, "footerImageURL", "") or "").strip() if character is not None else ""
        default_image_url = menu.imageURL if hasattr(menu, "imageURL") else None
        image_url = footer_image_url or default_image_url

        return RenderedMenu(
            title=replaced_title,
            description=replaced_body,
            footer=f"{display_name}'s Menu",
            imageURL=image_url,
            thumbnailURL=thumbnail_url or None,
            hasBack=menu.parent is not None,
            buttons=buttons,
        )



