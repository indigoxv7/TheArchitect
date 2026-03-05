import json
from pathlib import Path
from enum import Enum
from typing import Optional, Set, Dict


class MenuState (Enum):
    DEFAULT = 0
    NEW_PLAYER = 1
    MAIN = 2
    CHARACTER = 3


class MenuContext:
    def __init__(self):
        self.menuState = MenuState.MAIN
        self.character = None
        self.spellDraft = {}
        self.spellDraftActive = False
        self.spellDraftSourceName = None
        self.itemDraft = {}
        self.itemDraftActive = False
        self.itemDraftSourceName = None
        self.attributesDraft = {}
        self.attributesDraftActive = False
        self.gearDraft = {}
        self.gearDraftActive = False
        self.bonusDraft = {}
        self.bonusDraftActive = False
        self.achievementDraft = {}
        self.achievementDraftActive = False


class ContextButton:
    def __init__(self, name: str, count: int, target: 'Menu' = None, warningText: str = ""):
        self.name = name
        self.count = count
        self.target = target
        self.warningText = warningText


class Menu:
    def __init__(
        self,
        myOptionText,
        bodyText,
        uniqueName,
        parent=None,
        myEmoji=None,
        imageURL=None,
        menuState: MenuState = MenuState.DEFAULT,
        contextButtons: list[ContextButton] = None,
        developerOnly: bool = False,
    ):
        self.myOptionText = myOptionText
        self.myEmoji = myEmoji
        self.uniqueName = uniqueName
        self.bodyText = bodyText
        self.parent = parent
        self.Options = []
        self.imageURL = imageURL
        self.menuState = menuState
        self.contextButtons = contextButtons
        self.developerOnly = developerOnly

    def add_option(self, menu):
        menu.parent = self
        self.Options.append(menu)


def _menu_state_from_string(state_name: Optional[str]) -> MenuState:
    if not state_name:
        return MenuState.DEFAULT
    try:
        return MenuState[state_name]
    except KeyError:
        return MenuState.DEFAULT


def _menu_to_dict(menu: Menu) -> dict:
    return {
        "myOptionText": menu.myOptionText,
        "myEmoji": menu.myEmoji,
        "uniqueName": menu.uniqueName,
        "bodyText": menu.bodyText,
        "imageURL": menu.imageURL,
        "menuState": menu.menuState.name,
        "parentName": menu.parent.uniqueName if menu.parent else None,
        "developerOnly": menu.developerOnly,
        "Options": [option.uniqueName for option in menu.Options],
    }


def save_menu(menu: Menu, directory: str, saved_names: Optional[Set[str]] = None):
    if saved_names is None:
        saved_names = set()

    if menu.uniqueName in saved_names:
        return

    Path(directory).mkdir(parents=True, exist_ok=True)
    file_path = Path(directory) / f"{menu.uniqueName}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(_menu_to_dict(menu), f, indent=4, ensure_ascii=False)

    saved_names.add(menu.uniqueName)

    for option in menu.Options:
        save_menu(option, directory, saved_names)


def load_menus_from_directory(directory: str) -> Dict[str, Menu]:
    directory_path = Path(directory)
    menu_files = sorted(directory_path.glob("*.json"))
    if not menu_files:
        raise FileNotFoundError(f"No menu JSON files found in '{directory}'.")

    menus_by_name: Dict[str, Menu] = {}
    raw_data_by_name: Dict[str, dict] = {}

    for menu_file in menu_files:
        with open(menu_file, "r", encoding="utf-8-sig") as f:
            data = json.load(f)

        unique_name = data["uniqueName"]
        if unique_name in menus_by_name:
            raise ValueError(f"Duplicate menu uniqueName '{unique_name}' in '{menu_file}'.")

        menus_by_name[unique_name] = Menu(
            myOptionText=data["myOptionText"],
            myEmoji=data.get("myEmoji"),
            uniqueName=unique_name,
            bodyText=data["bodyText"],
            imageURL=data.get("imageURL"),
            menuState=_menu_state_from_string(data.get("menuState")),
            parent=None,
            developerOnly=bool(data.get("developerOnly", False)),
        )
        raw_data_by_name[unique_name] = data

    for unique_name, menu in menus_by_name.items():
        data = raw_data_by_name[unique_name]
        parent_name = data.get("parentName")
        if parent_name is not None:
            if parent_name not in menus_by_name:
                raise ValueError(f"Menu '{unique_name}' parent '{parent_name}' not found.")
            menu.parent = menus_by_name[parent_name]

    for unique_name, menu in menus_by_name.items():
        data = raw_data_by_name[unique_name]
        menu.Options = []
        for option_name in data.get("Options", []):
            if option_name not in menus_by_name:
                raise ValueError(f"Menu '{unique_name}' option '{option_name}' not found.")
            option_menu = menus_by_name[option_name]
            menu.Options.append(option_menu)
            option_menu.parent = menu

    return menus_by_name


