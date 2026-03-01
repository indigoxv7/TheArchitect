from src.ui.menu_functions import load_menus_from_directory


class MenuStore:
    def __init__(self, menu_directory: str):
        self.menu_directory = menu_directory

    def load_menus(self):
        return load_menus_from_directory(self.menu_directory)
