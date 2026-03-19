import json
from pathlib import Path
from typing import Dict, Optional, Set

from src.ui.menu import Menu, MenuState


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

    directory_path = Path(directory)
    directory_path.mkdir(parents=True, exist_ok=True)
    file_path = directory_path / f"{menu.uniqueName}.json"
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(_menu_to_dict(menu), file, indent=4, ensure_ascii=False)

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
        with open(menu_file, "r", encoding="utf-8-sig") as file:
            data = json.load(file)

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


class MenuStore:
    def __init__(self, menu_directory: str):
        self.menu_directory = menu_directory

    def load_menus(self):
        return load_menus_from_directory(self.menu_directory)

    def save_menu(self, menu: Menu):
        save_menu(menu, self.menu_directory)
