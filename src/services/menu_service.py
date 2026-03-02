from dataclasses import dataclass
from string import Template
from typing import List, Optional

from src.domain.player_functions import Player
from src.persistence.menu_store import MenuStore
from src.services.game_context import GameContext
from src.ui.menu_functions import Menu, MenuContext, MenuState


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

    def replace_placeholders(self, text: str, player: Player, menu_state: MenuContext) -> str:
        faction_title = player.faction.title if player.faction else ""

        draft = menu_state.spellDraft if hasattr(menu_state, "spellDraft") else {}

        data = {
            "nano": player.nano,
            "playerName": player.playerName,
            "factionTitle": faction_title,
            "achievementTitle": player.achievementTitle,
            "energy": int(player.energy),
            "energyCap": int(player.energyCap),
            "characters": player.GetCharacterText(),
            "spellbookOverview": self.context.spellbook_overview,
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

    def build_rendered_menu(self, menu: Menu, original_message: "OriginalMessage", display_name: str) -> RenderedMenu:
        original_message.player.GetCurrentEnergy(persist=True)
        replaced_title = self.replace_placeholders(menu.myOptionText, original_message.player, original_message.menuContext)
        replaced_body = self.replace_placeholders(menu.bodyText, original_message.player, original_message.menuContext)
        buttons = [
            RenderedButton(targetMenuName=child.uniqueName, label=label, emoji=child.myEmoji or "")
            for child, label in self.get_visible_child_menus(menu, original_message)
        ]

        return RenderedMenu(
            title=replaced_title,
            description=replaced_body,
            footer=f"{display_name}'s Menu",
            imageURL=menu.imageURL if hasattr(menu, "imageURL") else None,
            hasBack=menu.parent is not None,
            buttons=buttons,
        )
