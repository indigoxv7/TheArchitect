import json
from enum import Enum

class MenuState (Enum):
    DEFAULT = 0
    NEW_PLAYER = 1
    MAIN = 2
    CHARACTER = 3

class MenuContext:
    def __init__(self):
        self.menuState = MenuState.MAIN
        self.character = None


class Menu:
    def __init__(self, myOptionText, bodyText, uniqueName, parent=None, myEmoji=None, imageURL=None, menuState: MenuState = MenuState.DEFAULT):
        self.myOptionText = myOptionText
        self.myEmoji = myEmoji
        self.uniqueName = uniqueName
        self.bodyText = bodyText
        self.parent = parent  # This will hold a reference to the parent Menu object
        self.Options = []  # This will be a list of Menu objects
        self.imageURL = imageURL
        self.menuState = menuState

    def add_option(self, menu):
        menu.parent = self  # Set the parent of the added menu
        self.Options.append(menu)

def save_menu(menu, directory):
    def menu_to_dict(menu):
        return {
            "myOptionText": menu.myOptionText,
            "myEmoji": menu.myEmoji,
            "uniqueName": menu.uniqueName,
            "bodyText": menu.bodyText,
            "imageURL": menu.imageURL,
            "parentName": menu.parent.uniqueName,
            "Options": [option.uniqueName for option in menu.Options]
        }

    # Save the current menu as a JSON file
    file_path = f"{directory}/{menu.uniqueName}.json"
    with open(file_path, 'w') as f:
        json.dump(menu_to_dict(menu), f, indent=4)

    # Recursively save all child menus
    for option in menu.Options:
        save_menu(option, directory)

def load_menu(file_path, directory):
    def dict_to_menu(data, parent=None):
        # Initialize the menu object from the dictionary
        menu = Menu(
            myOptionText=data["myOptionText"],
            myEmoji=data.get("myEmoji"),
            uniqueName=data["uniqueName"],
            bodyText=data["bodyText"],
            imageURL=data["imageURL"],
            parent=parent
        )

        # Recursively load all child menus from their unique names
        for unique_name in data["Options"]:
            child_menu_path = f"{directory}/{unique_name}.json"
            option_menu = load_menu(child_menu_path, directory)
            option_menu.parent = menu
            menu.Options.append(option_menu)

        return menu

    with open(file_path, 'r') as f:
        data = json.load(f)
    return dict_to_menu(data)
